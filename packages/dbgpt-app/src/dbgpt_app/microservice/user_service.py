from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, List, Optional
from urllib.parse import quote

import httpx

from dbgpt.component import BaseComponent, SystemApp
from dbgpt_app.config import ApplicationConfig, RemoteServiceConfig
from dbgpt_app.microservice.context import RequestContext
from dbgpt_app.microservice.discovery import ServiceDiscovery, ServiceInstance

logger = logging.getLogger(__name__)


class ServiceUnavailableError(RuntimeError):
    pass


class AuthenticationFailedError(RuntimeError):
    pass


class AuthorizationFailedError(RuntimeError):
    pass


class InvalidUserServiceResponseError(ServiceUnavailableError):
    pass


@dataclass(eq=True)
class UserProfile:
    user_id: str
    tenant_id: Optional[str] = None
    user_name: Optional[str] = None
    display_name: Optional[str] = None


@dataclass(eq=True)
class UserPermissionSet:
    roles: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)


@dataclass(eq=True)
class ResolvedPrincipal:
    profile: UserProfile
    permissions: UserPermissionSet
    sys_code: Optional[str] = None
    request_id: Optional[str] = None


@dataclass(eq=True)
class SqlFragment:
    user_id: str
    table_code: str
    sql_fragment: str


class UserServiceClient(BaseComponent):
    name = "dbgpt_user_service_client"

    def __init__(
        self,
        system_app: Optional[SystemApp],
        discovery=None,
        remote_config: Optional[RemoteServiceConfig] = None,
        client_factory: Optional[Callable[[httpx.Timeout], httpx.AsyncClient]] = None,
    ):
        self.discovery = discovery
        self.remote_config = remote_config
        self._client_factory = client_factory or self._default_client_factory
        if system_app is not None:
            super().__init__(system_app)
        else:
            self.system_app = None

    def init_app(self, system_app: SystemApp):
        self.system_app = system_app
        if self.discovery is None:
            self.discovery = ServiceDiscovery.get_instance(system_app)
        if self.remote_config is None:
            self.remote_config = (
                self.app_config.service.web.remote_services.user_service
            )

    @property
    def app_config(self) -> ApplicationConfig:
        return self.system_app.config.configs["app_config"]

    def _default_client_factory(self, timeout: httpx.Timeout) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=timeout)

    async def resolve_principal(
        self, request_context: RequestContext
    ) -> ResolvedPrincipal:
        if self.remote_config is None:
            raise ServiceUnavailableError("User service configuration is missing")
        if not request_context.user_id:
            raise AuthenticationFailedError("Missing X-User-Id header")
        last_error = None
        last_endpoint = None
        attempts = max(1, self.remote_config.retries)
        for _ in range(attempts):
            instance = await self.discovery.get_service_instance(self.remote_config)
            if not instance:
                raise ServiceUnavailableError("No healthy user-service instance found")
            roles_path = self._roles_path(request_context)
            endpoint = self._build_url(instance, roles_path)
            last_endpoint = endpoint
            logger.info(
                "Calling user-service roles endpoint: service=%s baseUrl=%s "
                "url=%s userId=%s",
                self.remote_config.service_name,
                instance.base_url,
                endpoint,
                request_context.user_id,
            )
            try:
                return await self._fetch_roles(instance, request_context)
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
                last_error = exc
                logger.warning(
                    "Retryable user-service roles call failed: %s",
                    self._format_remote_error(exc, endpoint),
                )
                await self.discovery.invalidate(self.remote_config.service_name)
                continue
            except InvalidUserServiceResponseError:
                raise
            except ServiceUnavailableError as exc:
                last_error = exc
                logger.warning(
                    "Retryable user-service roles call failed: %s",
                    self._format_remote_error(exc, endpoint),
                )
                await self.discovery.invalidate(self.remote_config.service_name)
                continue
            except AuthenticationFailedError:
                raise
            except AuthorizationFailedError:
                raise
        message = self._format_remote_error(last_error, last_endpoint)
        if last_error:
            raise ServiceUnavailableError(message) from last_error
        raise ServiceUnavailableError(message)

    async def get_sql_fragment_by_user_id(
        self, request_context: RequestContext, table_code: str
    ) -> SqlFragment:
        if self.remote_config is None:
            raise ServiceUnavailableError("User service configuration is missing")
        if not request_context.user_id:
            raise AuthenticationFailedError("Missing X-User-Id header")
        last_error = None
        last_endpoint = None
        attempts = max(1, self.remote_config.retries)
        for _ in range(attempts):
            instance = await self.discovery.get_service_instance(self.remote_config)
            if not instance:
                raise ServiceUnavailableError("No healthy user-service instance found")
            fragment_path = self._sql_fragment_path(request_context)
            endpoint = self._build_url(instance, fragment_path)
            last_endpoint = endpoint
            logger.info(
                "Calling user-service SQL fragment endpoint: service=%s "
                "baseUrl=%s url=%s userId=%s tableCode=%s",
                self.remote_config.service_name,
                instance.base_url,
                endpoint,
                request_context.user_id,
                table_code,
            )
            try:
                return await self._fetch_sql_fragment(
                    instance, request_context, table_code
                )
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
                last_error = exc
                logger.warning(
                    "Retryable user-service SQL fragment call failed: %s",
                    self._format_remote_error(exc, endpoint),
                )
                await self.discovery.invalidate(self.remote_config.service_name)
                continue
            except InvalidUserServiceResponseError:
                raise
            except ServiceUnavailableError as exc:
                last_error = exc
                logger.warning(
                    "Retryable user-service SQL fragment call failed: %s",
                    self._format_remote_error(exc, endpoint),
                )
                await self.discovery.invalidate(self.remote_config.service_name)
                continue
            except AuthenticationFailedError:
                raise
            except AuthorizationFailedError:
                raise
        message = self._format_remote_error(last_error, last_endpoint)
        if last_error:
            raise ServiceUnavailableError(message) from last_error
        raise ServiceUnavailableError(message)

    def _roles_path(self, request_context: RequestContext) -> str:
        return self.remote_config.roles_path.format(
            user_id=quote(str(request_context.user_id), safe="")
        )

    def _sql_fragment_path(self, request_context: RequestContext) -> str:
        return self.remote_config.sql_fragment_path.format(
            user_id=quote(str(request_context.user_id), safe="")
        )

    def _format_remote_error(
        self, exc: Optional[BaseException], endpoint: Optional[str]
    ) -> str:
        if not exc:
            return "user-service unavailable"
        details = [type(exc).__name__]
        message = str(exc).strip()
        if message:
            details.append(message)
        else:
            details.append(repr(exc))
        if endpoint:
            details.append(f"endpoint={endpoint}")
        return ": ".join(details)

    async def _fetch_roles(
        self, instance: ServiceInstance, request_context: RequestContext
    ) -> ResolvedPrincipal:
        timeout = httpx.Timeout(
            timeout=self.remote_config.timeout_ms / 1000,
            connect=self.remote_config.connect_timeout_ms / 1000,
            read=self.remote_config.read_timeout_ms / 1000,
        )
        roles_path = self._roles_path(request_context)
        async with self._client_factory(timeout) as client:
            response = await client.get(
                self._build_url(instance, roles_path),
                headers=self._build_headers(request_context),
            )
        if response.status_code in (401, 404):
            raise AuthenticationFailedError("user-service rejected the principal")
        if response.status_code == 403:
            raise AuthorizationFailedError("user-service rejected the principal")
        if response.status_code >= 500:
            raise ServiceUnavailableError(
                f"user-service failed with {response.status_code}"
            )
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise InvalidUserServiceResponseError(
                "Invalid JSON in user-service response"
            ) from exc
        return self._to_resolved_principal(payload, request_context)

    async def _fetch_sql_fragment(
        self,
        instance: ServiceInstance,
        request_context: RequestContext,
        table_code: str,
    ) -> SqlFragment:
        timeout = httpx.Timeout(
            timeout=self.remote_config.timeout_ms / 1000,
            connect=self.remote_config.connect_timeout_ms / 1000,
            read=self.remote_config.read_timeout_ms / 1000,
        )
        fragment_path = self._sql_fragment_path(request_context)
        async with self._client_factory(timeout) as client:
            response = await client.get(
                self._build_url(instance, fragment_path),
                headers=self._build_headers(request_context),
                params={"tableCode": table_code},
            )
        if response.status_code in (401, 404):
            raise AuthenticationFailedError("user-service rejected the principal")
        if response.status_code == 403:
            raise AuthorizationFailedError("user-service rejected the principal")
        if response.status_code >= 500:
            raise ServiceUnavailableError(
                f"user-service failed with {response.status_code}"
            )
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise InvalidUserServiceResponseError(
                "Invalid JSON in user-service response"
            ) from exc
        return self._to_sql_fragment(payload, request_context, table_code)

    def _build_url(self, instance: ServiceInstance, path: str) -> str:
        prefix = self.remote_config.path_prefix.rstrip("/")
        suffix = path if path.startswith("/") else f"/{path}"
        if prefix:
            return f"{instance.base_url}{prefix}{suffix}"
        return f"{instance.base_url}{suffix}"

    def _build_headers(self, request_context: RequestContext) -> dict:
        headers = {}
        if request_context.authorization:
            headers["Authorization"] = request_context.authorization
        if request_context.user_id:
            headers["X-User-Id"] = request_context.user_id
        if request_context.tenant_id:
            headers["X-Tenant-Id"] = request_context.tenant_id
        if request_context.request_id:
            headers["X-Request-Id"] = request_context.request_id
        if request_context.roles:
            headers["X-Roles"] = ",".join(request_context.roles)
        if request_context.sys_code:
            headers["X-System-Code"] = request_context.sys_code
        return headers

    def _to_resolved_principal(
        self, payload: dict, request_context: RequestContext
    ) -> ResolvedPrincipal:
        if not isinstance(payload, dict):
            raise InvalidUserServiceResponseError("Invalid user-service response")
        code = payload.get("code")
        if code is not None and int(code) != 200:
            if int(code) in (401, 404):
                raise AuthenticationFailedError("user-service rejected the principal")
            if int(code) == 403:
                raise AuthorizationFailedError("user-service rejected the principal")
            if int(code) >= 500:
                raise ServiceUnavailableError(f"user-service failed with {code}")
            raise InvalidUserServiceResponseError(
                f"user-service returned unexpected code {code}"
            )
        data = payload.get("data") if "data" in payload else payload
        if not isinstance(data, dict):
            raise InvalidUserServiceResponseError(
                "Missing data in user-service response"
            )
        user_id = (
            data.get("userId")
            or data.get("user_id")
            or data.get("id")
            or request_context.user_id
        )
        if not user_id:
            raise InvalidUserServiceResponseError(
                "Missing user_id in user-service response"
            )
        roles = data.get("roleCodes")
        if roles is None:
            role_items = data.get("roles")
            if isinstance(role_items, list):
                roles = [
                    item.get("code")
                    for item in role_items
                    if isinstance(item, dict) and item.get("code")
                ]
        if roles is None:
            roles = data.get("roles")
        if roles is None:
            raise InvalidUserServiceResponseError(
                "Missing roles in user-service response"
            )
        permissions = data.get("permissions") or []
        return ResolvedPrincipal(
            profile=UserProfile(
                user_id=str(user_id),
                tenant_id=data.get("tenant_id") or request_context.tenant_id,
                user_name=data.get("user_name") or data.get("username"),
                display_name=data.get("display_name"),
            ),
            permissions=UserPermissionSet(
                roles=list(roles),
                permissions=list(permissions),
            ),
            sys_code=payload.get("sys_code") or request_context.sys_code,
            request_id=request_context.request_id,
        )

    def _to_sql_fragment(
        self, payload: dict, request_context: RequestContext, table_code: str
    ) -> SqlFragment:
        if not isinstance(payload, dict):
            raise InvalidUserServiceResponseError("Invalid user-service response")
        code = payload.get("code")
        if code is not None and int(code) != 200:
            if int(code) in (401, 404):
                raise AuthenticationFailedError("user-service rejected the principal")
            if int(code) == 403:
                raise AuthorizationFailedError("user-service rejected the principal")
            if int(code) >= 500:
                raise ServiceUnavailableError(f"user-service failed with {code}")
            raise InvalidUserServiceResponseError(
                f"user-service returned unexpected code {code}"
            )
        data = payload.get("data") if "data" in payload else payload
        if not isinstance(data, dict):
            raise InvalidUserServiceResponseError(
                "Missing data in user-service response"
            )
        sql_fragment = data.get("sqlFragment") or data.get("sql_fragment")
        if sql_fragment is None:
            raise InvalidUserServiceResponseError(
                "Missing sqlFragment in user-service response"
            )
        return SqlFragment(
            user_id=str(
                data.get("userId") or data.get("user_id") or request_context.user_id
            ),
            table_code=str(
                data.get("tableCode") or data.get("table_code") or table_code
            ),
            sql_fragment=str(sql_fragment),
        )
