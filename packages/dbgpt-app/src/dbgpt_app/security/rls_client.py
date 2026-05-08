"""
rls_client.py  ——  行级数据权限（Row-Level Security）谓词客户端（user-service 适配器版）
=============================================================

职责
----
封装 DB-GPT 与上游 user-service 之间的通信。
上游 user-service 通过 getSqlFragmentByUserId 接口，逐表返回 WHERE 谓词片段。
本模块负责：
  1. 逐表调用 UserServiceClient.get_sql_fragment_by_user_id；
  2. 维护进程内 LRU（TTLCache）+ stale 缓存，减少每次查询的远程开销；
  3. 把上游返回的 SqlFragment 转成强类型的 RLSRule 对象，供 RLSAwareSQLExecutor 消费。

缓存键格式
----------
  (user_id, sys_code, table_code)

错误映射
--------
  成功（含空 fragment）→ RLSRule(allowed=True, predicate=sql_fragment)
  AuthorizationFailedError（HTTP 403）→ RLSRule(allowed=False)
  AuthenticationFailedError（HTTP 401/404）→ 直接抛出，由 executor 处理（fail-close）
  ServiceUnavailableError / 网络异常 → 查 stale 缓存，无则抛 RLSUpstreamUnavailableError

测试
----
  see: tests/security/test_rls_client.py
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

from cachetools import TTLCache

from dbgpt_app.security.exceptions import RLSUpstreamUnavailableError  # re-export

if TYPE_CHECKING:
    from dbgpt_app.microservice.context import RequestContext
    from dbgpt_app.microservice.user_service import UserServiceClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 数据类型
# ---------------------------------------------------------------------------


@dataclass
class RLSTableRef:
    """标识一张目标表，作为缓存键与上游请求的基本单元。"""

    datasource: str  # DB-GPT 数据源名称
    schema: str  # 数据库 schema 名
    table: str  # 表名（不含 schema 前缀）
    alias: str = ""  # SQL 里该表的别名，仅在注入谓词时使用，不参与缓存键


@dataclass
class RLSRule:
    """上游权限服务对一张表返回的访问规则。

    Attributes:
        table:            对应 RLSTableRef.table
        allowed:          False 表示当前用户完全无权限，RLSAwareSQLExecutor
                          应直接拒绝整条 SQL。
        predicate:        WHERE 谓词片段，不含表别名前缀，不含 WHERE 关键字。
                          示例：create_by="1"
                          为空字符串表示无行级限制（全量可见）。
        predicate_dialect: 谓词使用的 SQL 方言。
        column_masks:     列遮蔽规则，初版保留字段，不实现。
        denied_columns:   完全禁止访问的列，初版保留字段，不实现。
        ttl_seconds:      上游建议的缓存时长；0 表示使用本地默认值。
    """

    table: str
    allowed: bool = True
    predicate: str = ""
    predicate_dialect: str = "ansi"
    column_masks: List[dict] = field(default_factory=list)
    denied_columns: List[str] = field(default_factory=list)
    ttl_seconds: int = 0


# ---------------------------------------------------------------------------
# 主类
# ---------------------------------------------------------------------------


class RLSClient:
    """行级权限谓词客户端（user-service 适配器版）。

    提供 batch_fetch 接口，供 RLSAwareSQLExecutor 使用。
    内部逐表调用 UserServiceClient.get_sql_fragment_by_user_id，
    维护 L1 TTLCache + stale 缓存兜底。
    """

    def __init__(
        self,
        user_service: "UserServiceClient",
        local_ttl_seconds: int = 60,
        stale_fallback_seconds: int = 1800,
    ):
        """
        Args:
            user_service:           UserServiceClient 实例（由 SystemApp 注入）。
            local_ttl_seconds:      进程内 TTLCache 的有效期（秒）。
            stale_fallback_seconds: 上游故障时允许使用的最长 stale 缓存年龄（秒）。
        """
        self._user_service = user_service
        self._local_ttl = local_ttl_seconds
        self._stale_ttl = stale_fallback_seconds
        # L1: TTL 缓存，key -> RLSRule
        self._l1_cache: TTLCache = TTLCache(maxsize=1024, ttl=local_ttl_seconds)
        # stale: 无 TTL，存最近一次成功的 RLSRule
        self._stale_cache: dict[str, RLSRule] = {}

    @classmethod
    def from_user_service(cls, system_app) -> "RLSClient":
        """从 SystemApp 取 UserServiceClient 单例构造 RLSClient。"""
        from dbgpt_app.microservice.user_service import UserServiceClient

        user_service = system_app.get_component(
            UserServiceClient.name, UserServiceClient
        )
        return cls(user_service=user_service)

    # ------------------------------------------------------------------
    # 核心接口
    # ------------------------------------------------------------------

    async def batch_fetch(
        self,
        principal: "RequestContext",
        tables: List[RLSTableRef],
    ) -> List[RLSRule]:
        """批量拉取多张表的 RLS 规则，与 tables 参数一一对应。

        执行顺序：
          1. 对每张表查 L1（进程内 TTLCache）；
          2. L1 miss → 调 _fetch_one 访问上游；
          3. 上游失败 → 查 stale 缓存兜底或抛 RLSUpstreamUnavailableError。

        Args:
            principal: 当前请求的用户身份（RequestContext）。
            tables:    SQL 中涉及的所有表。

        Returns:
            与 tables 顺序一一对应的 RLSRule 列表。

        Raises:
            RLSUpstreamUnavailableError: 上游不可用且无 stale 缓存。
        """
        from dbgpt_app.microservice.user_service import (
            AuthorizationFailedError,
            ServiceUnavailableError,
        )

        results: List[RLSRule] = []
        for ref in tables:
            cache_key = self._make_cache_key(principal, ref)
            # L1 命中
            if cache_key in self._l1_cache:
                results.append(self._l1_cache[cache_key])
                continue
            # L1 miss → 调上游
            try:
                rule = await self._fetch_one(principal, ref)
                self._l1_cache[cache_key] = rule
                self._stale_cache[cache_key] = rule
                results.append(rule)
            except (ServiceUnavailableError, OSError, Exception) as exc:
                # 只有非 AuthorizationFailedError / AuthenticationFailedError 走 stale
                if isinstance(exc, AuthorizationFailedError):
                    # 已在 _fetch_one 里处理，不应到这里
                    raise
                # 查 stale
                if cache_key in self._stale_cache:
                    logger.warning(
                        "RLS upstream unavailable, using stale cache for table=%s err=%s",
                        ref.table,
                        exc,
                    )
                    results.append(self._stale_cache[cache_key])
                else:
                    raise RLSUpstreamUnavailableError(
                        f"Upstream unavailable and no stale cache for table={ref.table}"
                    ) from exc
        return results

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _make_cache_key(self, principal: "RequestContext", table: RLSTableRef) -> str:
        """构造缓存键：(user_id, sys_code, table_code)。"""
        user_id = getattr(principal, "user_id", "") or ""
        sys_code = getattr(principal, "sys_code", "") or ""
        return f"{user_id}:{sys_code}:{table.table}"

    async def _fetch_one(
        self,
        principal: "RequestContext",
        ref: RLSTableRef,
    ) -> RLSRule:
        """调用 UserServiceClient 查询单张表的谓词。

        错误映射：
          成功 → RLSRule(allowed=True, predicate=sql_fragment)
          AuthorizationFailedError → RLSRule(allowed=False)
          其他异常 → 透传，由 batch_fetch 决定走 stale 还是抛
        """
        from dbgpt_app.microservice.user_service import AuthorizationFailedError

        try:
            fragment = await self._user_service.get_sql_fragment_by_user_id(
                principal, ref.table
            )
            return RLSRule(
                table=ref.table,
                allowed=True,
                predicate=fragment.sql_fragment or "",
            )
        except AuthorizationFailedError:
            return RLSRule(table=ref.table, allowed=False, predicate="")

    def invalidate(
        self,
        user_id: str,
        sys_code: str = "",
        table: Optional[str] = None,
    ) -> None:
        """主动使缓存失效（按前缀清除）。

        Args:
            user_id:  被变更的用户。
            sys_code: 租户编码。
            table:    指定表名；None 表示该用户所有表。
        """
        prefix = f"{user_id}:{sys_code}:"
        if table:
            prefix += table
        keys_to_delete = [
            k for k in list(self._l1_cache.keys()) if str(k).startswith(prefix)
        ]
        for k in keys_to_delete:
            self._l1_cache.pop(k, None)
            self._stale_cache.pop(k, None)
