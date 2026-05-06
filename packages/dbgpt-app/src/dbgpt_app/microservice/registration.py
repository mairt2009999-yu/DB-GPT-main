from __future__ import annotations

from dbgpt.component import BaseComponent, SystemApp
from dbgpt_app.config import ApplicationConfig


class ServiceRegistration(BaseComponent):
    name = "dbgpt_service_registration"

    def __init__(self, system_app: SystemApp, naming_client=None):
        self.naming_client = naming_client
        super().__init__(system_app)

    def init_app(self, system_app: SystemApp):
        self.system_app = system_app
        if self.naming_client is None:
            from dbgpt_app.microservice.nacos import NacosNamingClient

            self.naming_client = NacosNamingClient.get_instance(system_app)

    @property
    def app_config(self) -> ApplicationConfig:
        return self.system_app.config.configs["app_config"]

    async def async_after_start(self):
        if self.app_config.service.web.nacos.enabled:
            await self.naming_client.register_instance()

    async def async_before_stop(self):
        if self.app_config.service.web.nacos.enabled:
            await self.naming_client.deregister_instance()
