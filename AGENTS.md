# DB-GPT 项目指南

## 项目概述

DB-GPT 是一个开源的 **智能体 AI 数据助手**，面向下一代 AI + Data 产品。它可以连接数据库、CSV/Excel 文件、数据仓库和知识库，让用户用自然语言提问，由 AI 自动编写 SQL、执行 Python 分析、运行可复用的技能（Skills），并生成图表、仪表盘和报告。

**版本**: 0.8.0  
**许可证**: MIT  
**Python**: >= 3.10（`.python-version` 锁定为 3.11）  
**包管理器**: [uv](https://docs.astral.sh/uv/)  
**构建系统**: [Hatchling](https://hatch.pypa.io/)  

---

## 架构设计

DB-GPT 采用 **模块化分层 Monorepo** 架构，通过 `uv` 工作区管理。

### 依赖关系图

```
dbgpt-app（应用层 — FastAPI 服务器、业务逻辑）
  ├── dbgpt-core    （基础层 — 抽象接口、AWEL、智能体、模型接口）
  ├── dbgpt-ext     （扩展层 — 数据源连接器、存储后端、RAG、LLM 适配器）
  ├── dbgpt-serve   （服务层 — 各领域的 REST API）
  ├── dbgpt-client  （客户端 SDK — 面向外部消费者的 Python SDK）
  ├── dbgpt-sandbox （沙箱 — 安全的代码执行环境）
  └── dbgpt-acc-auto（加速器 — 自动检测 GPU/硬件优化）
```

### 各包概览

| 包名 | 位置 | 用途 |
|---|---|---|
| `dbgpt`（核心） | `packages/dbgpt-core/` | 核心抽象：AWEL DAG 引擎、LLM/Embedding 接口、智能体框架、存储 API、组件系统、CLI |
| `dbgpt-app` | `packages/dbgpt-app/` | 应用服务器（`dbgpt_server.py`）、组件编排、业务场景、OpenAPI 端点、数据库迁移 |
| `dbgpt-ext` | `packages/dbgpt-ext/` | 具体实现：数据源连接器（MySQL、PostgreSQL 等）、向量存储（Chroma、Milvus）、RAG 管道、LLM 提供商适配器 |
| `dbgpt-serve` | `packages/dbgpt-serve/` | REST API 层：智能体、会话、数据源、工作流、模型、提示词、RAG、文件、评估等服务 |
| `dbgpt-client` | `packages/dbgpt-client/` | Python SDK：`Client` 类，提供类型化的异步方法用于聊天、工作流、知识库、应用、数据源管理 |
| `dbgpt-sandbox` | `packages/dbgpt-sandbox/` | 隔离的代码执行环境，安全运行 Python/JS 代码 |
| `dbgpt-accelerator` | `packages/dbgpt-accelerator/` | 硬件加速：`dbgpt-acc-auto`（自动检测）、`dbgpt-acc-flash-attn`（Flash Attention） |

### 前端

| 组件 | 位置 | 技术栈 |
|---|---|---|
| Web UI | `web/` | Next.js 13、React 18、TypeScript、Ant Design 5、TailwindCSS 3、AntV 图表、Monaco Editor |

---

## 核心概念

### AWEL（智能体工作流表达语言）
- 位置：`packages/dbgpt-core/src/dbgpt/core/awel/`
- 声明式 DAG 工作流编排引擎
- 支持通过 Web UI 进行可视化流程设计
- 组成：`dag/`（图管理）、`operators/`（工作流节点）、`trigger/`（事件触发器）、`flow/`（执行流）

### 组件系统
- 文件：`packages/dbgpt-core/src/dbgpt/component.py`
- `SystemApp` 类管理组件生命周期（初始化 → 启动 → 停止）和依赖注入
- 所有服务通过该集中式组件注册中心进行注册

### 技能（Skills）
- 位置：`skills/`
- 可复用的领域分析工作流（CSV 分析、财务报告等）
- 内置技能：`csv-data-analysis`、`financial-report-analyzer`、`walmart-sales-analyzer`、`skill-creator`、`agent-browser`

### 配置系统
- 基于 TOML 的配置文件，位于 `configs/`
- 支持环境变量插值：`${env:VAR_NAME:-默认值}`
- 配置模板：`dbgpt-proxy-openai.toml`、`dbgpt-proxy-deepseek.toml`、`dbgpt-local-vllm.toml` 等
- 服务器默认：`host=0.0.0.0`，`port=5670`
- 数据库：SQLite（默认）或 MySQL

---

## 开发环境搭建

### 前置条件
- Python >= 3.10（推荐 3.11）
- [uv](https://docs.astral.sh/uv/) 包管理器
- Node.js（用于前端开发）

### 安装依赖

```bash
# 安装所有包及常用扩展
uv sync --all-packages \
  --extra "base" \
  --extra "proxy_openai" \
  --extra "rag" \
  --extra "storage_chromadb" \
  --extra "dbgpts"

# 安装 pre-commit 钩子
uv run pre-commit install
```

**中国用户提示**：如遇网络问题，可配置清华镜像源：
```bash
export UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
```

### 启动服务器

```bash
# 使用指定配置启动
uv run dbgpt start webserver --config configs/dbgpt-proxy-openai.toml

# 或使用 profile 简写
uv run dbgpt start webserver --profile openai
```

服务地址：`http://localhost:5670`

### 前端开发

```bash
cd web
npm install   # 或 yarn
npm run dev   # 启动 Next.js 开发服务器
```

---

## 代码质量与测试

### 格式化与 Lint

```bash
# 格式化代码（ruff）
make fmt

# 仅检查格式，不修改
make fmt-check
```

**Ruff 配置**（`pyproject.toml`）：
- 行宽限制：88 字符
- 目标版本：Python 3.10
- 启用规则：`E`（错误）、`F`（pyflakes）、`I`（isort 导入排序）
- 双引号、空格缩进

### 类型检查

```bash
make mypy
```

当前仅对 `packages/dbgpt-core/` 启用。

### 测试

```bash
# 单元测试
make test

# 文档测试
make test-doc

# 覆盖率
make coverage
```

**pytest 配置**：`--import-mode=importlib`，发现 `test_*.py` 和 `*_test.py` 文件。

### 提交前检查

```bash
make pre-commit  # 依次执行：fmt-check → test → test-doc → mypy
```

---

## 项目目录结构

```
DB-GPT-main/
├── packages/                        # Python 包（uv 工作区）
│   ├── dbgpt-core/src/dbgpt/       # 核心：agent、cli、core（AWEL、接口）、model、rag、storage、datasource、vis
│   ├── dbgpt-app/src/dbgpt_app/    # 应用：服务器、场景、openapi、初始化、知识库
│   ├── dbgpt-ext/src/dbgpt_ext/    # 扩展：数据源连接器、存储后端、RAG 实现、LLM 提供商
│   ├── dbgpt-serve/src/dbgpt_serve/ # 服务：agent、conversation、datasource、flow、model、prompt、rag、file
│   ├── dbgpt-client/               # 客户端 SDK
│   ├── dbgpt-sandbox/              # 代码执行沙箱
│   └── dbgpt-accelerator/          # GPU/硬件加速
├── web/                             # Next.js 前端
│   ├── app/                         # Next.js 应用目录
│   ├── components/                  # React 组件
│   ├── new-components/              # 新版组件
│   ├── pages/                       # 页面路由
│   ├── client/                      # API 客户端工具
│   ├── hooks/                       # React 自定义 Hooks
│   ├── locales/                     # 国际化翻译
│   └── types/                       # TypeScript 类型定义
├── configs/                         # TOML 配置模板
├── skills/                          # 内置可复用分析技能
├── pilot/                           # 工作区模板（数据库元数据、迁移、示例数据）
├── docker/                          # Docker 配置和示例数据
├── docs/                            # 文档
├── examples/                        # 使用示例
├── i18n/                            # 国际化资源
├── scripts/                         # 构建/安装/工具脚本
├── tests/                           # 集成测试和单元测试
├── pyproject.toml                   # 根工作区配置、开发依赖、工具设置
└── Makefile                         # 开发命令集
```

---

## 编码规范

### Python

- **风格**：Ruff 格式化，88 字符行宽，双引号
- **导入排序**：通过 ruff `I` 规则（isort），第一方模块：`dbgpt`、`dbgpt_app`、`dbgpt_ext`、`dbgpt_serve`、`dbgpt_client`、`dbgpt_sandbox`
- **类型注解**：必须添加。核心包强制执行 mypy 检查
- **异步编程**：全面使用 `async/await` 模式
- **数据模型**：Pydantic v2（>= 2.6.0）用于所有数据模型和验证
- **数据库操作**：SQLAlchemy v2（>= 2.0.25, < 2.0.29）
- **命名规范**：函数/变量用 `snake_case`，类用 `PascalCase`

### TypeScript/React（前端）

- **ESLint + Prettier** 格式化
- **Ant Design 5** 为主要 UI 框架
- **TailwindCSS** 用于工具类样式
- **i18next** 用于国际化

### 设计原则

1. **关注点分离**：每个包有单一明确的职责
2. **依赖倒置**：上层模块依赖核心抽象，而非具体实现
3. **开闭原则**：核心接口稳定；通过插件和新提供商进行扩展
4. **接口隔离**：接口聚焦且内聚
5. **可选依赖**：功能通过 extras 门控，最小化安装体积

---

## Docker 部署

```bash
# 启动 MySQL + webserver
SILICONFLOW_API_KEY=sk-xxx docker compose up -d
```

- MySQL 端口：3306
- Web 服务端口：5670
- 镜像：`mysql/mysql-server`、`eosphorosai/dbgpt-openai:latest`

---

## 常见开发任务

### 添加新的 LLM 提供商
1. 在 `packages/dbgpt-ext/src/dbgpt_ext/llms/` 中实现适配器
2. 在 `packages/dbgpt-core/pyproject.toml` 中添加可选依赖
3. 在模型提供商发现系统中注册

### 添加新的存储后端
1. 在 `packages/dbgpt-ext/src/dbgpt_ext/storage/` 中实现
2. 在 `packages/dbgpt-ext/pyproject.toml` 中添加可选依赖
3. 遵循 `packages/dbgpt-core/src/dbgpt/storage/` 中的存储接口

### 添加新的 Serve API
1. 在 `packages/dbgpt-serve/src/dbgpt_serve/` 中创建模块
2. 定义 API 路由、服务逻辑和 Schema
3. 在应用初始化流程中注册

### 添加新的技能（Skill）
1. 在 `skills/` 目录下创建文件夹
2. 参考已有技能的模式（如 `csv-data-analysis`）
3. 详见 `skills/INTEGRATION_GUIDE.md` 和 `skills/skill_implementation_guide.py`

---

## 重要文件速查

| 文件 | 用途 |
|---|---|
| `pyproject.toml` | 根工作区配置、开发依赖、工具设置 |
| `Makefile` | 所有开发命令（fmt、test、mypy、build、publish） |
| `packages/dbgpt-app/src/dbgpt_app/dbgpt_server.py` | 主 FastAPI 应用入口 |
| `packages/dbgpt-app/src/dbgpt_app/component_configs.py` | 组件注册与配置 |
| `packages/dbgpt-core/src/dbgpt/component.py` | 核心 `SystemApp` 组件生命周期管理 |
| `packages/dbgpt-core/src/dbgpt/core/awel/` | AWEL 工作流引擎 |
| `configs/dbgpt-proxy-openai.toml` | 配置模板示例 |
| `web/package.json` | 前端依赖和脚本 |
| `CONTRIBUTING.md` | 贡献指南 |
