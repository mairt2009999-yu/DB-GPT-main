# DB-GPT 二次开发 · 权限体系设计

## 1. 概述

### 1.1 背景
现有企业系统已具备完整权限控制体系。DB-GPT 作为新增的"AI 数据分析"子模块接入该系统，需要：
1. **数据库数据行级权限**：用户通过 DB-GPT 用自然语言问数时，最终落到目标库的 SQL 只能返回该用户被授权看到的行（必要时附带列遮蔽/列禁用）。
2. **DB-GPT 项目内资源权限**：DB-GPT 自身的应用（GptsApp）、数据源、会话/任务、Prompt 等资源按用户做基础隔离，避免跨用户越权读写。

### 1.2 集成假设（已对齐）
- DB-GPT 部署为现有系统的子模块/微服务，由现有系统的网关/BFF 统一认证后注入身份头。
- DB-GPT 不做认证，只做授权（拦截、决策、SQL 改写）。
- 行级数据权限的策略源是**远程权限服务**（输入 user+table，输出 WHERE 谓词片段）。
- 资源级权限暂不引入完整 RBAC，初版只做 owner 隔离 + 管理员角色放宽。

### 1.3 目标
- 在不破坏现有 DB-GPT 接口形态的前提下，渐进引入鉴权。
- 行级权限正确性优先，使用 AST 改写而非字符串拼接。
- 任务（数据分析执行实例）可被审计、回查、合规复盘。
- 鉴权链路全部可灰度、可回滚。

### 1.4 非目标
- 不实现独立的用户/角色管理 UI（角色由上游系统下发）。
- 不实现完整 RBAC（细粒度 permission/role 策略中心）。后续需要再扩展。
- 不为 `skills/` 目录下的静态技能模板做单独权限管控（无独立调用入口）。
- 不重写现有 SQL 生成 prompt，仅在生成结果上做改写。

## 2. 当前状态分析

### 2.1 鉴权现状
- `packages/dbgpt-serve/src/dbgpt_serve/utils/auth.py` 是 mock 实现：读 `user_id` 头部，缺失则用 `001`，永远授予 `role=admin`。
- 不同模块鉴权风格不一致：
  - 应用/会话/Flow 类用 `Depends(get_user_from_headers)`。
  - 数据源类只用 `Depends(check_api_key)`，没有用户维度。
- 多个表已有 `user_code/user_name/user_id` 等归属字段（部分表历史上还带 `sys_code`），但接口层未强制按 owner 过滤。`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:55` 直接写死 `query.ignore_user = \"true\"`，所有用户都能看所有 App。
- 没有 RBAC 数据模型，没有策略决策点。
- SQL 执行链路（`packages/dbgpt-app/src/dbgpt_app/scene/chat_db/`、`packages/dbgpt-core/src/dbgpt/datasource/rdbms/base.py`）没有任何行级或列级控制。

### 2.2 资源字段命名混乱
现有表对"owner"的命名混着用：`user_code`、`user_id`、`user_name`。本方案不强行统一字段名（避免大改），通过 ORM 层抽象统一暴露为 `owner_user_id`。

## 3. 总体架构

DB-GPT 内置三层鉴权 + 一处任务建模：

```
上游网关/BFF (认证完成，注入 X-User-* / Authorization)
        │
        ▼
┌──────────────────────────────────────────────┐
│ DB-GPT FastAPI                                │
│                                               │
│ L1 身份解析  Header → Principal               │
│      │                                        │
│ L2 资源隔离  owner 过滤/断言 + 管理员放宽         │
│      │                                        │
│ L3 行级 RLS  sqlglot AST 改写 + 远程谓词        │
│      │                                        │
│ 任务建模     gpts_conversations 加状态/审计字段  │
└──────────────────────────────────────────────┘
```

每层职责、输入、输出、失败模式：
- **L1 身份**：把 HTTP header / token 解析成 `Principal`（user_id、roles 等）。失败 → 401。
- **L2 资源**：判断 user 在 resource 上的可见性与可写性；list 接口自动注入 owner 过滤；编辑/删除前断言 owner。失败 → 403。
- **L3 行级**：在 LLM 生成 SQL 真正执行前，用 sqlglot 解析 AST，对每张表向远程 RLS 服务查谓词并 per-table 注入。失败默认 fail-close。
- **任务**：`gpts_conversations` 记录状态机、生成 SQL、改写后 SQL、RLS 谓词快照，用于合规审计。

## 4. L1 身份解析

