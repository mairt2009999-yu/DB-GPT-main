"""
rls_executor.py  ——  行级数据权限（Row-Level Security）SQL 执行器
================================================================

这个类是 DB-GPT 权限体系的安全底线。
==================================

背景
----
DB-GPT 让 LLM（大语言模型）把用户的自然语言问题翻译成 SQL，
再拿到目标数据库里执行，最后把结果渲染成图表或报表返回给用户。

但 LLM 生成的 SQL 没有任何权限约束——它会按照数据库里的全量数据生成查询。
如果直接执行这条 SQL，不同的用户都会拿到同样的数据，无法做到"A 只能看华南
区的订单，B 只能看华北区的订单"这种行级隔离。

职责
----
RLSAwareSQLExecutor 拦截每一条 LLM 生成的 SQL，强制注入当前用户对应的
行级权限谓词（WHERE 条件），再执行改写后的 SQL，确保用户只能拿到被授权的数据。

  「LLM 生成的 SQL」→ 「RLSAwareSQLExecutor」→ 「改写后的 SQL」→ 「数据库」

执行流程（共 5 步）
------------------

  Step 1  sqlglot 解析 SQL，收集所有涉及的表
  Step 2  批量向上游权限服务查询每张表的访问规则
  Step 3  AST 谓词注入（委托 rls_injector.inject）
  Step 4  执行改写后的 SQL
  Step 5  审计落库（logger.info JSON，不抛异常）

rls_mode 灰度开关
-----------------
  off     ：跳过所有权限改写，直接执行原 SQL
  shadow  ：执行改写流程，但实际仍执行原 SQL，记录差异
  enforce ：完整执行所有步骤（生产默认）

测试
----
  see: tests/security/test_rls_executor.py
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from dbgpt_app.security.principal import Principal
    from dbgpt_app.security.rls_client import RLSClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 返回类型
# ---------------------------------------------------------------------------


@dataclass
class SQLExecutionResult:
    """execute() 的返回结果。

    Attributes:
        data:           查询结果（DataFrame 或 list[dict]，由底层 datasource 决定）
        rewritten_sql:  RLS 改写后真正执行的 SQL；rls_mode=off 时与原 SQL 相同
        rls_snapshot:   每张表使用的谓词快照，格式 {"table_name": "predicate"}
                        rls_mode=off 时为空字典
        rls_mode:       本次执行使用的 rls_mode（off / shadow / enforce）
    """

    data: Any
    rewritten_sql: str
    rls_snapshot: Dict[str, str]
    rls_mode: str


from dbgpt_app.security.exceptions import (
    PermissionDeniedError,
    RLSSQLParseError,
    RLSUpstreamUnavailableError,
    RLSUnsupportedSQLError,
)


# ---------------------------------------------------------------------------
# 核心类
# ---------------------------------------------------------------------------


class RLSAwareSQLExecutor:
    """行级数据权限 SQL 执行器。

    本类是 DB-GPT 权限体系的安全底线，所有 SQL 最终执行都必须经过本类，
    禁止绕过本类直接调用 datasource 执行 LLM 生成的 SQL。

    Example::

        executor = RLSAwareSQLExecutor(
            datasource=datasource,
            rls_client=rls_client,
            principal=principal,
            conversation_id="conv-abc123",
            rls_mode="enforce",
        )
        result = await executor.execute("SELECT * FROM orders WHERE dt = '2024-01'")
        print(result.rewritten_sql)   # 带谓词的改写后 SQL
        print(result.rls_snapshot)    # {"orders": "region IN ('华南') AND owner_id = 1001"}
    """

    def __init__(
        self,
        datasource,
        rls_client: "RLSClient",
        principal: "Principal",
        conversation_id: str,
        rls_mode: str = "enforce",
        fail_strategy: str = "close",
    ):
        """
        Args:
            datasource:       目标数据源连接（ConnectorManager 返回的 connector）。
            rls_client:       RLSClient 实例，负责向上游查谓词。
            principal:        当前请求的用户身份（user_id, sys_code, roles 等）。
            conversation_id:  当前会话 ID，用于审计。
            rls_mode:         "off" | "shadow" | "enforce"
            fail_strategy:    "close" | "open"
        """
        self._datasource = datasource
        self._rls_client = rls_client
        self._principal = principal
        self._conversation_id = conversation_id
        self._rls_mode = rls_mode
        self._fail_strategy = fail_strategy

    # ------------------------------------------------------------------
    # 对外唯一入口
    # ------------------------------------------------------------------

    async def execute(
        self,
        sql: str,
        *,
        timeout_seconds: float = 30,
    ) -> SQLExecutionResult:
        """执行一条 LLM 生成的 SQL，自动完成 RLS 改写与审计。

        Args:
            sql:             LLM 生成的原始 SQL 字符串。
            timeout_seconds: 整体超时（秒）。

        Returns:
            SQLExecutionResult，包含查询结果和改写元信息。

        Raises:
            PermissionDeniedError:        用户对 SQL 中某张表无权限。
            RLSSQLParseError:             SQL 无法被 sqlglot 解析（fail-close）。
            RLSUpstreamUnavailableError:  上游不可用且无 stale 缓存（fail-close）。
        """
        if self._rls_mode == "off":
            return await self._execute_bypass(sql, timeout_seconds)

        rewritten_sql, rls_snapshot = await self._rewrite(sql)

        if self._rls_mode == "shadow":
            # shadow 模式：记录改写结果但实际执行原 SQL
            logger.info(
                "[RLS shadow] conv=%s original=%r rewritten=%r snapshot=%r",
                self._conversation_id, sql, rewritten_sql, rls_snapshot,
            )
            data = await self._run_sql(sql, timeout_seconds)
        else:
            # enforce 模式：执行改写后的 SQL
            data = await self._run_sql(rewritten_sql, timeout_seconds)

        # 审计落库（异步，失败只记 warning，不影响用户结果）
        await self._write_audit(rewritten_sql, rls_snapshot)

        return SQLExecutionResult(
            data=data,
            rewritten_sql=rewritten_sql,
            rls_snapshot=rls_snapshot,
            rls_mode=self._rls_mode,
        )

    # ------------------------------------------------------------------
    # 内部各步骤实现
    # ------------------------------------------------------------------

    async def _rewrite(self, sql: str):
        """Step 1~3：解析、查谓词、AST 注入，返回 (rewritten_sql, rls_snapshot)。"""
        from dbgpt_app.security import rls_injector

        # Step 1: 解析 SQL
        dialect = self._get_dialect()
        tree, tables = self._parse_and_collect_tables(sql, dialect)

        # Step 2: 批量查谓词
        rules = await self._rls_client.batch_fetch(self._principal, tables)

        # 检查 allowed=False
        for rule in rules:
            if not rule.allowed:
                raise PermissionDeniedError(
                    f"当前用户无权访问表 [{rule.table}]，已拒绝执行"
                )

        # Step 3: AST 注入（委托 rls_injector.inject）
        rewritten_sql, rls_snapshot = rls_injector.inject(tree, tables, rules, dialect)

        return rewritten_sql, rls_snapshot

    def _parse_and_collect_tables(self, sql: str, dialect: str):
        """Step 1：用 sqlglot 解析 SQL，返回 (AST tree, tables)。"""
        from dbgpt_app.security import rls_parser
        return rls_parser.parse_and_collect(
            sql, dialect, datasource=self._datasource.db_name
        )

    async def _run_sql(self, sql: str, timeout_seconds: float) -> Any:
        """Step 4：把 SQL 交给底层 datasource 执行，返回结果集。"""
        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, self._datasource.run_to_df, sql),
            timeout=timeout_seconds,
        )

    async def _write_audit(self, executed_sql: str, rls_snapshot: Dict[str, str]):
        """Step 5：结构化 JSON 审计日志（仅 logger.info，不写 DB，不抛异常）。"""
        try:
            logger.info(json.dumps({
                "conv_id": self._conversation_id,
                "mode": self._rls_mode,
                "user_id": getattr(self._principal, "user_id", None),
                "executed_sql": executed_sql,
                "snapshot": rls_snapshot,
            }, ensure_ascii=False))
        except Exception as e:
            logger.warning("RLS 审计日志写入失败 conv=%s err=%s", self._conversation_id, e)

    async def _execute_bypass(self, sql: str, timeout_seconds: float = 30) -> SQLExecutionResult:
        """rls_mode=off 时的快速路径：直接执行，不改写，不审计。"""
        data = await self._run_sql(sql, timeout_seconds)
        return SQLExecutionResult(
            data=data,
            rewritten_sql=sql,
            rls_snapshot={},
            rls_mode="off",
        )

    def _get_dialect(self) -> str:
        """从 datasource 配置获取 SQL 方言名称，用于 sqlglot 解析。"""
        return self._datasource.db_type.lower()
