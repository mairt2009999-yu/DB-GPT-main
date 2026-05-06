from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from dbgpt.component import BaseComponent, SystemApp
from dbgpt_app.config import ApplicationConfig, NacosClientConfig, RemoteServiceConfig


@dataclass
class ServiceInstance:
    service_name: str
    host: str
    port: int
    healthy: bool = True
    enabled: bool = True
    metadata: Dict[str, str] = field(default_factory=dict)
    cluster_name: Optional[str] = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


class ServiceRegistryCache:
    def __init__(self, ttl_seconds: int):
        self._ttl_seconds = ttl_seconds
        self._values: Dict[str, tuple[float, List[ServiceInstance]]] = {}

    def get(
        self, service_name: str, *, now: Optional[float] = None
    ) -> Optional[List[ServiceInstance]]:
        entry = self._values.get(service_name)
        if not entry:
            return None
        now = time.time() if now is None else now
        expires_at, values = entry
        if now >= expires_at:
            self._values.pop(service_name, None)
            return None
        return values

    def set(
        self,
        service_name: str,
        instances: List[ServiceInstance],
        *,
        now: Optional[float] = None,
    ) -> None:
        now = time.time() if now is None else now
        self._values[service_name] = (now + self._ttl_seconds, instances)

    def invalidate(self, service_name: str) -> None:
        self._values.pop(service_name, None)


class ServiceDiscovery(BaseComponent):
    name = "dbgpt_service_discovery"

    def __init__(self, system_app: SystemApp, naming_client=None):
        self.naming_client = naming_client
        self._caches: Dict[str, ServiceRegistryCache] = {}
        self._round_robin_counters: Dict[str, int] = {}
        super().__init__(system_app)

    def init_app(self, system_app: SystemApp):
        self.system_app = system_app
        if self.naming_client is None:
            from dbgpt_app.microservice.nacos import NacosNamingClient

            self.naming_client = NacosNamingClient.get_instance(system_app)

    @property
    def app_config(self) -> ApplicationConfig:
        return self.system_app.config.configs["app_config"]

    async def get_service_instances(
        self, service_config: RemoteServiceConfig
    ) -> List[ServiceInstance]:
        cache = self._caches.setdefault(
            service_config.service_name,
            ServiceRegistryCache(ttl_seconds=max(1, service_config.cache_ttl_seconds)),
        )
        cached = cache.get(service_config.service_name)
        if cached is not None:
            return cached
        nacos_config = self.app_config.service.web.nacos
        instances = await self.naming_client.list_instances(
            service_name=service_config.service_name,
            namespace_id=service_config.namespace_id or nacos_config.namespace_id,
            group_name=service_config.group_name or nacos_config.group_name,
            cluster_name=service_config.cluster_name or nacos_config.cluster_name,
        )
        healthy_instances = [instance for instance in instances if instance.healthy]
        cache.set(service_config.service_name, healthy_instances)
        return healthy_instances

    async def get_service_instance(
        self, service_config: RemoteServiceConfig
    ) -> Optional[ServiceInstance]:
        instances = await self.get_service_instances(service_config)
        if not instances:
            return None
        if service_config.load_balance == "round_robin":
            index = self._round_robin_counters.get(service_config.service_name, 0)
            self._round_robin_counters[service_config.service_name] = index + 1
            return instances[index % len(instances)]
        return random.choice(instances)

    async def invalidate(self, service_name: str) -> None:
        cache = self._caches.get(service_name)
        if cache:
            cache.invalidate(service_name)
