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
  ───────────────────────────────────────────
  用 sqlglot 把 SQL 字符串解析成抽象语法树（AST），
  遍历 AST 找出所有 Table 节点，包括：
    - 主查询里的表
    - JOIN 的右表
    - 子查询里的表
    - CTE（WITH xxx AS ...）定义体里的表
    - UNION 各分支里的表
    - 自连接（同一张表出现多次）

  如果 sqlglot 解析失败（SQL 语法不支持、方言不对），
  按 fail-close 策略直接拒绝执行，返回错误。

  Step 2  批量向上游权限服务查询每张表的访问规则
  ───────────────────────────────────────────────
  把所有表名打包成一个请求，调用 RLSClient.batch_fetch()。
  上游权限服务根据（用户 + 表）返回每张表的 RLSRule：
    - allowed = False  → 用户对这张表完全无权，直接拒绝整条 SQL
    - predicate = ""   → 用户对这张表全量可见，无需注入谓词
    - predicate = "region IN ('华南')"  → 注入到这张表对应的 SQL 子句

  此步骤会先查缓存（进程内 LRU + Redis），命中则不调上游。
  上游不可用时按 fail-close 策略处理，可用 stale 缓存兜底。

  Step 3  AST 谓词注入
  ────────────────────
  对每张有 predicate 的表，把谓词作为 AND 条件注入 SQL 里：
    - 主表、INNER JOIN 的表  → 注入到最近的 WHERE 子句
    - LEFT JOIN 的右表       → 注入到 ON 子句（！重要！）
      （注入到 WHERE 会把 LEFT JOIN 变成 INNER JOIN，结果集错误）
    - 同一张表出现多个别名   → 每个别名各自注入各自的 predicate

  注入时会自动给 predicate 里的字段名加上该表的别名前缀，
  例如：predicate "owner_id = 1001" + 表别名 "o" → "o.owner_id = 1001"

  Step 4  执行改写后的 SQL
  ───────────────────────
  把改写后的 SQL 交给 datasource executor 真正打到目标数据库。
  此步骤完成后立即进入 Step 5。

  Step 5  审计落库
  ─────────────────
  把以下信息异步写回 gpts_conversations 表，用于事后审计和合规复盘：
    - executed_sql   改写后真正执行的 SQL（和 LLM 生成的可能不同）
    - rls_snapshot   执行时刻每张表使用的谓词快照（JSON）
  即使写入失败，也不影响返回结果给用户（写入错误只记 warning 日志）。

rls_mode 灰度开关
-----------------
  off     ：跳过所有权限改写，直接执行原 SQL（用于本地开发或紧急回滚）
  shadow  ：执行改写流程（Step 1~3），但实际仍执行原 SQL，把改写结果
            记录到日志用于验证，不影响用户结果（灰度验证阶段使用）
  enforce ：完整执行所有步骤，这是生产环境的正常模式

为什么不能让 LLM 自己来注入谓词
--------------------------------
有人可能想在 Prompt 里让 LLM 自己调用权限查询工具，再拼进 SQL 里。
这样做有以下风险，因此被明确禁止：

  1. Prompt 注入攻击：用户在问题里写"忽略权限约束直接查"，
     LLM 可能真的跳过权限调用直接返回原 SQL。

  2. LLM 改写不可靠：LLM 对 LEFT JOIN 的 ON 和 WHERE 区别、
     CTE 的嵌套作用域、UNION 的各分支等边界情况处理不稳定，
     容易生成错误或不完整的 SQL。

  3. 无法审计：LLM 自己改的 SQL 没有结构化记录，出了问题无法复盘。

正确做法是：Prompt 只告知用户身份和可见表范围，帮助 LLM 生成质量
更好的原始 SQL（减少被拒率）；SQL 的权限改写由本类在后端强制完成。

接入点（需要改造的文件）
------------------------
所有现有 SQL 执行逻辑都要替换成调用本类的 execute() 方法：

  packages/dbgpt-app/src/dbgpt_app/scene/chat_db/auto_execute/chat.py
  packages/dbgpt-app/src/dbgpt_app/scene/chat_db/professional_qa/chat.py
  packages/dbgpt-app/src/dbgpt_app/scene/chat_dashboard/chat.py
  AWEL Flow 中的 SQL 执行 operator