### 4.1 Principal 数据结构
```python
class Principal(BaseModel):
    user_id: str
    user_name: Optional[str] = None
    roles: List[str] = []
    raw_token: Optional[str] = None    # 原始 JWT，转发给上游 RLS 接口
    trace_id: Optional[str] = None

    @property
    def is_admin(self) -> bool:
        return any(role in ADMIN_ROLE_CODES for role in self.roles)
```

### 4.2 FastAPI Dependency
新增 `get_principal`，作为新代码统一入口；保留 `get_user_from_headers` 作为兼容 shim，内部转调 `get_principal`，保证老 endpoint 不破坏。

约束：
- 必须字段缺失（`X-User-Id`）→ 401。
- 角色信息不在请求头中，按需调用 User 服务获取，并基于“现有系统中的特定角色编码”判断是否为 DB-GPT 管理员。
- 上游已校验 JWT，DB-GPT 默认不重复校验签名；若部署需要旁路校验，通过开关启用。
- 开发本地 mock 模式由 `DBGPT_AUTH_ENFORCED=false` 控制，生产固定为 true。

### 4.3 兼容老 `UserRequest`
`get_user_from_headers` 返回的 `UserRequest` 由 `Principal` 转换得到，字段尽量映射，避免大量调用点重写。

## 5. L2 资源隔离

按"owner + 管理员角色"做资源隔离，不做 RBAC。

### 5.1 过滤规则
- 普通用户列表：`WHERE owner_user_id = current_user_id`，再 OR 含 `published='true'` 的资源（如已发布 GptsApp）。
- 普通用户详情：同上。
- 编辑/删除：`assert owner_user_id == current_user_id`。
- 管理员（`is_admin=True`）：可跨 owner 查看、编辑、删除资源。
- `is_admin` 的判断不靠固定字符串 `admin`，而是用现有系统中的特定角色编码列表（如 `DBGPT_ADMIN_ROLE_CODES`）映射得到。

### 5.2 工具函数
新增 `packages/dbgpt-serve/src/dbgpt_serve/utils/authz.py`：
- `with_owner_filter(query, model_cls, principal)`：给 SQLAlchemy query 注入过滤。
- `assert_owner(entity, principal, allow_admin=True)`：编辑/删除前断言。

### 5.3 现有接口收口
重点改造（按文件路径）：
- `packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py`：移除 `query.ignore_user = "true"` 等裸奔逻辑；`GET /v1/app/{app_code}` 等无身份接口加 `Depends(get_principal)`；删除/编辑前 `assert_owner`，并把 `gpts_app.user_code` 强制覆盖为 `principal.user_id`。
- `packages/dbgpt-serve/src/dbgpt_serve/datasource/api/endpoints.py`：所有 endpoint 加 `Depends(get_principal)`；create 写入 owner；list/get/delete 走过滤。
- `packages/dbgpt-serve/src/dbgpt_serve/conversation/api/endpoints.py`、`flow/api/endpoints.py`、`prompt/api/endpoints.py`、`dbgpts/my/api/endpoints.py`、`file/api/endpoints.py`：同上。

### 5.4 数据模型补丁
- 资源权限初版不依赖 `sys_code`，只依赖 owner 字段。
- 缺失 owner 字段的表确认补齐（默认列名沿用各表已有的 `user_code`/`user_id`，应用层抽象为 `owner_user_id`）。
- 不强制统一字段名以避免大改；通过 SQLAlchemy 的 `synonym`/property 暴露统一访问名。

## 6. L3 行级 RLS

### 6.0 双层架构总览（Prompt + 后端硬拦截）

L3 的正确实现不是只改 Prompt，也不是让 Agent 在 ReAct 工具链里自己调权限接口，而是**两层同时存在**：

1. **Prompt 改造**：把当前用户、可见表/列范围、方言约束写入 system prompt，让 LLM 生成的 SQL 尽量贴合权限范围，减少被拒概率。
2. **后端硬拦截 `RLSAwareSQLExecutor`**：所有 SQL 最终执行前，必须进入同一个 Executor，统一做表识别、谓词拉取、AST 改写、审计落库。

职责划分如下：

- **Prompt 改造**：提升 SQL 质量与通过率，**不是安全底线**。
- **`RLSAwareSQLExecutor`**：真正的安全底线，**不可被 LLM 绕过**。

为什么不能只让 Agent 自己调谓词接口：
- LLM 可能被 prompt 注入，跳过工具直接返回原 SQL；
- LLM 自己拼谓词，对 LEFT JOIN / 聚合 / CTE / UNION 的边界处理不可靠；
- 安全决策必须发生在后端不可绕过的执行链路上。

### 6.0.1 Prompt 改造（提升通过率）

