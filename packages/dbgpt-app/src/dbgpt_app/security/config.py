"""RLS 配置模型。

由 ``component_configs.py`` 在应用启动时从配置文件解析并注册到 SystemApp。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal

from dbgpt.component import LifeCycle
from dbgpt.util.parameter_utils import BaseParameters


@dataclass
class RLSConfig(BaseParameters, LifeCycle):
    """L3 行级权限配置。

    - mode：``off`` 直通 / ``shadow`` 仅记录改写差异 / ``enforce`` 强制拦截
    - fail_strategy：``close`` 上游不可用时拒绝执行（v1 唯一支持）；``open`` 预留
    - local_ttl_seconds：进程内 LRU 缓存有效期
    - stale_fallback_seconds：上游故障时允许使用的最长 stale 缓存年龄
    - admin_role_codes：管理员角色编码列表（与 principal.is_admin 对齐）
    """

    name: str = field(default="dbgpt_rls_config")
    mode: Literal["off", "shadow", "enforce"] = field(default="off")
    fail_strategy: Literal["close", "open"] = field(default="close")
    upstream_url: str = field(default="")  # v1 不再使用，保留字段供后续接入
    upstream_timeout_ms: int = field(default=800)
    local_ttl_seconds: int = field(default=60)
    stale_fallback_seconds: int = field(default=1800)
    admin_role_codes: List[str] = field(default_factory=list)

    def init_app(self, system_app) -> None:
        """SystemApp component compatibility hook."""
        self.system_app = system_app
