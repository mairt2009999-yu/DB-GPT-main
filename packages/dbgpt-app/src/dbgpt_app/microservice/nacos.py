from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import socket
import time
from typing import Any, Dict, List, Optional

import httpx

from dbgpt.component import BaseComponent, SystemApp
from dbgpt_app.config import ApplicationConfig, NacosClientConfig
from dbgpt_app.microservice.discovery import ServiceInstance

logger = logging.getLogger(__name__)


class NacosNamingError(RuntimeError):
    pass


class NacosNamingClient(BaseComponent):
    name = "dbgpt_nacos_naming_client"

    def __init__(
        self,
        system_app: SystemApp,
        client_factory=None,
    ):
        self._client_factory = client_factory or self._default_client_factory
        self._access_token: Optional[str] = None
        self._access_token_expires_at = 0.0
        self._heartbeat_task: Optional[asyncio.Task] = None
        super().__init__(system_app)

    def init_app(self, system_app: SystemApp):
        self.system_app = system_app

    @property
    def app_config(self) -> ApplicationConfig:
        return self.system_app.config.configs["app_config"]

    @property
    def nacos_config(self) -> NacosClientConfig:
        return self.app_config.service.web.nacos

    def _default_client_factory(self, timeout: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self._base_url, timeout=timeout)

    @property
    def _base_url(self) -> str:
        server_addr = self.nacos_config.server_addr
        if server_addr.startswith("http://") or server_addr.startswith("https://"):
            return server_addr.rstrip("/")
        return f"http://{server_addr.rstrip('/')}"

    async def register_instance(self) -> None:
        nacos_config = self.nacos_config
        if not nacos_config.enabled or not nacos_config.register_on_startup:
            return
        params = {
            "serviceName": nacos_config.service_name,
            "ip": nacos_config.ip or self._resolve_local_ip(),
            "port": nacos_config.port or self.app_config.service.web.port,
            "namespaceId": nacos_config.namespace_id,
            "groupName": nacos_config.group_name,
            "clusterName": nacos_config.cluster_name,
            "ephemeral": str(nacos_config.ephemeral).lower(),
            "metadata": self._serialize_metadata(nacos_config.metadata),
            "healthy": "true",
            "enabled": "true",
        }
        await self._request("POST", "/nacos/v1/ns/instance", params=params)

    def start_heartbeat(self) -> None:
        nacos_config = self.nacos_config
        if (
            not nacos_config.enabled
            or not nacos_config.register_on_startup
            or not nacos_config.ephemeral
            or self._heartbeat_task
        ):
            return
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop_heartbeat(self) -> None:
        if not self._heartbeat_task:
            return
        self._heartbeat_task.cancel()
        try:
            await self._heartbeat_task
        except asyncio.CancelledError:
            pass
        finally:
            self._heartbeat_task = None

    async def send_heartbeat_once(self) -> None:
        nacos_config = self.nacos_config
        ip = nacos_config.ip or self._resolve_local_ip()
        port = nacos_config.port or self.app_config.service.web.port
        beat = {
            "serviceName": nacos_config.service_name,
            "ip": ip,
            "port": port,
            "cluster": nacos_config.cluster_name,
            "weight": 1.0,
            "metadata": nacos_config.metadata,
            "scheduled": True,
        }
        params = {
            "serviceName": nacos_config.service_name,
            "ip": ip,
            "port": port,
            "namespaceId": nacos_config.namespace_id,
            "groupName": nacos_config.group_name,
            "clusterName": nacos_config.cluster_name,
            "ephemeral": str(nacos_config.ephemeral).lower(),
            "beat": json.dumps(beat, separators=(",", ":"), ensure_ascii=False),
        }
        await self._request("PUT", "/nacos/v1/ns/instance/beat", params=params)

    async def _heartbeat_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self.nacos_config.heartbeat_interval_ms / 1000)
                await self.send_heartbeat_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Failed to send Nacos heartbeat: %s", exc)

    async def deregister_instance(self) -> None:
        nacos_config = self.nacos_config
        if not nacos_config.enabled:
            return
        params = {
            "serviceName": nacos_config.service_name,
            "ip": nacos_config.ip or self._resolve_local_ip(),
            "port": nacos_config.port or self.app_config.service.web.port,
            "namespaceId": nacos_config.namespace_id,
            "groupName": nacos_config.group_name,
            "clusterName": nacos_config.cluster_name,
            "ephemeral": str(nacos_config.ephemeral).lower(),
        }
        await self._request("DELETE", "/nacos/v1/ns/instance", params=params)

    async def list_instances(
        self,
        *,
        service_name: str,
        namespace_id: Optional[str],
        group_name: Optional[str],
        cluster_name: Optional[str],
    ) -> List[ServiceInstance]:
        params = {
            "serviceName": service_name,
            "namespaceId": namespace_id,
            "groupName": group_name,
            "clusterName": cluster_name,
            "healthyOnly": "true",
        }
        response = await self._request(
            "GET", "/nacos/v1/ns/instance/list", params=params
        )
        payload = response.json()
        hosts = payload.get("hosts", [])
        instances = []
        for host in hosts:
            instances.append(
                ServiceInstance(
                    service_name=service_name,
                    host=host["ip"],
                    port=int(host["port"]),
                    healthy=bool(host.get("healthy", True)),
                    enabled=bool(host.get("enabled", True)),
                    metadata=host.get("metadata") or {},
                    cluster_name=host.get("clusterName"),
                )
            )
        return instances

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        timeout = self.nacos_config.request_timeout_ms / 1000
        request_params = dict(params or {})
        await self._inject_auth(request_params)
        errors = []
        for _ in range(max(1, self.nacos_config.max_retries)):
            async with self._client_factory(timeout) as client:
                try:
                    response = await client.request(method, path, params=request_params)
                    response.raise_for_status()
                    return response
                except httpx.HTTPError as exc:
                    errors.append(exc)
        raise NacosNamingError(str(errors[-1]))

    async def _inject_auth(self, params: Dict[str, Any]) -> None:
        nacos_config = self.nacos_config
        if nacos_config.username and nacos_config.password:
            token = await self._get_access_token()
            if token:
                params["accessToken"] = token
        elif nacos_config.access_key and nacos_config.secret_key:
            timestamp = str(int(time.time() * 1000))
            service_name = params.get("serviceName", "")
            sign_data = f"{timestamp}@@{service_name}"
            signature = base64.b64encode(
                hmac.new(
                    nacos_config.secret_key.encode("utf-8"),
                    sign_data.encode("utf-8"),
                    hashlib.sha1,
                ).digest()
            ).decode("utf-8")
            params["ak"] = nacos_config.access_key
            params["data"] = sign_data
            params["signature"] = signature

    async def _get_access_token(self) -> Optional[str]:
        if self._access_token and time.time() < self._access_token_expires_at:
            return self._access_token
        timeout = self.nacos_config.request_timeout_ms / 1000
        async with self._client_factory(timeout) as client:
            response = await client.post(
                "/nacos/v1/auth/users/login",
                params={
                    "username": self.nacos_config.username,
                    "password": self.nacos_config.password,
                },
            )
            response.raise_for_status()
            payload = response.json()
            self._access_token = payload.get("accessToken")
            ttl = int(payload.get("tokenTtl", 18000))
            self._access_token_expires_at = time.time() + max(60, ttl - 30)
            return self._access_token

    def _serialize_metadata(self, metadata: Dict[str, str]) -> str:
        if not metadata:
            return "{}"
        return json.dumps(metadata, separators=(",", ":"), ensure_ascii=False)

    def _resolve_local_ip(self) -> str:
        try:
            addresses = socket.getaddrinfo(
                socket.gethostname(),
                None,
                family=socket.AF_INET,
                type=socket.SOCK_STREAM,
            )
            seen = set()
            for entry in addresses:
                ip = entry[4][0]
                if ip in seen:
                    continue
                seen.add(ip)
                if not ip.startswith("127."):
                    return ip
        except OSError:
            pass
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                ip = sock.getsockname()[0]
                if ip and not ip.startswith("127."):
                    return ip
        except OSError:
            pass
        return "127.0.0.1"