改造位置：各 chat 场景的 system prompt 构造逻辑，例如：
- `packages/dbgpt-app/src/dbgpt_app/scene/chat_db/auto_execute/chat.py`
- `packages/dbgpt-app/src/dbgpt_app/scene/chat_db/professional_qa/chat.py`

建议注入信息：

```text
当前用户：{user_id}（roles={roles}）
当前数据源：{datasource}
你可访问的表：{allowed_tables}
你可访问的列：{allowed_columns}

约束：
- 只能使用以上表与列；
- 避免 SELECT *；
- 如涉及敏感字段，优先聚合、脱敏或不选择；
- 生成 SQL 时不要自行拼接权限谓词；
- 系统会在执行前自动注入行级权限规则。
```

`allowed_tables` / `allowed_columns` 来源于 L2 过滤后的元数据，以及对上游权限服务做预判后得到的可见对象集合。

### 6.1 接口契约（DB-GPT ↔ 上游权限服务）

**Request（批量）**：
```json
{
    "principal": {
      "user_id": "yujiahong",
      "roles": ["ROLE_ANALYST"]
    },
  "resources": [
    {"datasource": "mysql_prod", "schema": "sales", "table": "orders"},
    {"datasource": "mysql_prod", "schema": "sales", "table": "customers"}
  ],
  "action": "select",
  "context": {"trace_id": "..."}
}
```

**Response**：
```json
{
  "results": [
    {
      "table": "orders",
      "allowed": true,
      "predicate": "region IN ('华南') AND owner_id = 1001",
      "predicate_dialect": "ansi",
      "column_masks": [],
      "denied_columns": [],
      "version": "v20260428-123",
      "ttl_seconds": 60
    },
    {"table": "customers", "allowed": false}
  ]
}
```

约束：
- predicate **不带表别名前缀**；DB-GPT 自己用 sqlglot 加。
- `allowed=false` 表示该表完全无权限，DB-GPT 直接拒绝整条 SQL。
- 初版只实现 `predicate`，`column_masks` / `denied_columns` 字段先留契约不实现。

### 6.2 RLSAwareSQLExecutor（后端硬拦截核心组件）

新建统一执行器：`packages/dbgpt-app/src/dbgpt_app/security/rls_executor.py`

核心原则：
- **所有 SQL 最终执行都必须经过 `RLSAwareSQLExecutor.execute()`**；
- 禁止在各 chat scene、AWEL operator、datasource helper 里各自散落调用上游权限接口；
- 上游谓词接口的调用、缓存、AST 改写、失败兜底、审计落库，统一收口到这一个组件。

#### 6.2.1 标准执行链路

```text
LLM 输出原始 SQL
    ↓
RLSAwareSQLExecutor.execute(sql, principal, datasource, conversation_id)
    ↓
1. sqlglot.parse_one(sql, dialect)
    - 解析失败 → fail-close
    ↓
2. qualify / collect_tables
    - 收集 SQL 中涉及的所有表、schema、alias
    - 覆盖 JOIN / 子查询 / CTE / UNION / 自连接
    ↓
3. RLSClient.batch_fetch(principal, tables)
    - 命中本地 LRU / Redis 则直接返回
    - miss 时批量调上游权限服务
    ↓
4. 权限决策
    - allowed = false → 拒绝整条 SQL
    - predicate 非空 → 进入 AST 注入
    ↓
5. inject_predicate(tree, table, predicate)
    - INNER JOIN / 主表：注入 WHERE
    - LEFT JOIN 右表：注入 ON
    - 同一张表多个 alias：分别注入
    ↓
6. 生成 rewritten_sql 并再次 parse 校验
    ↓
7. datasource_executor.run(rewritten_sql)
    ↓
8. 把 executed_sql / rls_snapshot 写回 gpts_conversations
    ↓
返回结果集
```

#### 6.2.2 接口建议

```python
class RLSAwareSQLExecutor:
    def __init__(
        self,
        datasource,
        rls_client,
        principal,
        conversation_id: str,
        rls_mode: str = "enforce",
    ):
        ...

    async def execute(self, sql: str, *, timeout_seconds: float = 30):
        ...
```

返回对象建议至少包含：
- `data`：查询结果
- `rewritten_sql`：改写后 SQL
- `rls_snapshot`：`{table: predicate}` 的快照

#### 6.2.3 接入点

所有现有 SQL 执行入口最终都要替换成 `RLSAwareSQLExecutor.execute()`：
- `packages/dbgpt-app/src/dbgpt_app/scene/chat_db/auto_execute/chat.py`
- `packages/dbgpt-app/src/dbgpt_app/scene/chat_db/professional_qa/chat.py`
- `packages/dbgpt-app/src/dbgpt_app/scene/chat_dashboard/chat.py`
- AWEL Flow 中的 SQL 执行 operator
- 如条件允许，进一步下沉到 `packages/dbgpt-core/src/dbgpt/datasource/rdbms/base.py` 的统一执行方法中，形成最彻底的拦截点

