"""
rls_client.py  ——  行级数据权限（Row-Level Security）谓词客户端
=============================================================

职责
----
封装 DB-GPT 与上游权限服务之间的通信。
上游权限服务决定"这个用户在这张表里能看到哪些行"，
本模块负责：
  1. 批量调用上游 HTTP 接口拿到 WHERE 谓词片段；
  2. 维护三级缓存（进程内 LRU → Redis → 直连上游），减少每次查询的远程开销；
  3. 把上游返回的原始 JSON 转成强类型的 RLSRule 对象，供 RLSAwareSQLExecutor 消费。

工作流程
--------
  调用方（RLSAwareSQLExecutor）
        │
        ▼
  RLSClient.batch_fetch(principal, tables)
        │
        ├─ L1 进程内 LRU（TTL 60s）→ 命中则直接返回
        │
        ├─ L2 Redis 共享缓存（TTL 5min）→ 命中则回填 L1 并返回
        │
        └─ L3 HTTP 调上游权限服务（批量接口）
                │
                ├─ 成功 → 写 L1/L2 缓存，返回 RLSRule 列表
                │
                └─ 失败 → 查 stale 缓存（最长 stale_fallback_seconds）
                          有 stale → 用 stale 兜底，同时异步重试
                          无 stale → 抛 RLSUpstreamUnavailableError

缓存键格式
----------
  (user_id, sys_code, roles_hash, datasource, schema_name, table_name)

  注意：roles 也参与 key，因为上游可能按角色给出不同谓词；
        roles_hash 是 sorted(roles) 的 sha256 前 8 位。

上游接口契约（Request / Response 详细格式见设计文档）
----------------------------------------------------
  POST {upstream_url}/v1/rls/batch-query

  Request:
    {
      "principal": {"user_id": "...", "sys_code": "...", "roles": [...]},
      "resources": [
        {"datasource": "...", "schema": "...", "table": "..."},
        ...
      ],
      "action": "select",
      "context": {"trace_id": "..."}
    }

  Response:
    {
      "results": [
        {
          "table": "orders",
          "allowed": true,
          "predicate": "region IN ('华南') AND owner_id = 1001",
          "predicate_dialect": "ansi",
          "column_masks": [],
          "denied_columns": [],
          "ttl_seconds": 60
        },
        {"table": "customers", "allowed": false}
      ]
    }

配置（configs/*.toml）
---------------------
  [serve.rls]
  upstream_url = "${env:RLS_UPSTREAM_URL}"
  upstream_timeout_ms = 800
  stale_fallback_seconds = 1800
  batch_enabled = true

  [serve.rls.cache]
  local_ttl_seconds = 60
  redis_ttl_seconds = 300
  redis_url = "${env:REDIS_URL:-}"

如何接入
--------
  rls_client = RLSClient.from_config(config)
  # 由 RLSAwareSQLExecutor 内部持有并调用，外部一般不需要直接使用。

测试
----
  see: tests/security/test_rls_client.py
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from dbgpt_app.security.principal import Principal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 数据类型
# ---------------------------------------------------------------------------


@dataclass
class RLSTableRef:
    """标识一张目标表，作为缓存键与上游请求的基本单元。"""

    datasource: str   # DB-GPT 数据源名称，对应 connect_config.db_name
    schema: str       # 数据库 schema 名（MySQL 里通常等于库名）
    table: str        # 表名（不含 schema 前缀）
    alias: str = ""   # SQL 里该表的别名，仅在注入谓词时使用，不参与缓存键


@dataclass
class RLSRule:
    """上游权限服务对一张表返回的访问规则。

    Attributes:
        table:            对应 RLSTableRef.table
        allowed:          False 表示当前用户完全无权限，RLSAwareSQLExecutor
                          应直接拒绝整条 SQL。
        predicate:        WHERE 谓词片段，不含表别名前缀，不含 WHERE 关键字。
                          示例："region IN ('华南') AND owner_id = 1001"
                          为空字符串表示无行级限制（全量可见）。
        predicate_dialect: 谓词使用的 SQL 方言，通常与 datasource 一致。
        column_masks:     列遮蔽规则，初版保留字段，不实现。
        denied_columns:   完全禁止访问的列，初版保留字段，不实现。
        ttl_seconds:      上游建议的缓存时长；0 表示使用本地默认值。
    """

    table: str
    allowed: bool
    predicate: str = ""
    predicate_dialect: str = "ansi"
    column_masks: List[dict] = field(default_factory=list)
    denied_columns: List[str] = field(default_factory=list)
    ttl_seconds: int = 0


class RLSUpstreamUnavailableError(Exception):
    """上游权限服务不可用，且无可用 stale 缓存兜底。

    由 RLSAwareSQLExecutor 捕获，按 fail_strategy 决定是拒绝还是放行。
    """


# ---------------------------------------------------------------------------
# 主类
# ---------------------------------------------------------------------------


class RLSClient:
    """行级权限谓词客户端。

    提供 batch_fetch 接口，供 RLSAwareSQLExecutor 使用。
    不应在 chat scene 或 AWEL operator 里直接调用，统一由 Executor 托管。

    Example::

        client = RLSClient.from_config(rls_config)
        rules = await client.batch_fetch(principal, [
            RLSTableRef("mysql_prod", "sales", "orders"),
            RLSTableRef("mysql_prod", "sales", "customers"),
        ])
        for rule in rules:
            if not rule.allowed:
                raise PermissionError(f"无权访问表 {rule.table}")
            print(rule.predicate)
    """

    def __init__(
        self,
        upstream_url: str,
        upstream_timeout_ms: int = 800,
        local_ttl_seconds: int = 60,
        redis_ttl_seconds: int = 300,
        stale_fallback_seconds: int = 1800,
        redis_url: Optional[str] = None,
    ):
        """
        Args:
            upstream_url:            上游权限服务地址，如 http://auth-svc/v1/rls/batch-query。
            upstream_timeout_ms:     HTTP 请求超时，单位毫秒。
            local_ttl_seconds:       进程内 LRU 缓存的有效期。
            redis_ttl_seconds:       Redis 缓存的有效期（多实例共享）。
            stale_fallback_seconds:  上游故障时允许使用的最长 stale 缓存年龄。
            redis_url:               Redis 连接串；为空则不使用 Redis。
        """
        self._upstream_url = upstream_url
        self._upstream_timeout = upstream_timeout_ms / 1000
        self._local_ttl = local_ttl_seconds
        self._redis_ttl = redis_ttl_seconds
        self._stale_ttl = stale_fallback_seconds
        self._redis_url = redis_url

        # TODO(实现阶段): 初始化 cachetools.TTLCache 作为 L1 LRU
        # TODO(实现阶段): 按需初始化 redis.asyncio.Redis 作为 L2
        self._l1_cache: dict = {}
        self._redis = None

    @classmethod
    def from_config(cls, config) -> "RLSClient":
        """从 serve.rls / serve.rls.cache 配置块构建实例。

        config 通常来自 RLSConfig pydantic 模型，
        由 component_configs.py 在应用启动时注入。
        """
        # TODO(实现阶段): 解析 config 各字段
        raise NotImplementedError

    # ------------------------------------------------------------------
    # 核心接口
    # ------------------------------------------------------------------

    async def batch_fetch(
        self,
        principal: "Principal",
        tables: List[RLSTableRef],
    ) -> List[RLSRule]:
        """批量拉取多张表的 RLS 规则，与 tables 参数一一对应。

        执行顺序：
          1. 对每张表查 L1（进程内 LRU）；
          2. L1 miss → 查 L2（Redis）；
          3. 仍 miss 的表聚合后一次性调上游；
          4. 上游失败 → 用 stale 缓存兜底或抛 RLSUpstreamUnavailableError。

        Args:
            principal: 当前请求的用户身份，包含 user_id、sys_code、roles。
            tables:    SQL 中涉及的所有表（已去重，含子查询/CTE/自连接 alias）。

        Returns:
            与 tables 顺序一一对应的 RLSRule 列表。
            调用方不应假设顺序会重排，请按索引对应。

        Raises:
            RLSUpstreamUnavailableError: 上游不可用且无 stale 缓存。
        """
        # TODO(实现阶段):
        #   cache_keys = [self._make_key(principal, t) for t in tables]
        #   hits, misses = self._check_l1(cache_keys)
        #   ...
        raise NotImplementedError

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _make_cache_key(
        self, principal: "Principal", table: RLSTableRef
    ) -> str:
        """构造缓存键。

        格式：{user_id}:{sys_code}:{roles_hash}:{datasource}:{schema}:{table}

        roles_hash 取 sorted(roles) 的 sha256 前 8 位，
        保证角色变化后缓存自动失效。
        """
        roles_hash = hashlib.sha256(
            ",".join(sorted(principal.roles)).encode()
        ).hexdigest()[:8]
        return (
            f"{principal.user_id}:{principal.sys_code}:{roles_hash}"
            f":{table.datasource}:{table.schema}:{table.table}"
        )

    async def _fetch_from_upstream(
        self,
        principal: "Principal",
        tables: List[RLSTableRef],
    ) -> List[RLSRule]:
        """直接调用上游权限服务，不经过缓存。

        仅在 batch_fetch 内部调用。
        调用失败应由 batch_fetch 根据 stale 缓存情况决策，
        本方法直接 raise，不吞异常。
        """
        # TODO(实现阶段):
        #   payload = self._build_request_payload(principal, tables)
        #   async with httpx.AsyncClient(timeout=self._upstream_timeout) as c:
        #       resp = await c.post(self._upstream_url, json=payload)
        #       resp.raise_for_status()
        #       return self._parse_response(resp.json(), tables)
        raise NotImplementedError

    def _parse_response(self, body: dict, tables: List[RLSTableRef]) -> List[RLSRule]:
        """把上游 JSON 响应解析成 RLSRule 列表，并与 tables 顺序对齐。

        如果上游返回中某张表缺失（上游 bug），按 allowed=False 填充，
        保持 fail-close 语义。
        """
        # TODO(实现阶段)
        raise NotImplementedError

    def invalidate(self, user_id: str, sys_code: str, table: Optional[str] = None):
        """主动使缓存失效。

        供上游通过 webhook / MQ 推送权限变更事件时调用。

        Args:
            user_id:  被变更的用户；None 表示全租户刷新（慎用）。
            sys_code: 租户编码。
            table:    指定表名；None 表示该用户的所有表。
        """
        # TODO(实现阶段): 按前缀 scan L1 / L2 del
        raise NotImplementedError
