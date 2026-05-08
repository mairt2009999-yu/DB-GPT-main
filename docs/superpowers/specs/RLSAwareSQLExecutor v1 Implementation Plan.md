# RLSAwareSQLExecutor v1 实施计划
> **致自动化执行者：** 必须使用 superpowers:subagent-driven-development（若支持子 Agent）或 superpowers:executing-plans 来执行本计划。各步骤使用复选框（`- [ ]`）语法追踪进度。
**目标：** 按照 `docs/superpowers/specs/2026-04-30-rls-aware-sql-executor-design.md` 的设计，以 TDD 方式完整实现 v1 安全模块（L3 行级权限）。
**架构：** LLM 生成的 SQL 在真正打到数据库之前，必须经过 `RLSAwareSQLExecutor.execute()`。该执行器解析 SQL AST，批量向上游服务拉取各表谓词，通过 sqlglot 注入后执行改写后的 SQL。三种模式：`off`（直通）、`shadow`（仅记录日志）、`enforce`（强制拦截）。
**技术栈：** Python 3.11、sqlglot、httpx、cachetools (TTLCache)、pytest、pytest-asyncio、FastAPI（仅用于 mock 上游）
**设计文档：** `docs/superpowers/specs/2026-04-30-rls-aware-sql-executor-design.md`
**关键约束（已与最新代码对齐）：**
* `RLSTableRef` 的权威定义在 `rls_client.py`，`rls_parser.py` 从那里导入，**不重复定义**。
* 异常类目前在 `rls_executor.py` 骨架中重复定义，必须先提取到 `exceptions.py`。
* 对外方法名为 `execute()`（非 `execute_to_df`），与现有骨架保持一致。
* `out_parser.py:138` 同步调用 `df = data(prompt_response.sql)`，因此 `do_action()` 必须返回一个接受 `sql: str` 并返回 DataFrame 的**同步**可调用对象。
* **不再自建 Principal 类**：`packages/dbgpt-app/src/dbgpt_app/microservice/context.py` 已提供 `RequestContext` 与 `get_current_request_context()`，由 `ContextMiddleware` 自动注入。`from_chat_param` 仅作为兜底适配器（无 contextvar 时使用）。
* **不再自建上游 batch 接口**：上游真实接口是 user-service 的 `getSqlFragmentByUserId`（即 `GET {prefix}/{user_id}/sql-fragment?tableCode=...`），已由 `microservice/user_service.py::UserServiceClient.get_sql_fragment_by_user_id(request_context, table_code) -> SqlFragment` 实现，通过 Nacos 服务发现。
* **`SqlFragment.sql_fragment`** 字段直接是 WHERE 谓词片段（示例：`create_by="1"`），DB-GPT 拿来后映射为 `RLSRule.predicate`。
* **`RLSClient` 重构为 user-service 适配器**：循环遍历每张表（**非 batch**），逐表调用 `UserServiceClient.get_sql_fragment_by_user_id`；HTTP 403 / `AuthorizationFailedError` → `RLSRule(allowed=False)`；`ServiceUnavailableError` → `RLSUpstreamUnavailableError`；本地 LRU 缓存键 `(user_id, sys_code, table_code)`。
* `mode=off` 时使用 `StubRLSClient`，直接返回 `allowed=True, predicate=""`，不发 HTTP 请求。
* v1 审计 = 仅 `logger.info` 输出结构化 JSON，不写数据库。
* **不再实现 `tools/rls_mock_upstream/`**（原 Task 12 取消）：实际联调使用真实 user-service + Nacos。
***
## 第一块：基础设施 — 依赖、异常、身份、配置
### 任务 1：添加依赖 + 创建 `__init__.py`
**文件：**
* 修改：`packages/dbgpt-app/pyproject.toml`
* 新建：`packages/dbgpt-app/src/dbgpt_app/security/__init__.py`
- [ ] **第 1 步：向 dbgpt-app 添加 sqlglot 和 cachetools**
在 `packages/dbgpt-app/pyproject.toml` 的 `dependencies` 列表中添加：
```toml
"sqlglot>=25.0.0",
"cachetools>=5.0.0",
```
- [ ] **第 2 步：安装新依赖**
运行：`uv sync --all-packages`
预期：无报错，sqlglot 可正常导入。
- [ ] **第 3 步：创建 security 包的 `__init__.py`**
新建空文件 `packages/dbgpt-app/src/dbgpt_app/security/__init__.py`。
- [ ] **第 4 步：验证导入正常**
运行：`uv run python -c "import sqlglot; import cachetools; print('OK')"`
预期：`OK`
- [ ] **第 5 步：提交**
```warp-runnable-command
git add packages/dbgpt-app/pyproject.toml packages/dbgpt-app/src/dbgpt_app/security/__init__.py
git commit -m "chore(security): add sqlglot + cachetools deps, init security package"
```
### 任务 2：`exceptions.py` — 统一 RLS 异常类
**文件：**
* 新建：`packages/dbgpt-app/src/dbgpt_app/security/exceptions.py`
* 修改：`packages/dbgpt-app/src/dbgpt_app/security/rls_executor.py`（第 176-185 行）
* 修改：`packages/dbgpt-app/src/dbgpt_app/security/rls_client.py`（第 148 行）
- [ ] **第 1 步：创建 `exceptions.py`**
```python
# packages/dbgpt-app/src/dbgpt_app/security/exceptions.py
class RLSError(Exception):
    """Parent for all RLS exceptions."""
class PermissionDeniedError(RLSError):
    """User lacks access to a table. message includes the table name."""
class RLSSQLParseError(RLSError):
    """sqlglot parse failed or post-rewrite validation failed."""
class RLSUpstreamUnavailableError(RLSError):
    """Upstream service unreachable with no stale cache available."""
class RLSUnsupportedSQLError(RLSError):
    """Non-SELECT statement or unsupported dialect."""
```
- [ ] **第 2 步：更新 `rls_executor.py` — 从 exceptions 导入，删除重复定义**
在 `rls_executor.py` 中，将第 176-185 行的本地 `PermissionDeniedError` 和 `RLSSQLParseError` 类定义替换为：
```python
from dbgpt_app.security.exceptions import (
    PermissionDeniedError,
    RLSSQLParseError,
    RLSUpstreamUnavailableError,
    RLSUnsupportedSQLError,
)
```
同时删除骨架 docstring 中对 `RLSUpstreamUnavailableError` 的本地类定义（import 已覆盖）。
- [ ] **第 3 步：更新 `rls_client.py` — 从 exceptions 导入 `RLSUpstreamUnavailableError`**
在 `rls_client.py` 中，将第 148 行的本地 `RLSUpstreamUnavailableError` 类定义替换为：
```python
from dbgpt_app.security.exceptions import RLSUpstreamUnavailableError
```
- [ ] **第 4 步：快速导入检验**
运行：`uv run python -c "from dbgpt_app.security.exceptions import PermissionDeniedError; print('OK')"`
预期：`OK`
- [ ] **第 5 步：提交**
```warp-runnable-command
git add packages/dbgpt-app/src/dbgpt_app/security/
git commit -m "feat(security): add exceptions.py, centralise RLS error hierarchy"
```
### 任务 3：`principal.py`（薄适配层 + 兜底）+ `tests/security/test_principal.py`
**说明：** `microservice/context.py::RequestContext` 已经是事实上的 Principal。本任务只在 `security/principal.py` 中提供：
1. `Principal` 类型别名（直接复用 `RequestContext`）
2. `from_chat_param(chat_param) -> RequestContext` 兜底适配器（contextvar 没值时使用，例如本地脚本/测试）
3. `current_principal()` 包装：优先 `get_current_request_context()`，兜底回退到 `from_chat_param`
**文件：**
* 新建：`packages/dbgpt-app/src/dbgpt_app/security/principal.py`
* 新建：`tests/security/__init__.py`
* 新建：`tests/security/conftest.py`
* 新建：`tests/security/test_principal.py`
- [ ] **第 1 步：编写失败测试（适配器 + contextvar 优先级）**
```python
# tests/security/test_principal.py
from dbgpt_app.microservice.context import RequestContext
from dbgpt_app.security.principal import (
    from_chat_param,
    current_principal,
)
def test_from_chat_param_user_name():
    from dbgpt_app.scene.base_chat import ChatParam
    from dbgpt_app.scene.base import ChatScene
    cp = ChatParam(
        chat_session_id="s1",
        current_user_input="hello",
        model_name="gpt-4",
        select_param="mydb",
        chat_mode=ChatScene.ChatWithDbExecute,
        user_name="bob",
        sys_code="tenant1",
    )
    p = from_chat_param(cp)
    assert p.user_id == "bob"
    assert p.sys_code == "tenant1"
def test_current_principal_uses_contextvar():
    from dbgpt_app.microservice.context import set_current_request_context, reset_current_request_context
    ctx = RequestContext(user_id="alice", sys_code="corp", roles=["ANALYST"])
    token = set_current_request_context(ctx)
    try:
        p = current_principal()
        assert p.user_id == "alice"
    finally:
        reset_current_request_context(token)
def test_current_principal_fallback_to_chat_param():
    from dbgpt_app.scene.base_chat import ChatParam
    from dbgpt_app.scene.base import ChatScene
    cp = ChatParam(
        chat_session_id="s1",
        current_user_input="hello",
        model_name="gpt-4",
        select_param="mydb",
        chat_mode=ChatScene.ChatWithDbExecute,
        user_name="bob",
        sys_code="tenant1",
    )
    # contextvar empty -> fallback to chat_param
    p = current_principal(chat_param=cp)
    assert p.user_id == "bob"
```
- [ ] **第 2 步：运行测试，确认失败**
运行：`uv run pytest tests/security/test_principal.py -v`
预期：ImportError / FAIL
- [ ] **第 3 步：实现 `principal.py`**
```python
# packages/dbgpt-app/src/dbgpt_app/security/principal.py
"""Principal 适配层：复用 microservice.context.RequestContext，提供 ChatParam 兜底适配。"""
from __future__ import annotations
from typing import Optional
from dbgpt_app.microservice.context import (
    RequestContext,
    get_current_request_context,
)
# 类型别名：security 子系统对外的“Principal”就是 RequestContext
Principal = RequestContext
_ADMIN_ROLES = frozenset([
    "ROLE_DBGPT_ADMIN",
    "ROLE_ADMIN",
])
def is_admin(principal: RequestContext) -> bool:
    return any(r in _ADMIN_ROLES for r in (principal.roles or []))
def from_chat_param(chat_param) -> RequestContext:
    """ChatParam 兜底适配（无 contextvar 时使用，如本地脚本/测试）。"""
    user_id = (getattr(chat_param, "user_name", "") or "").strip() or "anonymous"
    sys_code = getattr(chat_param, "sys_code", None) or None
    return RequestContext(user_id=user_id, sys_code=sys_code, roles=[])
def current_principal(chat_param: Optional[object] = None) -> RequestContext:
    """优先取 contextvar；为空时回退到 chat_param 适配。"""
    ctx = get_current_request_context()
    if ctx and ctx.user_id:
        return ctx
    if chat_param is not None:
        return from_chat_param(chat_param)
    return RequestContext(user_id="anonymous", roles=[])
```
- [ ] **第 4 步：创建 `tests/security/__init__.py`（空文件）和 `tests/security/conftest.py`**
```python
# tests/security/conftest.py
import pytest
from dbgpt_app.security.principal import Principal
@pytest.fixture
def alice() -> Principal:
    return Principal(user_id="alice", roles=("ANALYST",), sys_code="corp")
@pytest.fixture
def admin() -> Principal:
    return Principal(user_id="admin", roles=("ROLE_DBGPT_ADMIN",), sys_code="corp")
```
- [ ] **第 5 步：运行测试，确认全部通过**
运行：`uv run pytest tests/security/test_principal.py -v`
预期：全部 PASS
- [ ] **第 6 步：提交**
```warp-runnable-command
git add packages/dbgpt-app/src/dbgpt_app/security/principal.py tests/security/
git commit -m "feat(security): add Principal dataclass + from_chat_param adapter"
```
### 任务 4：`config.py`
**文件：**
* 新建：`packages/dbgpt-app/src/dbgpt_app/security/config.py`
- [ ] **第 1 步：创建 `config.py`**
```python
# packages/dbgpt-app/src/dbgpt_app/security/config.py
from __future__ import annotations
from typing import Literal
from dbgpt._private.pydantic import BaseModel
class RLSConfig(BaseModel):
    mode: Literal["off", "shadow", "enforce"] = "off"
    fail_strategy: Literal["close", "open"] = "close"  # v1: close only
    upstream_url: str = "http://localhost:9999"
    upstream_timeout_ms: int = 800
    local_ttl_seconds: int = 60
    stale_fallback_seconds: int = 1800
    admin_role_codes: list[str] = []
```
- [ ] **第 2 步：快速导入检验**
运行：`uv run python -c "from dbgpt_app.security.config import RLSConfig; print(RLSConfig())"`
预期：打印默认配置
- [ ] **第 3 步：提交**
```warp-runnable-command
git add packages/dbgpt-app/src/dbgpt_app/security/config.py
git commit -m "feat(security): add RLSConfig pydantic model"
```
***
## 第二块：SQL 解析与谓词注入（核心）
### 任务 5：`rls_parser.py` + `tests/security/test_rls_parser.py`
**文件：**
* 新建：`packages/dbgpt-app/src/dbgpt_app/security/rls_parser.py`
* 新建：`tests/security/test_rls_parser.py`
**注意：** `RLSTableRef` 的权威定义在 `rls_client.py`，`rls_parser.py` 从那里导入，**不重复定义**。
- [ ] **第 1 步：编写失败测试（约 15 个用例）**
```python
# tests/security/test_rls_parser.py
import pytest
from dbgpt_app.security.rls_parser import parse_and_collect, is_supported_dialect
from dbgpt_app.security.exceptions import RLSUnsupportedSQLError, RLSSQLParseError
def test_simple_select_mysql():
    _, refs = parse_and_collect("SELECT id FROM orders", "mysql", datasource="ds1")
    assert len(refs) == 1
    assert refs[0].table == "orders"
    assert refs[0].datasource == "ds1"
def test_inner_join_collects_both_tables():
    _, refs = parse_and_collect(
        "SELECT o.id FROM orders o JOIN customers c ON o.cid = c.id",
        "mysql", datasource="ds1"
    )
    tables = {r.table for r in refs}
    assert tables == {"orders", "customers"}
def test_left_join_collects_right_table():
    _, refs = parse_and_collect(
        "SELECT o.id FROM orders o LEFT JOIN items i ON o.id = i.oid",
        "mysql", datasource="ds1"
    )
    tables = {r.table for r in refs}
    assert tables == {"orders", "items"}
def test_subquery_collects_inner_table():
    _, refs = parse_and_collect(
        "SELECT * FROM (SELECT id FROM orders) sub",
        "sqlite", datasource="ds1"
    )
    tables = {r.table for r in refs}
    assert "orders" in tables
def test_cte_inner_table_collected_not_cte_name():
    sql = "WITH recent AS (SELECT id FROM orders) SELECT id FROM recent"
    _, refs = parse_and_collect(sql, "mysql", datasource="ds1")
    tables = {r.table for r in refs}
    # "recent" is a CTE name, not a real table
    assert "orders" in tables
    assert "recent" not in tables
def test_self_join_two_aliases():
    sql = "SELECT a.id, b.id FROM orders a JOIN orders b ON a.id = b.parent_id"
    _, refs = parse_and_collect(sql, "mysql", datasource="ds1")
    # Two refs for orders (two aliases)
    order_refs = [r for r in refs if r.table == "orders"]
    assert len(order_refs) == 2
    aliases = {r.alias for r in order_refs}
    assert aliases == {"a", "b"}
def test_non_select_raises():
    with pytest.raises(RLSUnsupportedSQLError):
        parse_and_collect("INSERT INTO orders VALUES (1)", "mysql", datasource="ds1")
def test_unsupported_dialect_raises():
    with pytest.raises(RLSUnsupportedSQLError):
        parse_and_collect("SELECT 1", "clickhouse", datasource="ds1")
def test_is_supported_dialect():
    assert is_supported_dialect("mysql")
    assert is_supported_dialect("postgres")
    assert is_supported_dialect("sqlite")
    assert not is_supported_dialect("clickhouse")
    assert not is_supported_dialect("oracle")
def test_postgres_schema_prefix():
    _, refs = parse_and_collect(
        "SELECT id FROM sales.orders", "postgres", datasource="ds1"
    )
    assert refs[0].table == "orders"
    assert refs[0].schema == "sales"
```
- [ ] **第 2 步：运行测试，确认失败**
运行：`uv run pytest tests/security/test_rls_parser.py -v`
预期：ImportError / FAIL
- [ ] **第 3 步：实现 `rls_parser.py`**
```python
# packages/dbgpt-app/src/dbgpt_app/security/rls_parser.py
"""Step 1 of RLSAwareSQLExecutor: parse SQL and collect real table references."""
from __future__ import annotations
import sqlglot
import sqlglot.expressions as exp
from dbgpt_app.security.rls_client import RLSTableRef  # authority definition
from dbgpt_app.security.exceptions import RLSSQLParseError, RLSUnsupportedSQLError
_SUPPORTED_DIALECTS = {"mysql", "postgres", "sqlite"}
def is_supported_dialect(dialect: str) -> bool:
    return dialect.lower() in _SUPPORTED_DIALECTS
def parse_and_collect(
    sql: str,
    dialect: str,
    datasource: str = "",
    default_schema: str = "",
) -> tuple[exp.Expression, list[RLSTableRef]]:
    """
    Parse sql and return (AST, table refs).
    CTE names are excluded from refs.
    Self-joins produce one ref per alias.
    Raises:
        RLSUnsupportedSQLError: non-SELECT or unsupported dialect
        RLSSQLParseError: sqlglot parse failed
    """
    if not is_supported_dialect(dialect):
        raise RLSUnsupportedSQLError(f"Dialect '{dialect}' is not supported in v1")
    try:
        tree = sqlglot.parse_one(sql, dialect=dialect)
    except Exception as e:
        raise RLSSQLParseError(f"sqlglot parse failed: {e}") from e
    if not isinstance(tree, exp.Select):
        raise RLSUnsupportedSQLError("Only SELECT statements are supported")
    # Collect CTE names so we can exclude them
    cte_names: set[str] = set()
    for cte in tree.find_all(exp.CTE):
        if cte.alias:
            cte_names.add(cte.alias.lower())
    seen: list[tuple[str, str, str]] = []  # (table, schema, alias) dedup
    refs: list[RLSTableRef] = []
    for table_node in tree.find_all(exp.Table):
        name = table_node.name
        if not name or name.lower() in cte_names:
            continue
        schema = table_node.db or default_schema
        alias = table_node.alias or name
        key = (name.lower(), schema.lower(), alias.lower())
        if key in seen:
            continue
        seen.append(key)
        refs.append(RLSTableRef(
            datasource=datasource,
            schema=schema,
            table=name,
            alias=alias,
        ))
    return tree, refs
```
- [ ] **第 4 步：运行测试，确认全部通过**
运行：`uv run pytest tests/security/test_rls_parser.py -v`
预期：全部 PASS
- [ ] **第 5 步：提交**
```warp-runnable-command
git add packages/dbgpt-app/src/dbgpt_app/security/rls_parser.py tests/security/test_rls_parser.py
git commit -m "feat(security): implement rls_parser — SQL parse + table collection"
```
### 任务 6：`rls_injector.py` + `tests/security/test_rls_injector.py`（核心 ★）
**文件：**
* 新建：`packages/dbgpt-app/src/dbgpt_app/security/rls_injector.py`
* 新建：`tests/security/test_rls_injector.py`
这是最复杂、最关键的模块。核心安全规则：**LEFT JOIN 右表谓词必须注入 ON 子句，不能注入 WHERE**（否则会将 LEFT JOIN 静默降级为 INNER JOIN）。
- [ ] **第 1 步：编写失败测试（约 25 个，覆盖完整矩阵）**
```python
# tests/security/test_rls_injector.py
import pytest
import sqlglot
from dbgpt_app.security.rls_parser import parse_and_collect
from dbgpt_app.security.rls_injector import inject
from dbgpt_app.security.rls_client import RLSTableRef, RLSRule
from dbgpt_app.security.exceptions import RLSSQLParseError
def _inject(sql: str, predicates: dict[str, str], dialect="mysql") -> str:
    """Helper: parse sql, build rules from predicates dict, inject, return rewritten sql."""
    tree, refs = parse_and_collect(sql, dialect, datasource="ds")
    rules = [
        RLSRule(table=r.table, allowed=True, predicate=predicates.get(r.table, ""))
        for r in refs
    ]
    rewritten, _ = inject(tree, refs, rules, dialect)
    return rewritten
def _parses(sql: str, dialect="mysql") -> bool:
    try:
        sqlglot.parse_one(sql, dialect=dialect)
        return True
    except Exception:
        return False
# ----- Simple SELECT -----
def test_simple_select_no_existing_where():
    out = _inject("SELECT id FROM orders", {"orders": "region = '华南'"})
    assert "华南" in out
    assert _parses(out)
def test_simple_select_existing_where():
    out = _inject("SELECT id FROM orders WHERE status = 1", {"orders": "region = '华南'"})
    assert "status" in out and "华南" in out
    assert _parses(out)
def test_empty_predicate_skipped():
    out = _inject("SELECT id FROM orders", {"orders": ""})
    # No extra WHERE added
    assert "WHERE" not in out.upper()
# ----- INNER JOIN -----
def test_inner_join_predicate_in_where_not_on():
    sql = "SELECT o.id FROM orders o JOIN customers c ON o.cid = c.id"
    out = _inject(sql, {"customers": "region = 'A'"})
    out_upper = out.upper()
    assert "WHERE" in out_upper
    assert _parses(out)
# ----- LEFT JOIN (safety critical) -----
def test_left_join_right_table_predicate_in_on_not_where():
    """CRITICAL: predicate for LEFT JOIN right table must land in ON."""
    sql = "SELECT o.id, i.name FROM orders o LEFT JOIN items i ON o.id = i.oid"
    out = _inject(sql, {"items": "region = 'B'"})
    # Verify it went into ON clause: check ON ... region
    assert "region" in out
    # Rewritten SQL must still parse
    assert _parses(out)
    # Verify result is still a LEFT JOIN (not downgraded to INNER)
    assert "LEFT JOIN" in out.upper() or "LEFT OUTER JOIN" in out.upper()
def test_left_join_right_table_predicate_not_in_where():
    sql = "SELECT o.id, i.name FROM orders o LEFT JOIN items i ON o.id = i.oid"
    out = _inject(sql, {"items": "region = 'B'"})
    # If WHERE appeared, it would silently downgrade to INNER JOIN — assert not
    # The WHERE from the main table (if any) is OK; but items predicate must not be alone in WHERE
    parsed = sqlglot.parse_one(out, dialect="mysql")
    # Check items predicate is inside ON
    on_clauses = list(parsed.find_all(sqlglot.exp.Join))
    for join in on_clauses:
        if join.side and join.side.upper() == "LEFT":
            on_text = join.args.get("on", "")
            assert "region" in str(on_text)
# ----- Subquery -----
def test_subquery_inner_table_predicate():
    sql = "SELECT * FROM (SELECT id FROM orders) sub"
    out = _inject(sql, {"orders": "region = 'C'"})
    assert "region" in out
    assert _parses(out, "sqlite")
# ----- CTE -----
def test_cte_inner_table_predicate():
    sql = "WITH recent AS (SELECT id FROM orders) SELECT id FROM recent"
    out = _inject(sql, {"orders": "region = 'D'"})
    assert "region" in out
    assert _parses(out)
# ----- Self-join -----
def test_self_join_both_aliases_injected():
    sql = "SELECT a.id, b.id FROM orders a JOIN orders b ON a.id = b.parent_id"
    out = _inject(sql, {"orders": "owner_id = 99"})
    # predicate injected twice (once per alias)
    assert out.count("99") >= 2
    assert _parses(out)
# ----- Postgres -----
def test_postgres_dialect():
    out = _inject("SELECT id FROM orders", {"orders": "region = 'A'"}, dialect="postgres")
    assert "region" in out
    assert _parses(out, "postgres")
# ----- SQLite -----
def test_sqlite_dialect():
    out = _inject("SELECT id FROM orders", {"orders": "region = 'A'"}, dialect="sqlite")
    assert "region" in out
# ----- Snapshot -----
def test_snapshot_populated():
    tree, refs = parse_and_collect("SELECT id FROM orders", "mysql", datasource="ds")
    rules = [RLSRule(table="orders", allowed=True, predicate="region = 'X'")]
    _, snapshot = inject(tree, refs, rules, "mysql")
    assert snapshot == {"orders": "region = 'X'"}
def test_snapshot_empty_when_no_predicate():
    tree, refs = parse_and_collect("SELECT id FROM orders", "mysql", datasource="ds")
    rules = [RLSRule(table="orders", allowed=True, predicate="")]
    _, snapshot = inject(tree, refs, rules, "mysql")
    assert snapshot == {}
```
- [ ] **第 2 步：运行测试，确认失败**
运行：`uv run pytest tests/security/test_rls_injector.py -v`
预期：ImportError / FAIL
- [ ] **第 3 步：实现 `rls_injector.py`**
实现要点：
* 使用 `sqlglot.optimizer.qualify.qualify(tree)` 在注入前使所有列引用无歧义。
* 通过检查 `join.side.upper() == "LEFT"` 识别 LEFT JOIN 右表。
* 注入 WHERE 时用 `sqlglot.exp.And` 追加到现有 WHERE，或新建 WHERE。
* 注入 ON 时将谓词 AND 到现有 ON 子句。
* 注入完成后调用 `tree.sql(dialect)` 生成 SQL，再 `sqlglot.parse_one(rewritten, dialect)` 做语法校验。
```python
# packages/dbgpt-app/src/dbgpt_app/security/rls_injector.py
"""Step 3 of RLSAwareSQLExecutor: inject RLS predicates into the SQL AST."""
from __future__ import annotations
import sqlglot
import sqlglot.expressions as exp
from dbgpt_app.security.rls_client import RLSTableRef, RLSRule
from dbgpt_app.security.exceptions import RLSSQLParseError
def inject(
    tree: exp.Expression,
    refs: list[RLSTableRef],
    rules: list[RLSRule],
    dialect: str,
) -> tuple[str, dict[str, str]]:
    """
    Inject per-table RLS predicates into the AST.
    Returns (rewritten_sql, snapshot).
    LEFT JOIN right-table predicates go into ON; all others go into WHERE.
    """
    snapshot: dict[str, str] = {}
    left_join_aliases = _collect_left_join_right_aliases(tree)
    for ref, rule in zip(refs, rules):
        if not rule.predicate:
            continue
        snapshot[ref.table] = rule.predicate
        pred_expr = sqlglot.parse_one(rule.predicate, dialect=dialect)
        if ref.alias in left_join_aliases:
            _inject_into_on(tree, ref.alias, pred_expr)
        else:
            _inject_into_where(tree, pred_expr)
    rewritten = tree.sql(dialect=dialect)
    try:
        sqlglot.parse_one(rewritten, dialect=dialect)
    except Exception as e:
        raise RLSSQLParseError(f"Post-rewrite validation failed: {e}") from e
    return rewritten, snapshot
def _collect_left_join_right_aliases(tree: exp.Expression) -> set[str]:
    """Return aliases of tables on the right side of a LEFT JOIN."""
    aliases: set[str] = set()
    for join in tree.find_all(exp.Join):
        if getattr(join, "side", None) and join.side.upper() in ("LEFT", "LEFT OUTER"):
            tbl = join.this
            if isinstance(tbl, exp.Table):
                alias = tbl.alias or tbl.name
                aliases.add(alias.lower())
    return aliases
def _inject_into_where(tree: exp.Expression, pred_expr: exp.Expression) -> None:
    """AND pred_expr into the WHERE clause of the outermost SELECT."""
    select = tree if isinstance(tree, exp.Select) else tree.find(exp.Select)
    if select is None:
        return
    existing_where = select.args.get("where")
    if existing_where:
        new_where = exp.Where(this=exp.And(
            this=existing_where.this,
            expression=pred_expr,
        ))
    else:
        new_where = exp.Where(this=pred_expr)
    select.set("where", new_where)
def _inject_into_on(tree: exp.Expression, alias: str, pred_expr: exp.Expression) -> None:
    """AND pred_expr into the ON clause of the LEFT JOIN matching alias."""
    for join in tree.find_all(exp.Join):
        if not (getattr(join, "side", None) and join.side.upper() in ("LEFT", "LEFT OUTER")):
            continue
        tbl = join.this
        if not isinstance(tbl, exp.Table):
            continue
        tbl_alias = (tbl.alias or tbl.name).lower()
        if tbl_alias != alias.lower():
            continue
        existing_on = join.args.get("on")
        if existing_on:
            new_on = exp.And(this=existing_on, expression=pred_expr)
        else:
            new_on = pred_expr
        join.set("on", new_on)
        return
```
- [ ] **第 4 步：运行测试，确认全部通过（失败则修复后重跑）**
运行：`uv run pytest tests/security/test_rls_injector.py -v`
预期：全部 PASS。若有失败，修复实现后重新运行。
- [ ] **第 5 步：提交**
```warp-runnable-command
git add packages/dbgpt-app/src/dbgpt_app/security/rls_injector.py tests/security/test_rls_injector.py
git commit -m "feat(security): implement rls_injector — AST predicate injection with LEFT JOIN safety"
```
***
## 第三块：RLS 客户端（重写为 user-service 适配器）
### 任务 7：实现 `rls_client.py` + `tests/security/test_rls_client.py`
**重大变更说明：** 上游接口已变更为 user-service 的 `getSqlFragmentByUserId`（每次调用查询单张表）。`RLSClient.batch_fetch` 内部循环遍历每张表，逐表调用 `UserServiceClient.get_sql_fragment_by_user_id(request_context, table_code)`，再将结果装配为 `List[RLSRule]`。
**错误映射：**
* 成功（含空 fragment）→ `RLSRule(table=t.table, allowed=True, predicate=sql_fragment.sql_fragment)`
* `AuthorizationFailedError`（HTTP 403）→ `RLSRule(table=t.table, allowed=False)`
* `AuthenticationFailedError`（HTTP 401/404）→ 直接抛出，由 executor 处理（fail-close）
* `ServiceUnavailableError`/网络异常 → 抛 `RLSUpstreamUnavailableError`，先尝试 stale 缓存
**缓存键：** `(user_id, sys_code, table_code)` —— 不再包含 datasource/schema/roles_hash（v1 简化）。
**文件：**
* 修改：`packages/dbgpt-app/src/dbgpt_app/security/rls_client.py`（实现所有 `NotImplementedError` 桩；增加 `from_user_service` 工厂）
* 新建：`packages/dbgpt-app/src/dbgpt_app/security/stub_rls_client.py`
* 新建：`tests/security/test_rls_client.py`
- [ ] **第 1 步：编写失败测试（约 10 个用例）**
```python
# tests/security/test_rls_client.py
import pytest
from unittest.mock import AsyncMock
from dbgpt_app.microservice.context import RequestContext
from dbgpt_app.microservice.user_service import (
    SqlFragment,
    AuthorizationFailedError,
    ServiceUnavailableError,
)
from dbgpt_app.security.rls_client import RLSClient, RLSTableRef, RLSRule
from dbgpt_app.security.exceptions import RLSUpstreamUnavailableError
@pytest.fixture
def principal():
    return RequestContext(user_id="alice", sys_code="corp", roles=["ANALYST"])
@pytest.fixture
def tables():
    return [RLSTableRef(datasource="ds", schema="sales", table="orders", alias="orders")]
@pytest.mark.asyncio
async def test_batch_fetch_calls_user_service(principal, tables):
    mock_user_svc = AsyncMock()
    mock_user_svc.get_sql_fragment_by_user_id = AsyncMock(
        return_value=SqlFragment(user_id="alice", table_code="orders", sql_fragment='create_by="1"')
    )
    client = RLSClient(user_service=mock_user_svc, local_ttl_seconds=60)
    rules = await client.batch_fetch(principal, tables)
    assert len(rules) == 1
    assert rules[0].allowed is True
    assert rules[0].predicate == 'create_by="1"'
    mock_user_svc.get_sql_fragment_by_user_id.assert_awaited_once_with(principal, "orders")
@pytest.mark.asyncio
async def test_batch_fetch_empty_fragment_means_allowed(principal, tables):
    mock_user_svc = AsyncMock()
    mock_user_svc.get_sql_fragment_by_user_id = AsyncMock(
        return_value=SqlFragment(user_id="alice", table_code="orders", sql_fragment="")
    )
    client = RLSClient(user_service=mock_user_svc)
    rules = await client.batch_fetch(principal, tables)
    assert rules[0].allowed is True
    assert rules[0].predicate == ""
@pytest.mark.asyncio
async def test_batch_fetch_authorization_failed_means_denied(principal, tables):
    mock_user_svc = AsyncMock()
    mock_user_svc.get_sql_fragment_by_user_id = AsyncMock(
        side_effect=AuthorizationFailedError("forbidden")
    )
    client = RLSClient(user_service=mock_user_svc)
    rules = await client.batch_fetch(principal, tables)
    assert rules[0].allowed is False
@pytest.mark.asyncio
async def test_batch_fetch_service_unavailable_raises(principal, tables):
    mock_user_svc = AsyncMock()
    mock_user_svc.get_sql_fragment_by_user_id = AsyncMock(
        side_effect=ServiceUnavailableError("down")
    )
    client = RLSClient(user_service=mock_user_svc)
    with pytest.raises(RLSUpstreamUnavailableError):
        await client.batch_fetch(principal, tables)
@pytest.mark.asyncio
async def test_batch_fetch_l1_cache_hit(principal, tables):
    mock_user_svc = AsyncMock()
    mock_user_svc.get_sql_fragment_by_user_id = AsyncMock(
        return_value=SqlFragment(user_id="alice", table_code="orders", sql_fragment='create_by="1"')
    )
    client = RLSClient(user_service=mock_user_svc, local_ttl_seconds=60)
    await client.batch_fetch(principal, tables)
    await client.batch_fetch(principal, tables)
    assert mock_user_svc.get_sql_fragment_by_user_id.await_count == 1
@pytest.mark.asyncio
async def test_batch_fetch_stale_fallback_on_failure(principal, tables):
    mock_user_svc = AsyncMock()
    mock_user_svc.get_sql_fragment_by_user_id = AsyncMock(
        side_effect=[
            SqlFragment(user_id="alice", table_code="orders", sql_fragment='create_by="1"'),
            ServiceUnavailableError("down"),
        ]
    )
    client = RLSClient(
        user_service=mock_user_svc, local_ttl_seconds=0, stale_fallback_seconds=3600
    )
    await client.batch_fetch(principal, tables)
    client._l1_cache.clear()  # force L1 expiry
    rules = await client.batch_fetch(principal, tables)
    assert rules[0].allowed is True
    assert rules[0].predicate == 'create_by="1"'
@pytest.mark.asyncio
async def test_batch_fetch_two_tables_two_calls(principal):
    mock_user_svc = AsyncMock()
    mock_user_svc.get_sql_fragment_by_user_id = AsyncMock(
        side_effect=[
            SqlFragment(user_id="alice", table_code="orders", sql_fragment='a=1'),
            SqlFragment(user_id="alice", table_code="customers", sql_fragment='b=2'),
        ]
    )
    client = RLSClient(user_service=mock_user_svc)
    refs = [
        RLSTableRef(datasource="ds", schema="s", table="orders", alias="o"),
        RLSTableRef(datasource="ds", schema="s", table="customers", alias="c"),
    ]
    rules = await client.batch_fetch(principal, refs)
    assert [r.predicate for r in rules] == ['a=1', 'b=2']
    assert mock_user_svc.get_sql_fragment_by_user_id.await_count == 2
def test_make_cache_key_contains_user_and_table(principal, tables):
    client = RLSClient(user_service=AsyncMock())
    key = client._make_cache_key(principal, tables[0])
    assert "alice" in key
    assert "orders" in key
```
- [ ] **第 2 步：运行测试，确认失败**
运行：`uv run pytest tests/security/test_rls_client.py -v`
预期：FAIL
- [ ] **第 3 步：实现 `rls_client.py` 各桩方法（user-service 适配器版本）**
关键实现要点：
* `__init__(self, user_service, local_ttl_seconds=60, stale_fallback_seconds=1800)`：注入 `UserServiceClient`，用 `cachetools.TTLCache` 初始化 L1 缓存（`_l1_cache`），另维护 `_stale_cache: dict`（无 TTL，存最近一次成功的 `RLSRule`）作兜底。
* `from_user_service(cls, system_app)` 类方法：从 `SystemApp` 取 `UserServiceClient` 单例，构造 `RLSClient`。
* `batch_fetch(principal: RequestContext, tables)`：对每个 ref 查 L1（缓存键 `(user_id, sys_code, table_code)`）；未命中则调 `_fetch_one(principal, ref)`；上游失败时查 `_stale_cache`，若也无则抛 `RLSUpstreamUnavailableError`。
* `_fetch_one(principal, ref)`：调用 `self._user_service.get_sql_fragment_by_user_id(principal, ref.table)`；映射 `SqlFragment.sql_fragment` → `RLSRule.predicate`；处理 `AuthorizationFailedError` → `allowed=False`；`ServiceUnavailableError` / 网络异常 → 抛出由 `batch_fetch` 处理。
* 删除原 `_fetch_from_upstream`、`_parse_response`、`from_config` 三个方法（不再使用 batch HTTP 接口）。
* `invalidate(user_id, sys_code, table=None)`：按前缀清除 L1 缓存条目。
* 顶部导入：`from cachetools import TTLCache`、`from dbgpt_app.microservice.user_service import UserServiceClient, AuthorizationFailedError, ServiceUnavailableError`、`from dbgpt_app.microservice.context import RequestContext`。
- [ ] **第 4 步：创建 `stub_rls_client.py`（用于 `mode=off`）**
```python
# packages/dbgpt-app/src/dbgpt_app/security/stub_rls_client.py
"""StubRLSClient — no-op for mode=off."""
from __future__ import annotations
from typing import List
from dbgpt_app.microservice.context import RequestContext
from dbgpt_app.security.rls_client import RLSTableRef, RLSRule
class StubRLSClient:
    """No-op RLS client. Returns allowed=True, predicate='' for all tables."""
    async def batch_fetch(self, principal: RequestContext, refs: List[RLSTableRef]) -> List[RLSRule]:
        return [RLSRule(table=r.table, allowed=True, predicate="") for r in refs]
    def invalidate(self, user_id: str, sys_code: str = None, table: str = None) -> None:
        pass
```
- [ ] **第 5 步：运行测试，确认全部通过**
运行：`uv run pytest tests/security/test_rls_client.py -v`
预期：全部 PASS
- [ ] **第 6 步：提交**
```warp-runnable-command
git add packages/dbgpt-app/src/dbgpt_app/security/rls_client.py \
         packages/dbgpt-app/src/dbgpt_app/security/stub_rls_client.py \
         tests/security/test_rls_client.py
git commit -m "feat(security): implement RLSClient with LRU + stale fallback; add StubRLSClient"
```
***
## 第四块：RLS 执行器 + bypass 检测
### 任务 8：实现 `rls_executor.py` + `tests/security/test_rls_executor.py`
**文件：**
* 修改：`packages/dbgpt-app/src/dbgpt_app/security/rls_executor.py`（实现所有 `NotImplementedError` 桩）
* 新建：`tests/security/test_rls_executor.py`
**`rls_executor.py` 实现要点：**
* `_get_dialect()`：调用 `self._datasource.db_type.lower()`，返回如 `"mysql"`、`"sqlite"`。
* `_parse_and_collect_tables(sql, dialect)`：委托 `rls_parser.parse_and_collect(sql, dialect, datasource=self._datasource.db_name)`。
* `_inject_predicate()`：**删除**此薄包装层，在 `_rewrite()` 中直接调用 `rls_injector.inject(tree, tables, rules, dialect)`（替换现有 per-table 循环）。
* `_run_sql(sql, timeout_seconds)`：使用 `asyncio.wait_for(asyncio.get_event_loop().run_in_executor(None, self._datasource.run_to_df, sql), timeout=timeout_seconds)`。
* `_write_audit(executed_sql, rls_snapshot)`：`logger.info(json.dumps({"conv_id": ..., "mode": ..., "executed_sql": ..., "snapshot": ...}))`，不抛异常。
* 重构 `_rewrite()`，改为调用 `rls_injector.inject()` 直接返回 `(rewritten_sql, snapshot)`，简化现有循环逻辑。
- [ ] **第 1 步：编写失败测试（约 20 个用例）**
```python
# tests/security/test_rls_executor.py
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd
from dbgpt_app.security.rls_executor import RLSAwareSQLExecutor, SQLExecutionResult
from dbgpt_app.security.principal import Principal
from dbgpt_app.security.rls_client import RLSTableRef, RLSRule
from dbgpt_app.security.stub_rls_client import StubRLSClient
from dbgpt_app.security.exceptions import PermissionDeniedError, RLSUpstreamUnavailableError
@pytest.fixture
def datasource():
    ds = MagicMock()
    ds.db_type = "sqlite"
    ds.db_name = "testdb"
    df = pd.DataFrame({"id": [1, 2]})
    ds.run_to_df = MagicMock(return_value=df)
    return ds
@pytest.fixture
def principal():
    return Principal(user_id="alice", roles=("ANALYST",))
def _make_executor(datasource, rls_client, principal, mode="enforce"):
    return RLSAwareSQLExecutor(
        datasource=datasource,
        rls_client=rls_client,
        principal=principal,
        conversation_id="conv1",
        rls_mode=mode,
    )
@pytest.mark.asyncio
async def test_mode_off_bypasses_rls(datasource, principal):
    executor = _make_executor(datasource, StubRLSClient(), principal, mode="off")
    result = await executor.execute("SELECT * FROM orders")
    assert result.rls_mode == "off"
    assert result.rls_snapshot == {}
@pytest.mark.asyncio
async def test_mode_enforce_rewrites_sql(datasource, principal):
    mock_client = AsyncMock()
    mock_client.batch_fetch = AsyncMock(return_value=[
        RLSRule(table="orders", allowed=True, predicate="region = 'A'")
    ])
    executor = _make_executor(datasource, mock_client, principal, mode="enforce")
    result = await executor.execute("SELECT id FROM orders")
    assert "region" in result.rewritten_sql
    assert result.rls_mode == "enforce"
@pytest.mark.asyncio
async def test_mode_shadow_executes_original_sql(datasource, principal):
    mock_client = AsyncMock()
    mock_client.batch_fetch = AsyncMock(return_value=[
        RLSRule(table="orders", allowed=True, predicate="region = 'A'")
    ])
    executor = _make_executor(datasource, mock_client, principal, mode="shadow")
    result = await executor.execute("SELECT id FROM orders")
    # Shadow mode: executed_sql is original, but rewritten_sql is computed
    assert result.rls_mode == "shadow"
    assert "region" in result.rewritten_sql
    assert datasource.run_to_df.called
    # Should have called with ORIGINAL sql
    called_sql = datasource.run_to_df.call_args[0][0]
    assert "region" not in called_sql  # original sql, no predicate injected
@pytest.mark.asyncio
async def test_permission_denied_raises(datasource, principal):
    mock_client = AsyncMock()
    mock_client.batch_fetch = AsyncMock(return_value=[
        RLSRule(table="orders", allowed=False, predicate="")
    ])
    executor = _make_executor(datasource, mock_client, principal, mode="enforce")
    with pytest.raises(PermissionDeniedError):
        await executor.execute("SELECT id FROM orders")
@pytest.mark.asyncio
async def test_upstream_unavailable_fail_close(datasource, principal):
    mock_client = AsyncMock()
    mock_client.batch_fetch = AsyncMock(side_effect=RLSUpstreamUnavailableError("down"))
    executor = _make_executor(datasource, mock_client, principal, mode="enforce")
    with pytest.raises(RLSUpstreamUnavailableError):
        await executor.execute("SELECT id FROM orders")
@pytest.mark.asyncio
async def test_result_contains_data_and_metadata(datasource, principal):
    executor = _make_executor(datasource, StubRLSClient(), principal, mode="off")
    result = await executor.execute("SELECT * FROM orders")
    assert isinstance(result, SQLExecutionResult)
    assert result.data is not None
    assert isinstance(result.rls_snapshot, dict)
```
- [ ] **第 2 步：运行测试，确认失败**
运行：`uv run pytest tests/security/test_rls_executor.py -v`
预期：FAIL
- [ ] **第 3 步：实现 `rls_executor.py` 所有 `NotImplementedError` 桩**
重点：
1. `_get_dialect()` → `return self._datasource.db_type.lower()`
2. `_parse_and_collect_tables(sql, dialect)` → 委托 `rls_parser.parse_and_collect(...)`，删除 `_inject_predicate` 方法。
3. 重构 `_rewrite()` → 直接调用 `rls_injector.inject(tree, tables, rules, dialect)` 返回 `(rewritten_sql, rls_snapshot)`。
4. `_run_sql(sql, timeout_seconds)` → `asyncio.wait_for(loop.run_in_executor(None, self._datasource.run_to_df, sql), timeout=timeout_seconds)`。
5. `_write_audit(executed_sql, rls_snapshot)` → `logger.info(json.dumps({...}))`，不抛异常。
- [ ] **第 4 步：运行测试，确认全部通过**
运行：`uv run pytest tests/security/test_rls_executor.py -v`
预期：全部 PASS
- [ ] **第 5 步：提交**
```warp-runnable-command
git add packages/dbgpt-app/src/dbgpt_app/security/rls_executor.py tests/security/test_rls_executor.py
git commit -m "feat(security): implement RLSAwareSQLExecutor — 5-step pipeline"
```
### 任务 9：`bypass_detector.py`
**文件：**
* 新建：`packages/dbgpt-app/src/dbgpt_app/security/bypass_detector.py`
- [ ] **第 1 步：创建 `bypass_detector.py`**
```python
# packages/dbgpt-app/src/dbgpt_app/security/bypass_detector.py
"""Detect calls to datasource.run_to_df that bypass RLSAwareSQLExecutor."""
from __future__ import annotations
import inspect
import logging
logger = logging.getLogger(__name__)
_RLS_EXECUTOR_CLASS = "RLSAwareSQLExecutor"
def warn_if_bypass(connector_method_name: str) -> None:
    """Log WARNING if the call stack does not go through RLSAwareSQLExecutor.
    
    Decorate RDBMSConnector.run_to_df to call this.
    v1: observe only, do not block.
    """
    stack = inspect.stack()
    for frame_info in stack:
        if _RLS_EXECUTOR_CLASS in frame_info.filename or _RLS_EXECUTOR_CLASS in (frame_info.function or ""):
            return  # OK — called from executor
    caller = stack[2].function if len(stack) > 2 else "unknown"
    logger.warning(
        "BYPASS_RLS detected: %s called from %s without RLSAwareSQLExecutor",
        connector_method_name, caller
    )
```
- [ ] **第 2 步：提交**
```warp-runnable-command
git add packages/dbgpt-app/src/dbgpt_app/security/bypass_detector.py
git commit -m "feat(security): add bypass_detector — warn on RLS bypass (observe-only v1)"
```
***
## 第五块：集成测试、场景接入、mock 上游
### 任务 10：SQLite 集成测试
**文件：**
* 新建：`tests/security/test_rls_integration.py`
- [ ] **第 1 步：编写集成测试（5 个用例）**
```python
# tests/security/test_rls_integration.py
"""End-to-end tests using real SQLite + in-process mock RLSClient."""
import asyncio
import sqlite3
import pytest
import pandas as pd
from unittest.mock import AsyncMock
from dbgpt_app.security.rls_executor import RLSAwareSQLExecutor
from dbgpt_app.security.principal import Principal
from dbgpt_app.security.rls_client import RLSRule
@pytest.fixture
def sqlite_ds(tmp_path):
    """Minimal datasource stub backed by a real in-memory SQLite."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE orders (id INT, region TEXT, amount INT)")
    conn.executemany("INSERT INTO orders VALUES (?, ?, ?)", [
        (1, "华南", 100), (2, "华南", 200),
        (3, "华北", 300), (4, "华北", 400), (5, "华北", 500),
    ])
    conn.commit()
    class FakeDS:
        db_type = "sqlite"
        db_name = "test"
        def run_to_df(self, sql: str) -> pd.DataFrame:
            return pd.read_sql_query(sql, conn)
    return FakeDS()
@pytest.mark.asyncio
async def test_enforce_filters_to_huanan(sqlite_ds):
    mock_client = AsyncMock()
    mock_client.batch_fetch = AsyncMock(return_value=[
        RLSRule(table="orders", allowed=True, predicate="region = '华南'")
    ])
    principal = Principal(user_id="alice")
    executor = RLSAwareSQLExecutor(
        datasource=sqlite_ds, rls_client=mock_client,
        principal=principal, conversation_id="c1", rls_mode="enforce"
    )
    result = await executor.execute("SELECT * FROM orders")
    assert len(result.data) == 2
    assert set(result.data["region"]) == {"华南"}
@pytest.mark.asyncio
async def test_shadow_returns_all_rows(sqlite_ds):
    mock_client = AsyncMock()
    mock_client.batch_fetch = AsyncMock(return_value=[
        RLSRule(table="orders", allowed=True, predicate="region = '华南'")
    ])
    principal = Principal(user_id="alice")
    executor = RLSAwareSQLExecutor(
        datasource=sqlite_ds, rls_client=mock_client,
        principal=principal, conversation_id="c1", rls_mode="shadow"
    )
    result = await executor.execute("SELECT * FROM orders")
    # shadow: original sql executed, all 5 rows returned
    assert len(result.data) == 5
    assert "华南" in result.rewritten_sql
@pytest.mark.asyncio
async def test_off_returns_all_rows(sqlite_ds):
    from dbgpt_app.security.stub_rls_client import StubRLSClient
    principal = Principal(user_id="alice")
    executor = RLSAwareSQLExecutor(
        datasource=sqlite_ds, rls_client=StubRLSClient(),
        principal=principal, conversation_id="c1", rls_mode="off"
    )
    result = await executor.execute("SELECT * FROM orders")
    assert len(result.data) == 5
    assert result.rls_snapshot == {}
@pytest.mark.asyncio
async def test_snapshot_recorded(sqlite_ds):
    mock_client = AsyncMock()
    mock_client.batch_fetch = AsyncMock(return_value=[
        RLSRule(table="orders", allowed=True, predicate="region = '华南'")
    ])
    principal = Principal(user_id="alice")
    executor = RLSAwareSQLExecutor(
        datasource=sqlite_ds, rls_client=mock_client,
        principal=principal, conversation_id="c1", rls_mode="enforce"
    )
    result = await executor.execute("SELECT * FROM orders")
    assert result.rls_snapshot == {"orders": "region = '华南'"}
```
- [ ] **第 2 步：运行集成测试**
运行：`uv run pytest tests/security/test_rls_integration.py -v`
预期：全部 PASS
- [ ] **第 3 步：提交**
```warp-runnable-command
git add tests/security/test_rls_integration.py
git commit -m "test(security): add SQLite end-to-end integration tests"
```
### 任务 11：场景接入 — 改造 `chat_db/auto_execute/chat.py`
**文件：**
* 修改：`packages/dbgpt-app/src/dbgpt_app/scene/chat_db/auto_execute/chat.py`（第 132 行）
* 修改：`packages/dbgpt-app/src/dbgpt_app/component_configs.py`
**接线方式说明：** `out_parser.py:138` 同步调用 `df = data(prompt_response.sql)`，其中 `data = do_action(prompt_response)`。因此 `do_action` 必须返回一个接受 `sql: str` 并返回 DataFrame 的**同步**可调用对象。
用户身份来自 `chat_param.user_name`，`self.system_app` 持有 RLSClient 单例。
- [ ] **第 1 步：在 `component_configs.py` 中注册 RLSClient**
新增 `_initialize_rls` 函数并在 `initialize_components` 中调用：
```python
# In component_configs.py
def _initialize_rls(system_app: SystemApp, param):
    """Register RLSClient (or StubRLSClient for mode=off) into SystemApp."""
    from dbgpt_app.security.config import RLSConfig
    from dbgpt_app.security.rls_client import RLSClient
    from dbgpt_app.security.stub_rls_client import StubRLSClient
    from dbgpt_app.microservice.user_service import UserServiceClient
    # Read from serve.rls section; default to mode=off if missing
    rls_cfg_dict = getattr(getattr(param, "serve", None), "rls", None)
    if rls_cfg_dict:
        cfg = RLSConfig(**rls_cfg_dict) if isinstance(rls_cfg_dict, dict) else rls_cfg_dict
    else:
        cfg = RLSConfig()
    system_app.register_instance(cfg)
    if cfg.mode == "off":
        system_app.register_instance(StubRLSClient())
    else:
        # 使用已注册的 UserServiceClient（Nacos 服务发现 + getSqlFragmentByUserId）
        user_service = UserServiceClient.get_instance(system_app)
        rls_client = RLSClient(
            user_service=user_service,
            local_ttl_seconds=cfg.local_ttl_seconds,
            stale_fallback_seconds=cfg.stale_fallback_seconds,
        )
        system_app.register_instance(rls_client)
```
在 `initialize_components` 末尾（确保 `UserServiceClient` 已注册之后）增加调用：`_initialize_rls(system_app, param)`
- [ ] **第 2 步：修改 `chat.py` — 替换 `do_action` 返回值**
**说明：** Principal 优先取 contextvar（由 `ContextMiddleware` 注入），若无则回退到 `chat_param`。
替换 `chat.py:132-134`：
```python
# BEFORE
def do_action(self, prompt_response):
    print(f"do_action:{prompt_response}")
    return self.database.run_to_df
# AFTER
def do_action(self, prompt_response):
    print(f"do_action:{prompt_response}")
    return self._make_rls_runner()
def _make_rls_runner(self):
    """返回一个同步 callable(sql) -> DataFrame，内部经过 RLSAwareSQLExecutor。"""
    import asyncio
    from dbgpt_app.security.rls_executor import RLSAwareSQLExecutor
    from dbgpt_app.security.principal import current_principal
    from dbgpt_app.security.rls_client import RLSClient
    from dbgpt_app.security.config import RLSConfig
    from dbgpt_app.security.stub_rls_client import StubRLSClient
    # 1. 取 RLSClient（已注册到 SystemApp；mode=off 时是 StubRLSClient）
    try:
        rls_client = self.system_app.get_instance(RLSClient)
    except Exception:
        try:
            rls_client = self.system_app.get_instance(StubRLSClient)
        except Exception:
            rls_client = StubRLSClient()
    # 2. 取 RLSConfig
    try:
        cfg = self.system_app.get_instance(RLSConfig)
    except Exception:
        cfg = RLSConfig()
    # 3. Principal: 优先 contextvar，回退 chat_param
    principal = current_principal(chat_param=self.chat_param)
    executor = RLSAwareSQLExecutor(
        datasource=self.database,
        rls_client=rls_client,
        principal=principal,
        conversation_id=self.chat_session_id,
        rls_mode=cfg.mode,
        fail_strategy=cfg.fail_strategy,
    )
    def runner(sql: str):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(executor.execute(sql), loop)
            result = future.result(timeout=30)
        else:
            result = loop.run_until_complete(executor.execute(sql))
        return result.data
    return runner
```
- [ ] **第 3 步：快速冒烟测试 — 验证 chat_db 模式仍可正常导入**
运行：`uv run python -c "from dbgpt_app.scene.chat_db.auto_execute.chat import ChatWithDbAutoExecute; print('import OK')"`
预期：`import OK`
- [ ] **第 4 步：提交**
```warp-runnable-command
git add packages/dbgpt-app/src/dbgpt_app/scene/chat_db/auto_execute/chat.py \
         packages/dbgpt-app/src/dbgpt_app/component_configs.py
git commit -m "feat(security): wire RLSAwareSQLExecutor into chat_db/auto_execute scene"
```
### 任务 12：~~Mock 上游服务~~（已取消）
**取消原因：** 真实 user-service 已通过 Nacos 服务发现接入（见 `microservice/user_service.py`），`getSqlFragmentByUserId` 接口已可用。本地端到端联调时启动真实 user-service mock 即可，不在本计划范围内。
***
## 第六块：最终验证
### 任务 13：运行完整测试套件
- [ ] **第 1 步：运行所有安全模块测试**
运行：`uv run pytest tests/security/ -v`
预期：全部 PASS
- [ ] **第 2 步：运行项目 lint 检查**
运行：`make fmt-check`
预期：无错误（有问题先修复再继续）
- [ ] **第 3 步：运行项目单元测试，确认无回归**
运行：`make test`
预期：无新增失败
- [ ] **第 4 步：最终提交（如有 fmt 修复）**
```warp-runnable-command
git add -A
git commit -m "chore(security): fix lint issues, finalize RLS v1 implementation"
```