#### 6.2.4 rls_mode

| mode | 行为 |
|---|---|
| `off` | 不调上游、不改写，直接执行原 SQL |
| `shadow` | 调上游、做改写，但实际仍执行原 SQL，只记录差异 |
| `enforce` | 调上游、做改写，并执行改写后 SQL；失败则拒绝 |

`shadow` 用于灰度验证 AST 改写正确性，避免一上来就强制拦截导致业务中断。

### 6.3 SQL 改写细节

```python
def rewrite_sql_with_rls(sql, dialect, principal, rls_client):
    tree = sqlglot.parse_one(sql, dialect=dialect)
    tree = sqlglot.optimizer.qualify.qualify(tree, dialect=dialect)
    tables = collect_tables(tree)
    rules = rls_client.batch_fetch(principal, tables)
    for tbl, rule in zip(tables, rules):
        if not rule.allowed:
            raise PermissionDenied(tbl)
        if rule.predicate:
            inject_predicate(tree, tbl, rule.predicate, dialect)
    return tree.sql(dialect=dialect)
```

要点：
- 自连接同一张表的不同 alias 各自独立注入；
- 子查询 / CTE / UNION 分支都要扫到；
- **LEFT JOIN 的右表谓词必须注入到 ON 子句，而不是 WHERE**，否则会把 LEFT JOIN 静默变成 INNER JOIN；
- 解析失败 → fail-close；
- 改写后再 parse 一次校验语法正确。

### 6.4 多方言适配
sqlglot 原生支持 MySQL / PostgreSQL / SQLite / ClickHouse / Oracle 等。约定：
- `RLSAwareSQLExecutor` 实例化时显式传 `dialect`，从 datasource 配置取；
- 上游返回的 predicate 假定与 datasource 方言一致，Executor 不做翻译；
- sqlglot 不支持的方言 → fail-close 并记录。

### 6.5 RLSClient 与缓存

建议新增：`packages/dbgpt-app/src/dbgpt_app/security/rls_client.py`

职责：
- 封装上游权限服务的 HTTP/gRPC 调用；
- 封装进程内 LRU + Redis + stale fallback；
- 统一输出 `RLSRule` 列表给 `RLSAwareSQLExecutor`。

缓存三层：
- 进程内 LRU：键 `(user_id, roles_hash, datasource, schema, table)`，TTL 60s；
- Redis：同键，TTL 5min，多实例共享；
- 上游推送失效：MQ/HTTP webhook 通知 DB-GPT 主动 invalidate（实现可后置）。

`allowed=false` 同样缓存，避免反复打爆上游。

### 6.6 失败策略
- 默认 **fail-close**：上游异常/超时 → 拒绝执行，返回"权限服务不可用"；
- stale 兜底：使用未过期的 stale 缓存（最长 stale 时长 = `stale_fallback_seconds`，默认 30 分钟），同时异步重试；
- fail-open 白名单（仅 admin + 配置显式开启）：stale 也没有时允许放行，但强制写审计日志，标记 `rls_bypassed=true`。

## 7. 任务建模（gpts_conversations 加字段）

### 7.1 Schema 补丁
```sql
ALTER TABLE gpts_conversations
  ADD COLUMN task_status        VARCHAR(16) DEFAULT 'pending',
  ADD COLUMN task_started_at    DATETIME,
  ADD COLUMN task_finished_at   DATETIME,
  ADD COLUMN task_duration_ms   INT,
  ADD COLUMN task_error_code    VARCHAR(64),
  ADD COLUMN task_error_message TEXT,
  ADD COLUMN generated_sql      TEXT,
  ADD COLUMN executed_sql       TEXT,
  ADD COLUMN rls_snapshot       TEXT,
  ADD COLUMN result_file_id     VARCHAR(64),
  ADD COLUMN trace_id           VARCHAR(64),
  ADD COLUMN client_ip          VARCHAR(64);
CREATE INDEX idx_owner_status ON gpts_conversations (user_id, task_status, gmt_modified);
```

### 7.2 状态机
```
pending → running → success / failed / cancelled
```
- pending：用户发起执行时写入。
- running：实际开跑前更新。
- 终态：执行结束/异常 handler 写入。
- 所有状态变更必须带 owner 校验，避免 A 用户取消 B 用户的任务。