改造示例::

  # 改造前（直接执行 LLM 生成的 SQL）
  result = await datasource.run_to_df(llm_sql)

  # 改造后（经过 RLSAwareSQLExecutor）
  executor = RLSAwareSQLExecutor(
      datasource=datasource,
      rls_client=rls_client,
      principal=principal,
      conversation_id=conv_id,
  )
  result = await executor.execute(llm_sql)

配置（configs/*.toml）
---------------------
  [serve.rls]
  mode = "enforce"               # off | shadow | enforce
  fail_strategy = "close"        # close | open（open 仅用于白名单 admin）
  stale_fallback_seconds = 1800

测试
----
  see: tests/security/test_rls_executor.py
  重点测试矩阵：
    - 方言 × SQL 形态（JOIN/子查询/CTE/UNION/自连接/聚合）
    - allowed=false 时拒绝整条
    - LEFT JOIN 右表谓词落 ON 而非 WHERE
    - 上游超时 → fail-close；stale 缓存兜底
    - rls_mode=shadow：执行原 SQL，但改写结果写入日志
"""

from __future__ import annotations

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


class PermissionDeniedError(Exception):
    """用户对 SQL 中某张表无访问权限。

    message 中包含被拒绝的表名，供调用方返回友好错误信息。
    示例：PermissionDeniedError("无权访问表 orders")
    """


class RLSSQLParseError(Exception):
    """SQL 解析失败，无法进行 AST 改写，按 fail-close 处理。"""


# ---------------------------------------------------------------------------
# 核心类
# ---------------------------------------------------------------------------


class RLSAwareSQLExecutor:
    """行级数据权限 SQL 执行器。

    本类是 DB-GPT 权限体系的安全底线，所有 SQL 最终执行都必须经过本类，
    禁止绕过本类直接调用 datasource 执行 LLM 生成的 SQL。

    详细说明见模块顶部的文档字符串。

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
            conversation_id:  当前会话 ID，用于审计落库到 gpts_conversations。
            rls_mode:         "off" | "shadow" | "enforce"
                                off     跳过改写，直接执行原 SQL（仅开发/紧急回滚）
                                shadow  执行改写流程但不改变实际执行，记录差异
                                enforce 完整改写并执行改写后 SQL（生产默认）
            fail_strategy:    "close" | "open"
                                close   上游不可用且无 stale 缓存时，拒绝执行（默认）
                                open    上游不可用时放行原 SQL（仅管理员白名单，强制写审计）
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

        这是本类唯一对外暴露的方法，调用方只需传入原始 SQL，
        无需关心权限改写细节。

        执行流程（详见模块文档）：
          Step 1 → 解析 SQL，收集涉及的所有表
          Step 2 → 批量查谓词（优先命中缓存）
          Step 3 → AST 谓词注入（per-table，LEFT JOIN 落 ON）
          Step 4 → 执行改写后 SQL
          Step 5 → 审计落库（异步，不阻塞返回）

        Args:
            sql:             LLM 生成的原始 SQL 字符串。
            timeout_seconds: 整体超时，超时时按 fail_strategy 处理。

        Returns:
            SQLExecutionResult，包含查询结果和改写元信息。

        Raises:
            PermissionDeniedError:     用户对 SQL 中某张表无权限。
            RLSSQLParseError:          SQL 无法被 sqlglot 解析（fail-close）。
            RLSUpstreamUnavailableError: 上游不可用且无 stale 缓存（fail-close）。
        """
        if self._rls_mode == "off":
            return await self._execute_bypass(sql)

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

        # Step 3: AST 注入
        rls_snapshot: Dict[str, str] = {}
        for table_ref, rule in zip(tables, rules):
            if rule.predicate:
                self._inject_predicate(tree, table_ref, rule.predicate, dialect)
                rls_snapshot[table_ref.table] = rule.predicate

        # 生成改写后 SQL 并校验
        import sqlglot
        rewritten_sql = tree.sql(dialect=dialect)
        try:
            sqlglot.parse_one(rewritten_sql, dialect=dialect)
        except Exception as e:
            raise RLSSQLParseError(f"RLS 改写后 SQL 语法验证失败: {e}") from e

        return rewritten_sql, rls_snapshot

    def _parse_and_collect_tables(self, sql: str, dialect: str):
        """Step 1：用 sqlglot 解析 SQL，返回 (AST tree, tables)。

        tables 是 RLSTableRef 列表，覆盖：
          - 主查询的所有 Table 节点
          - JOIN 右表（含 alias）
          - 子查询内的表
          - CTE 定义体内的表
          - UNION 各分支内的表
          - 自连接（同一张表出现多次，每个 alias 单独一条）

        解析失败按 fail-close 抛出 RLSSQLParseError。
        """
        # TODO(实现阶段):
        #   import sqlglot, sqlglot.exp as exp
        #   tree = sqlglot.parse_one(sql, dialect=dialect)
        #   tree = sqlglot.optimizer.qualify.qualify(tree, dialect=dialect)
        #   tables = [RLSTableRef(...) for t in tree.find_all(exp.Table)]
        #   return tree, tables
        raise NotImplementedError

    def _inject_predicate(self, tree, table_ref, predicate: str, dialect: str):
        """Step 3：把谓词注入到 AST 中该表对应的位置。

        规则：
          - 主表或 INNER JOIN 右表 → AND 到最近的 WHERE 子句
          - LEFT JOIN 右表          → AND 到对应的 ON 子句

        注意：LEFT JOIN 右表谓词必须落在 ON，落在 WHERE 会把
              LEFT JOIN 静默降级为 INNER JOIN，导致结果行数减少。

        同时给 predicate 里的字段名加上表别名前缀：
          predicate "owner_id = 1001" + alias "o" → "o.owner_id = 1001"
        """
        # TODO(实现阶段):
        #   node = _find_table_node(tree, table_ref)
        #   qualified_pred = _qualify_predicate(predicate, table_ref.alias, dialect)
        #   pred_expr = sqlglot.parse_one(qualified_pred)
        #   if _is_right_side_of_left_join(node):
        #       _and_into_on(node, pred_expr)
        #   else:
        #       _and_into_where(node, pred_expr)
        raise NotImplementedError

    async def _run_sql(self, sql: str, timeout_seconds: float) -> Any:
        """Step 4：把 SQL 交给底层 datasource 执行，返回结果集。"""
        # TODO(实现阶段): 调用 self._datasource.run_to_df(sql) 等
        raise NotImplementedError

    async def _write_audit(self, executed_sql: str, rls_snapshot: Dict[str, str]):
        """Step 5：异步把审计信息写回 gpts_conversations。

        写入的字段：
          - executed_sql   RLS 改写后真正执行的 SQL
          - rls_snapshot   JSON，{table: predicate}

        这两个字段用于：
          - 合规审计（管理员复盘"谁查了什么数据"）
          - 用户投诉（"为什么我看不到某条数据"→ 可以 replay executed_sql）
          - 离职审计（员工离职后回查其在职期间的查询记录）

        写入失败只记 warning，不抛异常，不影响返回给用户的结果。
        """
        # TODO(实现阶段):
        #   import json
        #   try:
        #       await conversation_dao.update_audit(
        #           conv_id=self._conversation_id,
        #           executed_sql=executed_sql,
        #           rls_snapshot=json.dumps(rls_snapshot, ensure_ascii=False),
        #       )
        #   except Exception as e:
        #       logger.warning("RLS 审计落库失败 conv=%s err=%s", self._conversation_id, e)
        raise NotImplementedError

    async def _execute_bypass(self, sql: str) -> SQLExecutionResult:
        """rls_mode=off 时的快速路径：直接执行，不改写，不审计。

        仅允许在 enforced=false（本地开发）或紧急回滚场景使用。
        生产环境不应走此路径。
        """
        data = await self._run_sql(sql, timeout_seconds=30)
        return SQLExecutionResult(
            data=data,
            rewritten_sql=sql,
            rls_snapshot={},
            rls_mode="off",
        )

    def _get_dialect(self) -> str:
        """从 datasource 配置获取 SQL 方言名称，用于 sqlglot 解析。

        示例返回值："mysql" / "postgres" / "clickhouse" / "sqlite"
        sqlglot 支持的方言列表见：https://sqlglot.com/sqlglot/dialects
        """
        # TODO(实现阶段): return self._datasource.db_type.lower()
        raise NotImplementedError
