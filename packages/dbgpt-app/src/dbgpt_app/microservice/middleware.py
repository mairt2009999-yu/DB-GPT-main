from __future__ import annotations

import json
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from dbgpt_app.microservice.context import (
    RequestContext,
    reset_current_request_context,
    reset_current_resolved_principal,
    set_current_request_context,
    set_current_resolved_principal,
)

logger = logging.getLogger(__name__)


def _split_roles(raw_roles: str | None) -> list[str]:
    if not raw_roles:
        return []
    return [role.strip() for role in raw_roles.split(",") if role.strip()]


def _extract_user_id_from_user_info(raw_user_info: str | None) -> str | None:
    if not raw_user_info:
        return None
    try:
        user_info = json.loads(raw_user_info)
    except json.JSONDecodeError:
        logger.warning("Invalid X-User-Info JSON: %s", raw_user_info)
        return None
    if not isinstance(user_info, dict):
        return None
    user_id = user_info.get("userId") or user_info.get("user_id")
    return str(user_id) if user_id else None


class ContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        user_info_header = request.headers.get("X-User-Info")
        if user_info_header:
            logger.info("X-User-Info: %s", user_info_header)
        header_user_id = request.headers.get("X-User-Id")
        user_info_user_id = _extract_user_id_from_user_info(user_info_header)
        request_context = RequestContext(
            authorization=request.headers.get("Authorization"),
            user_id=header_user_id or user_info_user_id,
            tenant_id=request.headers.get("X-Tenant-Id"),
            request_id=request.headers.get("X-Request-Id"),
            roles=_split_roles(request.headers.get("X-Roles")),
            sys_code=request.headers.get("X-System-Code"),
        )
        logger.info(
            "Request context inbound: path=%s headerUserId=%s "
            "userInfoUserId=%s contextUserId=%s roles=%s sysCode=%s "
            "requestId=%s",
            request.url.path,
            header_user_id,
            user_info_user_id,
            request_context.user_id,
            request_context.roles,
            request_context.sys_code,
            request_context.request_id,
        )
        request.state.request_context = request_context
        token = set_current_request_context(request_context)
        try:
            if request.url.path.startswith("/api") and request_context.user_id:
                response = await self._resolve_principal(request, request_context)
                if response is not None:
                    return response
            response = await call_next(request)
        finally:
            resolved_token = getattr(request.state, "_resolved_principal_token", None)
            if resolved_token is not None:
                reset_current_resolved_principal(resolved_token)
            reset_current_request_context(token)
        return response

    async def _resolve_principal(
        self, request: Request, request_context: RequestContext
    ):
        system_app = getattr(request.app.state, "dbgpt_system_app", None)
        if not system_app:
            return None
        app_config = system_app.config.configs.get("app_config")
        if not app_config or not app_config.service.web.nacos.enabled:
            return None
        from dbgpt_app.microservice.user_service import (
            AuthenticationFailedError,
            AuthorizationFailedError,
            ServiceUnavailableError,
            UserServiceClient,
        )

        user_service_client = UserServiceClient.get_instance(system_app)
        inbound_user_id = request_context.user_id
        logger.info(
            "Resolving principal via user-service: path=%s userId=%s "
            "roles=%s sysCode=%s requestId=%s",
            request.url.path,
            inbound_user_id,
            request_context.roles,
            request_context.sys_code,
            request_context.request_id,
        )
        try:
            resolved_principal = await user_service_client.resolve_principal(
                request_context
            )
        except AuthenticationFailedError as exc:
            return JSONResponse(status_code=401, content={"detail": str(exc)})
        except AuthorizationFailedError as exc:
            return JSONResponse(status_code=403, content={"detail": str(exc)})
        except ServiceUnavailableError as exc:
            return JSONResponse(status_code=503, content={"detail": str(exc)})
        resolved_user_id = resolved_principal.profile.user_id
        logger.info(
            "Resolved principal from user-service: inboundUserId=%s "
            "resolvedUserId=%s roles=%s sysCode=%s requestId=%s",
            inbound_user_id,
            resolved_user_id,
            resolved_principal.permissions.roles,
            resolved_principal.sys_code,
            resolved_principal.request_id,
        )
        if inbound_user_id and resolved_user_id != inbound_user_id:
            logger.warning(
                "User-service resolved principal user mismatch: "
                "inboundUserId=%s resolvedUserId=%s path=%s",
                inbound_user_id,
                resolved_user_id,
                request.url.path,
            )
        request.state.resolved_principal = resolved_principal
        request_context.user_id = resolved_user_id
        request_context.tenant_id = resolved_principal.profile.tenant_id
        request_context.roles = list(resolved_principal.permissions.roles)
        request_context.sys_code = resolved_principal.sys_code
        logger.info(
            "Request context resolved: path=%s userId=%s tenantId=%s "
            "roles=%s sysCode=%s requestId=%s",
            request.url.path,
            request_context.user_id,
            request_context.tenant_id,
            request_context.roles,
            request_context.sys_code,
            request_context.request_id,
        )
        token = set_current_resolved_principal(resolved_principal)
        request.state._resolved_principal_token = token
        return None