### 7.3 审计核心字段
- `executed_sql`：RLS 改写后真正打到目标库的 SQL。
- `rls_snapshot`：JSON `{table: predicate}`，记录执行那一刻使用的 RLS 谓词。
- 用于合规复盘、用户投诉回查、离职审计。

## 8. 配置与开关

放到 `configs/*.toml`：
```toml
[serve.auth]
enforced = true
dev_mock_user_id = "001"
admin_role_codes = ["ROLE_DBGPT_ADMIN"]

[serve.rls]
mode = "enforce"               # off | shadow | enforce
fail_strategy = "close"
stale_fallback_seconds = 1800
batch_enabled = true
upstream_url = "${env:RLS_UPSTREAM_URL}"
upstream_timeout_ms = 800

[serve.rls.cache]
local_ttl_seconds = 60
redis_ttl_seconds = 300
redis_url = "${env:REDIS_URL:-}"
```

## 9. 迁移与灰度

阶段 0 · 基线收口（约 1~2 周）
- 替换 `get_user_from_headers` 内部为 Principal 解析。
- 加 `DBGPT_AUTH_ENFORCED` 开关，默认关。
- 小流量环境打开做兼容验证。

阶段 1 · 资源隔离（约 2~3 周）
- 数据模型补丁与历史数据回填。
- 改造各 endpoint 走 `with_owner_filter` / `assert_owner`。
- 移除裸奔代码（如 `ignore_user="true"`）。
- 流量切 20% → 50% → 100%。

阶段 2 · 任务建模（约 1 周）
- `gpts_conversations` 加字段。
- 执行 chain 写入状态、SQL、RLS 快照。
- 前端"我的任务"列表对接。

阶段 3 · 行级 RLS（约 3~4 周）
- 引入 sqlglot，实现改写器（先 MySQL / PostgreSQL）。
- 对接上游批量接口、缓存、fail-close。
- **影子模式**：不改写实际 SQL，只跑改写并记录差异，1~2 周观察。
- 切 enforce，从单数据源灰度开始。

阶段 4 · 监控告警（持续）
- 鉴权拒绝率、RLS 改写失败率、缓存命中率、stale 兜底触发频次。

## 10. 测试策略

### 10.1 L1/L2 单元测试
- 缺 header → 401。
- 非 owner 改/删 → 403。
- admin 跨 owner → 200。
- `published='true'` 的 GptsApp 其他用户可读 → 200。

### 10.2 L3 SQL 改写测试矩阵（最关键）
按以下维度交叉组合：
- 方言：mysql / postgres / clickhouse / sqlite。
- SQL 形态：简单 SELECT / JOIN / 子查询 / CTE / UNION / 自连接 / 聚合 / 窗口函数。
- 表数量：1 / 2 / 3+。
- 谓词形态：简单 IN / 多 AND/OR / 含函数。
- allowed：true / false。
- 边界：空谓词 / null / 解析失败 / 上游超时。

每个组合断言：
- 改写后 SQL 能再被该方言 parse 成功。
- 改写后结果 ⊆ 原始结果（用受控样本数据集）。
- `allowed=false` 抛 PermissionDenied。
- 失败按配置 fail-close。

### 10.3 端到端测试
1. 上游注入身份 → 创建 GptsApp → 跨 owner 不可见 → admin 可见。
2. 用户 A 跑任务 → conversation 写入 task_status/executed_sql/rls_snapshot → 用户 B 查询不到。
3. 同一 SQL，user1（华南）和 user2（华北）跑出不同结果。
4. RLS 服务挂掉，普通用户拒绝，admin 走 stale 兜底（如策略允许）。

### 10.4 安全回归
固定一组"已知应该被拒"的请求每次发版前跑：无 header / 伪造 X-User-Id / SQL 注入 / 跨租户尝试。

## 11. 风险与待定项

风险：
- L3 改写器的 SQL 方言覆盖度，是阶段 3 的最大不确定性，需要影子模式兜底。
- 上游 RLS 接口契约未最终敲定（包括是否带表别名前缀、是否一次返回多表、错误语义），需要与上游团队联合定稿。
- 老资源缺少统一 owner 字段时，需要业务团队配合梳理真实创建者并补齐。

待定项：
- 列遮蔽 / 列禁用是否在初版实现，还是仅留契约。
- 上游推送失效（webhook/MQ）的具体协议。
- 是否引入独立的"分享"机制（owner 主动把资源/任务分享给指定用户）。

## 12. 不在本设计范围
- `skills/` 静态目录的权限管控。
- 完整 RBAC（permission/role 中心化）。
- 自建用户/角色管理 UI。
- 重写 LLM SQL 生成 prompt。
