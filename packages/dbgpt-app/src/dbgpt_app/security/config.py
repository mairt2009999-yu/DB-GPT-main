"""RLS 配置模型。

由 ``component_configs.py`` 在应用启动时从配置文件解析并注册到 SystemApp。
"""

from __future__ import annotations

from typing import List, Literal

from dbgpt._private.pydantic import BaseModel


class RLSConfig(BaseModel):
    """L3 行级权限配置。

    - mode：``off`` 直通 / ``shadow`` 仅记录改写差异 / ``enforce`` 强制拦截
    - fail_strategy：``close`` 上游不可用时拒绝执行（v1 唯一支持）；``open`` 预留
    - local_ttl_seconds：进程内 LRU 缓存有效期
    - stale_fallback_seconds：上游故障时允许使用的最长 stale 缓存年龄
    - admin_role_codes：管理员角色编码列表（与 principal.is_admin 对齐）
    """

    mode: Literal["off", "shadow", "enforce"] = "off"
    fail_strategy: Literal["close", "open"] = "close"
    upstream_url: str = ""  # v1 不再使用，保留字段供后续接入
    upstream_timeout_ms: int = 800
    local_ttl_seconds: int = 60
    stale_fallback_seconds: int = 1800
    admin_role_codes: List[str] = []
