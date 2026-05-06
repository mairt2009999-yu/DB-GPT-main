from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

import httpx

from dbgpt.component import BaseComponent, SystemApp
from dbgpt_app.config import ApplicationConfig, RemoteServiceConfig
from dbgpt_app.microservice.context import RequestContext
from dbgpt_app.microservice.discovery import ServiceDiscovery, ServiceInstance


class ServiceUnavailableError(RuntimeError):
    pass


class AuthenticationFailedError(RuntimeError):
    pass


class AuthorizationFailedError(RuntimeError):
    pass


class InvalidUserServiceResponseError(RuntimeError):
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
            self.remote_config = self.app_config.service.web.remote_services.user_service

    @property
    def app_config(self) -> ApplicationConfig:
        return self.system_app.config.configs["app_config"]

    def _default_client_factory(self, timeout: httpx.Timeout) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=timeout)

    async def resolve_principal(self, request_context: RequestContext) -> ResolvedPrincipal:
        if self.remote_config is None:
            raise ServiceUnavailableError("User service configuration is missing")
        last_error = None
        attempts = max(1, self.remote_config.retries)
        for _ in range(attempts):
            instance = await self.discovery.get_service_instance(self.remote_config)
            if not instance:
                raise ServiceUnavailableError("No healthy user-service instance found")
            try:
                return await self._fetch_profile(instance, request_context)
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
                last_error = exc
                await self.discovery.invalidate(self.remote_config.service_name)
                continue
            except ServiceUnavailableError as exc:
                last_error = exc
                await self.discovery.invalidate(self.remote_config.service_name)
                continue
            except AuthenticationFailedError:
                raise
            except AuthorizationFailedError:
                raise
        raise ServiceUnavailableError(str(last_error) if last_error else "user-service unavailable")

    async def _fetch_profile(
        self, instance: ServiceInstance, request_context: RequestContext
    ) -> ResolvedPrincipal:
        timeout = httpx.Timeout(
            timeout=self.remote_config.timeout_ms / 1000,
            connect=self.remote_config.connect_timeout_ms / 1000,
            read=self.remote_config.read_timeout_ms / 1000,
        )
        async with self._client_factory(timeout) as client:
            response = await client.get(
                self._build_url(instance, self.remote_config.profile_path),
                headers=self._build_headers(request_context),
            )
        if response.status_code == 401:
            raise AuthenticationFailedError("user-service rejected the bearer token")
        if response.status_code == 403:
            raise AuthorizationFailedError("user-service rejected the principal")
        if response.status_code >= 500:
            raise ServiceUnavailableError(f"user-service failed with {response.status_code}")
        response.raise_for_status()
        payload = response.json()
        return self._to_resolved_principal(payload, request_context)

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
        user_id = payload.get("user_id") or payload.get("id") or request_context.user_id
        if not user_id:
            raise InvalidUserServiceResponseError("Missing user_id in user-service response")
        roles = payload.get("roles") or request_context.roles
        permissions = payload.get("permissions") or []
        return ResolvedPrincipal(
            profile=UserProfile(
                user_id=user_id,
                tenant_id=payload.get("tenant_id") or request_context.tenant_id,
                user_name=payload.get("user_name"),
                display_name=payload.get("display_name"),
            ),
            permissions=UserPermissionSet(
                roles=list(roles),
                permissions=list(permissions),
            ),
            sys_code=payload.get("sys_code") or request_context.sys_code,
            request_id=request_context.request_id,
        )
