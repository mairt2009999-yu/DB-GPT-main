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
from typing import TYPE_CHECKING, Any, Dict

from sqlalchemy.exc import DBAPIError, OperationalError

from dbgpt_app.security.exceptions import PermissionDeniedError, RLSSQLParseError

if TYPE_CHECKING:
    from dbgpt_app.security.principal import Principal
    from dbgpt_app.security.rls_client import RLSClient

logger = logging.getLogger(__name__)
RLS_LOG_PREFIX = ">>>>>>>>>>> [SQL拦截/RLS]"


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
        print(result.rewritten_sql)  # 带谓词的改写后 SQL
        print(
            result.rls_snapshot
        )  # {"orders": "region IN ('华南') AND owner_id = 1001"}
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
        logger.info(
            "%s 初始化 SQL 拦截器 | conv=%s mode=%s failStrategy=%s "
            "datasource=%s dbType=%s userId=%s roles=%s sysCode=%s",
            RLS_LOG_PREFIX,
            self._conversation_id,
            self._rls_mode,
            self._fail_strategy,
            self._get_datasource_name(),
            getattr(self._datasource, "db_type", None),
            getattr(self._principal, "user_id", None),
            getattr(self._principal, "roles", None),
            getattr(self._principal, "sys_code", None),
        )

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
        logger.info(
            "%s 进入 SQL 拦截执行入口 | conv=%s mode=%s timeout=%s 执行前原始SQL=%s",
            RLS_LOG_PREFIX,
            self._conversation_id,
            self._rls_mode,
            timeout_seconds,
            sql,
        )
        if self._rls_mode == "off":
            return await self._execute_bypass(sql, timeout_seconds)

        rewritten_sql, rls_snapshot = await self._rewrite(sql)
        logger.info(
            "%s SQL 改写完成 | conv=%s mode=%s 改写后SQL=%s rlsSnapshot=%s",
            RLS_LOG_PREFIX,
            self._conversation_id,
            self._rls_mode,
            rewritten_sql,
            rls_snapshot,
        )

        if self._rls_mode == "shadow":
            # shadow 模式：记录改写结果但实际执行原 SQL
            logger.info(
                "[RLS shadow] conv=%s original=%r rewritten=%r snapshot=%r",
                self._conversation_id,
                sql,
                rewritten_sql,
                rls_snapshot,
            )
            data = await self._run_sql(sql, timeout_seconds)
        else:
            # enforce 模式：执行改写后的 SQL
            logger.info(
                "%s enforce模式准备执行改写后SQL | conv=%s 数据库执行前SQL=%s",
                RLS_LOG_PREFIX,
                self._conversation_id,
                rewritten_sql,
            )
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
        logger.info(
            "%s Step1 解析执行前SQL | conv=%s dialect=%s datasource=%s "
            "执行前原始SQL=%s",
            RLS_LOG_PREFIX,
            self._conversation_id,
            dialect,
            self._get_datasource_name(),
            sql,
        )
        tree, tables = self._parse_and_collect_tables(sql, dialect)
        logger.info(
            "%s Step1 收集SQL涉及表 | conv=%s tables=%s",
            RLS_LOG_PREFIX,
            self._conversation_id,
            [
                {
                    "datasource": ref.datasource,
                    "schema": ref.schema,
                    "table": ref.table,
                    "alias": ref.alias,
                    "columns": list(ref.columns),
                }
                for ref in tables
            ],
        )

        # Step 2: 批量查谓词
        logger.info(
            "%s Step2 拉取行级权限规则 | conv=%s userId=%s tableCount=%s",
            RLS_LOG_PREFIX,
            self._conversation_id,
            getattr(self._principal, "user_id", None),
            len(tables),
        )
        rules = await self._rls_client.batch_fetch(self._principal, tables)
        logger.info(
            "%s Step2 行级权限规则返回 | conv=%s rules=%s",
            RLS_LOG_PREFIX,
            self._conversation_id,
            [
                {
                    "table": rule.table,
                    "allowed": rule.allowed,
                    "predicate": rule.predicate,
                }
                for rule in rules
            ],
        )

        # 检查 allowed=False
        for rule in rules:
            if not rule.allowed:
                logger.warning(
                    "%s permission denied | conv=%s table=%s userId=%s",
                    RLS_LOG_PREFIX,
                    self._conversation_id,
                    rule.table,
                    getattr(self._principal, "user_id", None),
                )
                raise PermissionDeniedError(
                    f"当前用户无权访问表 [{rule.table}]，已拒绝执行"
                )

        # Step 3: AST 注入（委托 rls_injector.inject）
        logger.info(
            "%s Step3 注入RLS谓词 | conv=%s",
            RLS_LOG_PREFIX,
            self._conversation_id,
        )
        rewritten_sql, rls_snapshot = rls_injector.inject(tree, tables, rules, dialect)

        return rewritten_sql, rls_snapshot

    def _parse_and_collect_tables(self, sql: str, dialect: str):
        """Step 1：用 sqlglot 解析 SQL，返回 (AST tree, tables)。"""
        from dbgpt_app.security import rls_parser

        default_schema = self._resolve_default_schema(dialect)
        tree, tables = rls_parser.parse_and_collect(
            sql,
            dialect,
            datasource=self._get_datasource_name(),
            default_schema=default_schema,
        )
        return tree, self._enrich_table_columns(tables)

    def _enrich_table_columns(self, tables):
        """Attach datasource column metadata to table refs when it is available."""
        for ref in tables:
            columns = self._get_table_column_names(ref)
            if columns:
                ref.columns = columns
        return tables

    def _get_table_column_names(self, ref) -> tuple[str, ...]:
        raw_columns = self._read_columns_from_inspector(ref)
        columns = self._normalize_column_names(raw_columns)
        if columns:
            return columns

        raw_columns = self._read_columns_from_datasource(ref)
        return self._normalize_column_names(raw_columns)

    def _read_columns_from_datasource(self, ref):
        get_columns = getattr(self._datasource, "get_columns", None)
        if not callable(get_columns):
            return None
        try:
            return get_columns(ref.table)
        except Exception as exc:
            logger.debug(
                "%s datasource get_columns failed | conv=%s table=%s schema=%s "
                "errType=%s err=%s",
                RLS_LOG_PREFIX,
                self._conversation_id,
                ref.table,
                ref.schema,
                type(exc).__name__,
                exc,
            )
            return None

    def _read_columns_from_inspector(self, ref):
        inspector = getattr(self._datasource, "_inspector", None)
        get_columns = getattr(inspector, "get_columns", None)
        if not callable(get_columns):
            return None
        try:
            if ref.schema:
                return get_columns(ref.table, schema=ref.schema)
            return get_columns(ref.table)
        except Exception as exc:
            logger.debug(
                "%s inspector get_columns failed | conv=%s table=%s schema=%s "
                "errType=%s err=%s",
                RLS_LOG_PREFIX,
                self._conversation_id,
                ref.table,
                ref.schema,
                type(exc).__name__,
                exc,
            )
            return None

    def _normalize_column_names(self, raw_columns) -> tuple[str, ...]:
        if not isinstance(raw_columns, (list, tuple, set)):
            return ()

        names: list[str] = []
        for column in raw_columns:
            name = None
            if isinstance(column, dict):
                name = column.get("name")
            else:
                name = getattr(column, "name", None)
            if isinstance(name, str) and name:
                names.append(name)
        return tuple(names)

    async def _run_sql(self, sql: str, timeout_seconds: float) -> Any:
        """Step 4：把 SQL 交给底层 datasource 执行，返回结果集。"""
        logger.info(
            "%s Step4 数据库执行前SQL | conv=%s timeout=%s sql=%s",
            RLS_LOG_PREFIX,
            self._conversation_id,
            timeout_seconds,
            sql,
        )
        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, self._datasource.run_to_df, sql),
            timeout=timeout_seconds,
        )

    async def _write_audit(self, executed_sql: str, rls_snapshot: Dict[str, str]):
        """Step 5：结构化 JSON 审计日志（仅 logger.info，不写 DB，不抛异常）。"""
        try:
            logger.info(
                json.dumps(
                    {
                        "conv_id": self._conversation_id,
                        "mode": self._rls_mode,
                        "user_id": getattr(self._principal, "user_id", None),
                        "executed_sql": executed_sql,
                        "snapshot": rls_snapshot,
                    },
                    ensure_ascii=False,
                )
            )
        except Exception as e:
            logger.warning(
                "RLS 审计日志写入失败 conv=%s err=%s", self._conversation_id, e
            )

    async def _execute_bypass(
        self, sql: str, timeout_seconds: float = 30
    ) -> SQLExecutionResult:
        """rls_mode=off 时的快速路径：直接执行，不改写，不审计。"""
        logger.info(
            "%s mode=off 跳过RLS改写直接执行 | conv=%s 数据库执行前SQL=%s",
            RLS_LOG_PREFIX,
            self._conversation_id,
            sql,
        )
        data = await self._run_sql(sql, timeout_seconds)
        return SQLExecutionResult(
            data=data,
            rewritten_sql=sql,
            rls_snapshot={},
            rls_mode="off",
        )

    def _get_dialect(self) -> str:
        """从 datasource 配置获取 SQL 方言名称，用于 sqlglot 解析。"""
        raw_dialect = (
            self._string_datasource_attr("db_dialect")
            or self._string_datasource_attr("dialect")
            or self._string_datasource_attr("db_type")
        )
        dialect = str(raw_dialect or "").lower()
        aliases = {
            "postgresql": "postgres",
            "pgsql": "postgres",
            "postgresql+psycopg2": "postgres",
        }
        return aliases.get(dialect, dialect)

    def _string_datasource_attr(self, name: str) -> str:
        value = getattr(self._datasource, name, None)
        if isinstance(value, str):
            return value
        if callable(value):
            try:
                value = value()
            except Exception:
                return ""
            return value if isinstance(value, str) else ""
        return ""

    def _get_datasource_name(self) -> str:
        """Return a stable datasource/database name without assuming db_name exists."""
        db_name = self._string_datasource_attr("db_name")
        if db_name:
            return db_name

        engine = getattr(self._datasource, "_engine", None)
        engine_url = getattr(engine, "url", None)
        engine_database = getattr(engine_url, "database", None)
        if isinstance(engine_database, str) and engine_database:
            return engine_database

        getter = getattr(self._datasource, "get_current_db_name", None)
        if callable(getter):
            try:
                current_db = getter()
            except Exception as exc:
                logger.warning(
                    "%s datasource name fallback failed | conv=%s errType=%s err=%s",
                    RLS_LOG_PREFIX,
                    self._conversation_id,
                    type(exc).__name__,
                    exc,
                )
            else:
                if isinstance(current_db, str) and current_db:
                    return current_db

        return ""

    def _get_default_schema(self) -> str:
        """Return connector default schema for unqualified table names."""
        return self._resolve_default_schema(self._get_dialect())

    def _resolve_default_schema(self, dialect: str) -> str:
        configured_schema = self._configured_default_schema()
        if configured_schema:
            logger.info(
                "%s resolved default schema | conv=%s defaultSchema=%s "
                "source=configured_schema",
                RLS_LOG_PREFIX,
                self._conversation_id,
                configured_schema,
            )
            return configured_schema

        if self._is_postgres_dialect(dialect):
            getter = self._get_declared_datasource_callable("get_current_schema")
            if getter is not None:
                schema = self._get_postgres_current_schema_with_retry(getter)
                logger.info(
                    "%s resolved default schema | conv=%s defaultSchema=%s "
                    "source=current_schema",
                    RLS_LOG_PREFIX,
                    self._conversation_id,
                    schema,
                )
                return schema

        logger.info(
            "%s resolved default schema | conv=%s defaultSchema=%s source=%s",
            RLS_LOG_PREFIX,
            self._conversation_id,
            "",
            "none",
        )
        return ""

    def _configured_default_schema(self) -> str:
        return (
            self._string_datasource_attr("_schema") or self._string_datasource_attr(
                "schema"
            )
        )

    def _get_postgres_current_schema_with_retry(self, getter) -> str:
        last_error: BaseException | None = None
        for attempt in range(2):
            try:
                schema = getter()
            except (OperationalError, DBAPIError) as exc:
                last_error = exc
                logger.warning(
                    "%s current_schema lookup failed | conv=%s attempt=%s "
                    "errType=%s err=%s",
                    RLS_LOG_PREFIX,
                    self._conversation_id,
                    attempt + 1,
                    type(exc).__name__,
                    exc,
                )
                if attempt == 0:
                    self._dispose_datasource_engine()
                    continue
                break
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "%s current_schema lookup failed | conv=%s attempt=%s "
                    "errType=%s err=%s",
                    RLS_LOG_PREFIX,
                    self._conversation_id,
                    attempt + 1,
                    type(exc).__name__,
                    exc,
                )
                break
            if isinstance(schema, str) and schema:
                if attempt:
                    logger.info(
                        "%s current_schema lookup recovered after retry | conv=%s "
                        "schema=%s",
                        RLS_LOG_PREFIX,
                        self._conversation_id,
                        schema,
                    )
                return schema
            last_error = ValueError(f"empty current schema: {schema!r}")
            break

        raise RLSSQLParseError(
            "Unable to resolve PostgreSQL current schema for RLS enforcement"
        ) from last_error

    def _dispose_datasource_engine(self) -> None:
        engine = getattr(self._datasource, "_engine", None)
        dispose = getattr(engine, "dispose", None)
        if not callable(dispose):
            return
        try:
            dispose()
            logger.warning(
                "%s disposed datasource engine after current_schema failure | conv=%s",
                RLS_LOG_PREFIX,
                self._conversation_id,
            )
        except Exception as exc:
            logger.warning(
                "%s datasource engine dispose failed | conv=%s errType=%s err=%s",
                RLS_LOG_PREFIX,
                self._conversation_id,
                type(exc).__name__,
                exc,
            )

    def _get_declared_datasource_callable(self, name: str):
        datasource_dict = getattr(self._datasource, "__dict__", {})
        if isinstance(datasource_dict, dict) and name in datasource_dict:
            value = getattr(self._datasource, name, None)
            return value if callable(value) else None

        class_value = getattr(type(self._datasource), name, None)
        if not callable(class_value):
            return None
        value = getattr(self._datasource, name, None)
        return value if callable(value) else None

    def _is_postgres_dialect(self, dialect: str) -> bool:
        return (dialect or "").lower() in {"postgres", "postgresql"}
