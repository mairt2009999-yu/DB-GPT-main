# DB-GPT 后端 API 清单


生成时间：2026-04-22（基于源码静态分析，不依赖运行中的 OpenAPI 文档）

说明：
- 路由前缀来自 `dbgpt_server.py`、`serve_initialization.py` 和各 `Serve` 组件默认配置。
- `health` / `test_auth` 这类通用接口也保留在清单中，便于你核对完整暴露面。
- 参数说明优先取 `Query/Body/Field` 的 `description`、函数 docstring，其次按字段名做保守推断。

## 模块总览

| 模块 | 基础前缀 | 接口数 | 源文件 |
| --- | --- | ---: | --- |
| AWEL Flow API | /api/v1/serve/awel<br>/api/v2/serve/awel | 19 | `packages/dbgpt-serve/src/dbgpt_serve/flow/api/endpoints.py` |
| Agent Chat Serve API | /api/v1/serve/agent/chat | 6 | `packages/dbgpt-serve/src/dbgpt_serve/agent/chat/api/endpoints.py` |
| Agent Hub API | /api | 6 | `packages/dbgpt-serve/src/dbgpt_serve/agent/hub/controller.py` |
| DBGPTS Hub API | /api/v1/serve/dbgpts/hub | 8 | `packages/dbgpt-serve/src/dbgpt_serve/dbgpts/hub/api/endpoints.py` |
| Libro API | /api/v1/serve/libro | 6 | `packages/dbgpt-serve/src/dbgpt_serve/libro/api/endpoints.py` |
| Prompt 管理 API | /prompt | 11 | `packages/dbgpt-serve/src/dbgpt_serve/prompt/api/endpoints.py` |
| Python 文件上传 API | /api | 1 | `packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/python_upload_api.py` |
| RAG / Knowledge Serve API | /api/v2/serve/knowledge | 16 | `packages/dbgpt-serve/src/dbgpt_serve/rag/api/endpoints.py` |
| SQL/图表编辑器 API | /api | 9 | `packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/editor/api_editor_v1.py` |
| 会话管理 API | /api/v1/chat/dialogue | 10 | `packages/dbgpt-serve/src/dbgpt_serve/conversation/api/endpoints.py` |
| 应用市场/DBGPTS API | /api | 24 | `packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py` |
| 应用服务 v2 API | /api | 5 | `packages/dbgpt-serve/src/dbgpt_serve/agent/app/endpoints.py` |
| 我的 DBGPTS API | /api/v1/serve/dbgpts/my | 7 | `packages/dbgpt-serve/src/dbgpt_serve/dbgpts/my/api/endpoints.py` |
| 技能/分享/React Agent API | /api | 10 | `packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/agentic_data_api.py` |
| 推荐问题 API | /api | 4 | `packages/dbgpt-serve/src/dbgpt_serve/agent/app/recommend_question/controller.py` |
| 数据源 API | /api/v2/serve | 10 | `packages/dbgpt-serve/src/dbgpt_serve/datasource/api/endpoints.py` |
| 文件服务 API | /api/v2/serve/file | 7 | `packages/dbgpt-serve/src/dbgpt_serve/file/api/endpoints.py` |
| 新版反馈 API | /api/v1/conv/feedback | 9 | `packages/dbgpt-serve/src/dbgpt_serve/feedback/api/endpoints.py` |
| 旧版反馈 API | /api | 3 | `packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/feedback/api_fb_v1.py` |
| 旧版聊天/OpenAPI v1 | /api | 21 | `packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py` |
| 模型服务 API | /api/v1/worker<br>/api/v2/serve/model | 7 | `packages/dbgpt-serve/src/dbgpt_serve/model/api/endpoints.py` |
| 知识库 API |  | 22 | `packages/dbgpt-app/src/dbgpt_app/knowledge/api.py` |
| 示例数据 API | /api | 1 | `packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/examples_api.py` |
| 聊天 OpenAPI v2 兼容层 | /api | 1 | `packages/dbgpt-app/src/dbgpt_app/openapi/api_v2.py` |
| 评测/Benchmark API | /api/v1/evaluate<br>/api/v2/serve/evaluate | 12 | `packages/dbgpt-serve/src/dbgpt_serve/evaluate/api/endpoints.py` |

## 详细接口

### AWEL Flow API

基础前缀：`/api/v1/serve/awel`, `/api/v2/serve/awel`

- `GET /api/v1/serve/awel/health` / `GET /api/v2/serve/awel/health`
  - 作用：Health check endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/flow/api/endpoints.py:110`
- `GET /api/v1/serve/awel/test_auth` / `GET /api/v2/serve/awel/test_auth`
  - 作用：Test auth endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/flow/api/endpoints.py:116`
- `POST /api/v1/serve/awel/flows` / `POST /api/v2/serve/awel/flows`
  - 作用：Create a new Flow entity
  - 参数：
    - `request`（body，`ServeRequest`）: The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/flow/api/endpoints.py:126`
- `PUT /api/v1/serve/awel/flows/{uid}` / `PUT /api/v2/serve/awel/flows/{uid}`
  - 作用：Update a Flow entity
  - 参数：
    - `uid`（path，`str`）: The uid
    - `request`（body，`ServeRequest`）: The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/flow/api/endpoints.py:148`
- `DELETE /api/v1/serve/awel/flows/{uid}` / `DELETE /api/v2/serve/awel/flows/{uid}`
  - 作用：Delete a Flow entity
  - 参数：
    - `uid`（path，`str`）: The uid
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/flow/api/endpoints.py:170`
- `GET /api/v1/serve/awel/flows/{uid}` / `GET /api/v2/serve/awel/flows/{uid}`
  - 作用：Get a Flow entity by uid
  - 参数：
    - `uid`（path，`str`）: The uid
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/flow/api/endpoints.py:186`
- `GET /api/v1/serve/awel/chat/flows` / `GET /api/v2/serve/awel/chat/flows`
  - 作用：查询AWEL Flow相关操作
  - 参数：
    - `user_name`（query，`Optional[str]`）: user name，默认值 `Query(default=None, description='user name')`
    - `sys_code`（query，`Optional[str]`）: system code，默认值 `Query(default=None, description='system code')`
    - `page`（query，`int`）: current page，默认值 `Query(default=1, description='current page')`
    - `page_size`（query，`int`）: page size，默认值 `Query(default=20, description='page size')`
    - `name`（query，`Optional[str]`）: flow name，默认值 `Query(default=None, description='flow name')`
    - `uid`（query，`Optional[str]`）: flow uid，默认值 `Query(default=None, description='flow uid')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/flow/api/endpoints.py:207`
- `GET /api/v1/serve/awel/flows` / `GET /api/v2/serve/awel/flows`
  - 作用：Query Flow entities
  - 参数：
    - `user_name`（query，`Optional[str]`）: user name，默认值 `Query(default=None, description='user name')`
    - `sys_code`（query，`Optional[str]`）: system code，默认值 `Query(default=None, description='system code')`
    - `page`（query，`int`）: current page，默认值 `Query(default=1, description='current page')`
    - `page_size`（query，`int`）: page size，默认值 `Query(default=20, description='page size')`
    - `name`（query，`Optional[str]`）: flow name，默认值 `Query(default=None, description='flow name')`
    - `uid`（query，`Optional[str]`）: flow uid，默认值 `Query(default=None, description='flow uid')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/flow/api/endpoints.py:236`
- `GET /api/v1/serve/awel/nodes` / `GET /api/v2/serve/awel/nodes`
  - 作用：Get the operator or resource nodes
  - 参数：
    - `user_name`（query，`Optional[str]`）: user name，默认值 `Query(default=None, description='user name')`
    - `sys_code`（query，`Optional[str]`）: system code，默认值 `Query(default=None, description='system code')`
    - `tags`（query，`Optional[str]`）: tags，默认值 `Query(default=None, description='tags')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/flow/api/endpoints.py:268`
- `POST /api/v1/serve/awel/nodes/refresh` / `POST /api/v2/serve/awel/nodes/refresh`
  - 作用：Refresh the operator or resource nodes
  - 参数：
    - `refresh_request`（body，`RefreshNodeRequest`）: 请求体对象，使用模型 `RefreshNodeRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/flow/api/endpoints.py:304`
- `POST /api/v1/serve/awel/variables` / `POST /api/v2/serve/awel/variables`
  - 作用：Create a new Variables entity
  - 参数：
    - `variables_request`（body，`VariablesRequest`）: The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/flow/api/endpoints.py:330`
- `PUT /api/v1/serve/awel/variables/{v_id}` / `PUT /api/v2/serve/awel/variables/{v_id}`
  - 作用：Update a Variables entity
  - 参数：
    - `v_id`（path，`int`）: The variable id
    - `variables_request`（body，`VariablesRequest`）: The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/flow/api/endpoints.py:351`
- `GET /api/v1/serve/awel/variables` / `GET /api/v2/serve/awel/variables`
  - 作用：Get the variables by keys
  - 参数：
    - `key`（query，`str`）: variable key，默认值 `Query(..., description='variable key')`
    - `scope`（query，`Optional[str]`）: scope，默认值 `Query(default=None, description='scope')`
    - `scope_key`（query，`Optional[str]`）: scope key，默认值 `Query(default=None, description='scope key')`
    - `user_name`（query，`Optional[str]`）: user name，默认值 `Query(default=None, description='user name')`
    - `sys_code`（query，`Optional[str]`）: system code，默认值 `Query(default=None, description='system code')`
    - `page`（query，`int`）: current page，默认值 `Query(default=1, description='current page')`
    - `page_size`（query，`int`）: page size，默认值 `Query(default=20, description='page size')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/flow/api/endpoints.py:373`
- `GET /api/v1/serve/awel/variables/keys` / `GET /api/v2/serve/awel/variables/keys`
  - 作用：Get the variable keys
  - 参数：
    - `user_name`（query，`Optional[str]`）: user name，默认值 `Query(default=None, description='user name')`
    - `sys_code`（query，`Optional[str]`）: system code，默认值 `Query(default=None, description='system code')`
    - `category`（query，`Optional[str]`）: category，默认值 `Query(default=None, description='category')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/flow/api/endpoints.py:404`
- `POST /api/v1/serve/awel/flow/debug` / `POST /api/v2/serve/awel/flow/debug`
  - 作用：Run the flow in debug mode.
  - 参数：
    - `flow_debug_request`（body，`FlowDebugRequest`）: 请求体对象，使用模型 `FlowDebugRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/flow/api/endpoints.py:425`
- `GET /api/v1/serve/awel/flow/export/{uid}` / `GET /api/v2/serve/awel/flow/export/{uid}`
  - 作用：Export the flow to a file.
  - 参数：
    - `uid`（path，`str`）: 资源唯一标识
    - `export_type`（query，`Literal['json', 'dbgpts']`）: export type(json or dbgpts)，默认值 `Query('json', description='export type(json or dbgpts)')`
    - `format`（query，`Literal['file', 'json']`）: response format(file or json)，默认值 `Query('file', description='response format(file or json)')`
    - `file_name`（query，`Optional[str]`）: file name to export，默认值 `Query(default=None, description='file name to export')`
    - `user_name`（query，`Optional[str]`）: user name，默认值 `Query(default=None, description='user name')`
    - `sys_code`（query，`Optional[str]`）: system code，默认值 `Query(default=None, description='system code')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/flow/api/endpoints.py:446`
- `POST /api/v1/serve/awel/flow/import` / `POST /api/v2/serve/awel/flow/import`
  - 作用：Import the flow from a file.
  - 参数：
    - `file`（file，`UploadFile`）: 参数含义需结合同名模型/业务字段理解，默认值 `File(...)`
    - `save_flow`（query，`bool`）: Whether to save the flow after importing，默认值 `Query(False, description='Whether to save the flow after importing')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/flow/api/endpoints.py:504`
- `GET /api/v1/serve/awel/flow/templates` / `GET /api/v2/serve/awel/flow/templates`
  - 作用：Query Flow templates.
  - 参数：
    - `user_name`（query，`Optional[str]`）: user name，默认值 `Query(default=None, description='user name')`
    - `sys_code`（query，`Optional[str]`）: system code，默认值 `Query(default=None, description='system code')`
    - `page`（query，`int`）: current page，默认值 `Query(default=1, description='current page')`
    - `page_size`（query，`int`）: page size，默认值 `Query(default=20, description='page size')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/flow/api/endpoints.py:545`
- `GET /api/v1/serve/awel/flow/notebook/file/path` / `GET /api/v2/serve/awel/flow/notebook/file/path`
  - 作用：处理AWEL Flow相关操作
  - 参数：
    - `flow_uid`（query，`str`）: 参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/flow/api/endpoints.py:570`

### Agent Chat Serve API

基础前缀：`/api/v1/serve/agent/chat`

- `GET /api/v1/serve/agent/chat/health`
  - 作用：Health check endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/chat/api/endpoints.py:86`
- `GET /api/v1/serve/agent/chat/test_auth`
  - 作用：Test auth endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/chat/api/endpoints.py:92`
- `POST /api/v1/serve/agent/chat/`
  - 作用：Create a new Agent/chat entity
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/chat/api/endpoints.py:100`
- `PUT /api/v1/serve/agent/chat/`
  - 作用：Update a Agent/chat entity
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/chat/api/endpoints.py:117`
- `POST /api/v1/serve/agent/chat/query`
  - 作用：Query Agent/chat entities
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/chat/api/endpoints.py:136`
- `POST /api/v1/serve/agent/chat/query_page`
  - 作用：Query Agent/chat entities
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
    - `page`（query，`Optional[int]`）: current page，默认值 `Query(default=1, description='current page')`
    - `page_size`（query，`Optional[int]`）: page size，默认值 `Query(default=20, description='page size')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/chat/api/endpoints.py:155`

### Agent Hub API

基础前缀：`/api`

- `POST /api/v1/agent/hub/update`
  - 作用：更新Agent Hub相关操作
  - 参数：
    - `update_param`（body，`PluginHubParam`）: 请求体对象，使用模型 `PluginHubParam`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/hub/controller.py:48`
- `POST /api/v1/agent/query`
  - 作用：列表查询Agent Hub相关操作
  - 参数：
    - `filter`（body，`PagenationFilter[PluginHubFilter]`）: 请求体对象，使用模型 `PagenationFilter`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/hub/controller.py:70`
- `POST /api/v1/agent/my`
  - 作用：处理Agent Hub相关操作
  - 参数：
    - `user`（body，`str`）: 参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/hub/controller.py:92`
- `POST /api/v1/agent/install`
  - 作用：安装Agent Hub相关操作
  - 参数：
    - `plugin_name`（body，`str`）: 参数含义需结合同名模型/业务字段理解
    - `user`（body，`str`）: 参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/hub/controller.py:100`
- `POST /api/v1/agent/uninstall`
  - 作用：卸载Agent Hub相关操作
  - 参数：
    - `plugin_name`（body，`str`）: 参数含义需结合同名模型/业务字段理解
    - `user`（body，`str`）: 参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/hub/controller.py:114`
- `POST /api/v1/personal/agent/upload`
  - 作用：上传Agent Hub相关操作
  - 参数：
    - `doc_file`（file，`UploadFile`）: 参数含义需结合同名模型/业务字段理解，默认值 `File(...)`
    - `user`（body，`str`）: 参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/hub/controller.py:127`

### DBGPTS Hub API

基础前缀：`/api/v1/serve/dbgpts/hub`

- `GET /api/v1/serve/dbgpts/hub/health`
  - 作用：Health check endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/dbgpts/hub/api/endpoints.py:89`
- `GET /api/v1/serve/dbgpts/hub/test_auth`
  - 作用：Test auth endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/dbgpts/hub/api/endpoints.py:95`
- `POST /api/v1/serve/dbgpts/hub/`
  - 作用：Create a new DbgptsHub entity
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/dbgpts/hub/api/endpoints.py:103`
- `PUT /api/v1/serve/dbgpts/hub/`
  - 作用：Update a DbgptsHub entity
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/dbgpts/hub/api/endpoints.py:120`
- `POST /api/v1/serve/dbgpts/hub/query`
  - 作用：Query DbgptsHub entities
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/dbgpts/hub/api/endpoints.py:139`
- `POST /api/v1/serve/dbgpts/hub/query_page`
  - 作用：Query DbgptsHub entities
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
    - `page`（query，`Optional[int]`）: current page，默认值 `Query(default=1, description='current page')`
    - `page_size`（query，`Optional[int]`）: page size，默认值 `Query(default=20, description='page size')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/dbgpts/hub/api/endpoints.py:158`
- `POST /api/v1/serve/dbgpts/hub/source/refresh`
  - 作用：刷新DBGPTS Hub相关操作
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/dbgpts/hub/api/endpoints.py:182`
- `POST /api/v1/serve/dbgpts/hub/install`
  - 作用：安装DBGPTS Hub相关操作
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/dbgpts/hub/api/endpoints.py:199`

### Libro API

基础前缀：`/api/v1/serve/libro`

- `GET /api/v1/serve/libro/health`
  - 作用：Health check endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/libro/api/endpoints.py:86`
- `GET /api/v1/serve/libro/test_auth`
  - 作用：Test auth endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/libro/api/endpoints.py:92`
- `POST /api/v1/serve/libro/`
  - 作用：Create a new Libro entity
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/libro/api/endpoints.py:100`
- `PUT /api/v1/serve/libro/`
  - 作用：Update a Libro entity
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/libro/api/endpoints.py:117`
- `POST /api/v1/serve/libro/query`
  - 作用：Query Libro entities
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/libro/api/endpoints.py:136`
- `POST /api/v1/serve/libro/query_page`
  - 作用：Query Libro entities
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
    - `page`（query，`Optional[int]`）: current page，默认值 `Query(default=1, description='current page')`
    - `page_size`（query，`Optional[int]`）: page size，默认值 `Query(default=20, description='page size')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/libro/api/endpoints.py:155`

### Prompt 管理 API

基础前缀：`/prompt`

- `GET /prompt/health`
  - 作用：Health check endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/prompt/api/endpoints.py:81`
- `GET /prompt/test_auth`
  - 作用：Test auth endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/prompt/api/endpoints.py:87`
- `POST /prompt/add`
  - 作用：Create a new Prompt entity
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/prompt/api/endpoints.py:96`
- `POST /prompt/update`
  - 作用：Update a Prompt entity
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/prompt/api/endpoints.py:115`
- `POST /prompt/delete`
  - 作用：Delete a Prompt entity
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/prompt/api/endpoints.py:137`
- `POST /prompt/list`
  - 作用：Query Prompt entities
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/prompt/api/endpoints.py:156`
- `POST /prompt/query_page`
  - 作用：Query Prompt entities
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
    - `page`（query，`Optional[int]`）: current page，默认值 `Query(default=1, description='current page')`
    - `page_size`（query，`Optional[int]`）: page size，默认值 `Query(default=20, description='page size')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/prompt/api/endpoints.py:175`
- `GET /prompt/type/targets`
  - 作用：get Prompt type
  - 参数：
    - `prompt_type`（query，`str`）: Prompt template type，默认值 `Query(default=PromptType.NORMAL, description='Prompt template type')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/prompt/api/endpoints.py:199`
- `POST /prompt/template/load`
  - 作用：load Prompt from target
  - 参数：
    - `prompt_type`（query，`str`）: Prompt template type，默认值 `Query(default=PromptType.NORMAL, description='Prompt template type')`
    - `target`（query，`Optional[str]`）: The target to load the template from，默认值 `Query(default=None, description='The target to load the template from')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/prompt/api/endpoints.py:220`
- `POST /prompt/template/debug`
  - 作用：test Prompt
  - 参数：
    - `debug_input`（body，`PromptDebugInput`）: 请求体对象，使用模型 `PromptDebugInput`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/prompt/api/endpoints.py:244`
- `POST /prompt/response/verify`
  - 作用：test Prompt
  - 参数：
    - `request`（body，`PromptVerifyInput`）: 请求体对象，使用模型 `PromptVerifyInput`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/prompt/api/endpoints.py:279`

### Python 文件上传 API

基础前缀：`/api`

- `POST /api/v1/python/file/upload`
  - 作用：上传Python 文件上传相关操作
  - 参数：
    - `file`（file，`UploadFile`）: 参数含义需结合同名模型/业务字段理解，默认值 `File(...)`
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/python_upload_api.py:16`

### RAG / Knowledge Serve API

基础前缀：`/api/v2/serve/knowledge`

- `GET /api/v2/serve/knowledge/health`
  - 作用：Health check endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/rag/api/endpoints.py:100`
- `GET /api/v2/serve/knowledge/test_auth`
  - 作用：Test auth endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/rag/api/endpoints.py:106`
- `POST /api/v2/serve/knowledge/spaces`
  - 作用：Create a new Space entity
  - 参数：
    - `request`（body，`SpaceServeRequest`）: 请求体对象，使用模型 `SpaceServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/rag/api/endpoints.py:112`
- `PUT /api/v2/serve/knowledge/spaces`
  - 作用：Update a Space entity
  - 参数：
    - `request`（body，`SpaceServeRequest`）: 请求体对象，使用模型 `SpaceServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/rag/api/endpoints.py:128`
- `DELETE /api/v2/serve/knowledge/spaces/{space_id}`
  - 作用：Delete a Space entity
  - 参数：
    - `space_id`（path，`str`）: 知识空间 ID
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/rag/api/endpoints.py:147`
- `GET /api/v2/serve/knowledge/spaces/{space_id}`
  - 作用：Query Space entities
  - 参数：
    - `space_id`（path，`str`）: 知识空间 ID
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/rag/api/endpoints.py:167`
- `GET /api/v2/serve/knowledge/spaces`
  - 作用：Query Space entities
  - 参数：
    - `page`（query，`int`）: current page，默认值 `Query(default=1, description='current page')`
    - `page_size`（query，`int`）: page size，默认值 `Query(default=20, description='page size')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/rag/api/endpoints.py:187`
- `POST /api/v2/serve/knowledge/spaces/{space_id}/retrieve`
  - 作用：Create a new Document entity
  - 参数：
    - `space_id`（path，`int`）: The space id
    - `request`（body，`KnowledgeRetrieveRequest`）: 请求体对象，使用模型 `KnowledgeRetrieveRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/rag/api/endpoints.py:205`
- `POST /api/v2/serve/knowledge/documents`
  - 作用：Create a new Document entity
  - 参数：
    - `doc_name`（form，`str`）: 参数含义需结合同名模型/业务字段理解，默认值 `Form(...)`
    - `doc_type`（form，`str`）: 参数含义需结合同名模型/业务字段理解，默认值 `Form(...)`
    - `space_id`（form，`str`）: 知识空间 ID，默认值 `Form(...)`
    - `content`（form，`Optional[str]`）: 正文内容，默认值 `Form(None)`
    - `doc_file`（form，`Union[UploadFile, str]`）: 参数含义需结合同名模型/业务字段理解，默认值 `Form(None)`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/rag/api/endpoints.py:230`
- `GET /api/v2/serve/knowledge/documents/{document_id}`
  - 作用：Query Space entities
  - 参数：
    - `document_id`（path，`int`）: 文档 ID
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/rag/api/endpoints.py:263`
- `GET /api/v2/serve/knowledge/documents`
  - 作用：Query Space entities
  - 参数：
    - `page`（query，`int`）: current page，默认值 `Query(default=1, description='current page')`
    - `page_size`（query，`int`）: page size，默认值 `Query(default=20, description='page size')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/rag/api/endpoints.py:283`
- `POST /api/v2/serve/knowledge/documents/chunks/add`
  - 作用：新增RAG / Knowledge Serve相关操作
  - 参数：
    - `doc_name`（form，`str`）: 参数含义需结合同名模型/业务字段理解，默认值 `Form(...)`
    - `space_id`（form，`int`）: 知识空间 ID，默认值 `Form(...)`
    - `content`（form，`List[str]`）: 正文内容，默认值 `Form(None)`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/rag/api/endpoints.py:301`
- `POST /api/v2/serve/knowledge/documents/sync`
  - 作用：Create a new Document entity
  - 参数：
    - `requests`（body，`List[KnowledgeSyncRequest]`）: 请求体对象，使用模型 `KnowledgeSyncRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/rag/api/endpoints.py:311`
- `POST /api/v2/serve/knowledge/documents/batch_sync`
  - 作用：Create a new Document entity
  - 参数：
    - `requests`（body，`List[KnowledgeSyncRequest]`）: 请求体对象，使用模型 `KnowledgeSyncRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/rag/api/endpoints.py:326`
- `POST /api/v2/serve/knowledge/documents/{document_id}/sync`
  - 作用：Create a new Document entity
  - 参数：
    - `document_id`（path，`int`）: 文档 ID
    - `request`（body，`KnowledgeSyncRequest`）: 请求体对象，使用模型 `KnowledgeSyncRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/rag/api/endpoints.py:342`
- `DELETE /api/v2/serve/knowledge/documents/{document_id}`
  - 作用：Delete a Space entity
  - 参数：
    - `document_id`（path，`str`）: 文档 ID
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/rag/api/endpoints.py:366`

### SQL/图表编辑器 API

基础前缀：`/api`

- `GET /api/v1/editor/db/tables`
  - 作用：编辑SQL/图表编辑器相关操作
  - 参数：
    - `db_name`（query，`str`）: 数据库名称
    - `page_index`（query，`int`）: 参数含义需结合同名模型/业务字段理解
    - `page_size`（query，`int`）: 每页条数
    - `search_str`（query，`str`）: 参数含义需结合同名模型/业务字段理解，默认值 `''`
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/editor/api_editor_v1.py:48`
- `GET /api/v1/editor/sql/rounds`
  - 作用：编辑SQL/图表编辑器相关操作
  - 参数：
    - `con_uid`（query，`str`）: 会话唯一 ID
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/editor/api_editor_v1.py:75`
- `GET /api/v1/editor/sql`
  - 作用：编辑SQL/图表编辑器相关操作
  - 参数：
    - `con_uid`（query，`str`）: 会话唯一 ID
    - `round`（query，`int`）: 参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/editor/api_editor_v1.py:88`
- `POST /api/v1/editor/sql/run`
  - 作用：编辑SQL/图表编辑器相关操作
  - 参数：
    - `run_param`（body，`dict`）: 参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/editor/api_editor_v1.py:179`
- `POST /api/v1/sql/editor/submit`
  - 作用：编辑SQL/图表编辑器相关操作
  - 参数：
    - `sql_edit_context`（body，`ChatSqlEditContext`）: 请求体对象，使用模型 `ChatSqlEditContext`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/editor/api_editor_v1.py:222`
- `GET /api/v1/editor/chart/list`
  - 作用：编辑SQL/图表编辑器相关操作
  - 参数：
    - `con_uid`（query，`str`）: 会话唯一 ID
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/editor/api_editor_v1.py:238`
- `POST /api/v1/editor/chart/info`
  - 作用：编辑SQL/图表编辑器相关操作
  - 参数：
    - `param`（body，`dict`）: 参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/editor/api_editor_v1.py:252`
- `POST /api/v1/editor/chart/run`
  - 作用：执行SQL/图表编辑器相关操作
  - 参数：
    - `run_param`（body，`dict`）: 参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/editor/api_editor_v1.py:262`
- `POST /api/v1/chart/editor/submit`
  - 作用：编辑SQL/图表编辑器相关操作
  - 参数：
    - `chart_edit_context`（body，`ChatChartEditContext`）: 请求体对象，使用模型 `ChatChartEditContext`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/editor/api_editor_v1.py:316`

### 会话管理 API

基础前缀：`/api/v1/chat/dialogue`

- `GET /api/v1/chat/dialogue/health`
  - 作用：Health check endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/conversation/api/endpoints.py:94`
- `GET /api/v1/chat/dialogue/test_auth`
  - 作用：Test auth endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/conversation/api/endpoints.py:100`
- `POST /api/v1/chat/dialogue/query`
  - 作用：Query Conversation entities
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/conversation/api/endpoints.py:110`
- `POST /api/v1/chat/dialogue/new`
  - 作用：新建会话管理相关操作
  - 参数：
    - `chat_mode`（body，`str`）: 聊天模式，默认值 `'chat_normal'`
    - `app_code`（body，`str`）: 应用编码
    - `user_name`（body，`str`）: 用户名
    - `user_id`（body，`str`）: 用户 ID
    - `sys_code`（body，`str`）: 系统编码/租户编码
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/conversation/api/endpoints.py:129`
- `POST /api/v1/chat/dialogue/delete`
  - 作用：Delete a Conversation entity
  - 参数：
    - `con_uid`（body，`str`）: The conversation UID
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/conversation/api/endpoints.py:153`
- `POST /api/v1/chat/dialogue/clear`
  - 作用：Clear a Conversation entity
  - 参数：
    - `con_uid`（body，`str`）: The conversation UID
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/conversation/api/endpoints.py:168`
- `POST /api/v1/chat/dialogue/query_page`
  - 作用：Query Conversation entities
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
    - `page`（query，`Optional[int]`）: current page，默认值 `Query(default=1, description='current page')`
    - `page_size`（query，`Optional[int]`）: page size，默认值 `Query(default=10, description='page size')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/conversation/api/endpoints.py:187`
- `GET /api/v1/chat/dialogue/list`
  - 作用：Return latest conversations
  - 参数：
    - `user_name`（query，`str`）: 用户名
    - `user_id`（query，`str`）: 用户 ID
    - `sys_code`（query，`str`）: 系统编码/租户编码
    - `page`（query，`Optional[int]`）: current page，默认值 `Query(default=1, description='current page')`
    - `page_size`（query，`Optional[int]`）: page size，默认值 `Query(default=10, description='page size')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/conversation/api/endpoints.py:211`
- `GET /api/v1/chat/dialogue/messages/history`
  - 作用：Get the history messages of a conversation
  - 参数：
    - `con_uid`（query，`str`）: 会话唯一 ID
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/conversation/api/endpoints.py:232`
- `GET /api/v1/chat/dialogue/export_messages`
  - 作用：Export all conversations and messages for a user
  - 参数：
    - `user_name`（query，`Optional[str]`）: The user name
    - `user_id`（query，`Optional[str]`）: The user id (alternative to user_name)
    - `sys_code`（query，`Optional[str]`）: The system code
    - `format`（query，`Literal['file', 'json']`）: response format(file or json)，默认值 `Query('file', description='response format(file or json)')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/conversation/api/endpoints.py:241`

### 应用市场/DBGPTS API

基础前缀：`/api`

- `POST /api/v1/app/create`
  - 作用：创建应用市场/DBGPTS相关操作
  - 参数：
    - `gpts_app`（body，`GptsApp`）: 请求体对象，使用模型 `GptsApp`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:33`
- `POST /api/v1/app/list`
  - 作用：列表查询应用市场/DBGPTS相关操作
  - 参数：
    - `query`（body，`GptsAppQuery`）: 请求体对象，使用模型 `GptsAppQuery`。查询条件
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:47`
- `GET /api/v1/app/info`
  - 作用：查看详情应用市场/DBGPTS相关操作
  - 参数：
    - `chat_scene`（query，`str`）: 参数含义需结合同名模型/业务字段理解
    - `app_code`（query，`str`）: 应用编码
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:66`
- `GET /api/v1/app/export`
  - 作用：导出应用市场/DBGPTS相关操作
  - 参数：
    - `chat_scene`（query，`str`）: 参数含义需结合同名模型/业务字段理解
    - `app_code`（query，`str`）: 应用编码
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:91`
- `GET /api/v1/app/{app_code}`
  - 作用：处理应用市场/DBGPTS相关操作
  - 参数：
    - `app_code`（path，`str`）: 应用编码
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:116`
- `POST /api/v1/app/hot/list`
  - 作用：列表查询应用市场/DBGPTS相关操作
  - 参数：
    - `query`（body，`GptsAppQuery`）: 请求体对象，使用模型 `GptsAppQuery`。查询条件
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:127`
- `POST /api/v1/app/detail`
  - 作用：列表查询应用市场/DBGPTS相关操作
  - 参数：
    - `gpts_app`（body，`GptsApp`）: 请求体对象，使用模型 `GptsApp`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:142`
- `POST /api/v1/app/edit`
  - 作用：编辑应用市场/DBGPTS相关操作
  - 参数：
    - `gpts_app`（body，`GptsApp`）: 请求体对象，使用模型 `GptsApp`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:155`
- `GET /api/v1/agents/list`
  - 作用：处理应用市场/DBGPTS相关操作
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:169`
- `POST /api/v1/app/remove`
  - 作用：删除应用市场/DBGPTS相关操作
  - 参数：
    - `gpts_app`（body，`GptsApp`）: 请求体对象，使用模型 `GptsApp`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:181`
- `POST /api/v1/app/collect`
  - 作用：处理应用市场/DBGPTS相关操作
  - 参数：
    - `gpts_app`（body，`GptsApp`）: 请求体对象，使用模型 `GptsApp`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:196`
- `POST /api/v1/app/uncollect`
  - 作用：处理应用市场/DBGPTS相关操作
  - 参数：
    - `gpts_app`（body，`GptsApp`）: 请求体对象，使用模型 `GptsApp`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:210`
- `GET /api/v1/team-mode/list`
  - 作用：列表查询应用市场/DBGPTS相关操作
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:226`
- `GET /api/v1/resource-type/list`
  - 作用：列表查询应用市场/DBGPTS相关操作
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:235`
- `GET /api/v1/llm-strategy/list`
  - 作用：处理应用市场/DBGPTS相关操作
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:245`
- `GET /api/v1/llm-strategy/value/list`
  - 作用：处理应用市场/DBGPTS相关操作
  - 参数：
    - `type`（query，`str`）: 参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:256`
- `GET /api/v1/app/resources/list`
  - 作用：Get agent resources, such as db, knowledge, internet, plugin.
  - 参数：
    - `type`（query，`str`）: 参数含义需结合同名模型/业务字段理解
    - `name`（query，`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
    - `version`（query，`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
    - `user_code`（query，`Optional[str]`）: 用户编码
    - `sys_code`（query，`Optional[str]`）: 系统编码/租户编码
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:273`
- `POST /api/v1/app/publish`
  - 作用：发布应用市场/DBGPTS相关操作
  - 参数：
    - `gpts_app`（body，`GptsApp`）: 请求体对象，使用模型 `GptsApp`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:300`
- `POST /api/v1/app/unpublish`
  - 作用：发布应用市场/DBGPTS相关操作
  - 参数：
    - `gpts_app`（body，`GptsApp`）: 请求体对象，使用模型 `GptsApp`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:315`
- `POST /api/v1/app/native/init`
  - 作用：处理应用市场/DBGPTS相关操作
  - 参数：
    - `gpts_app`（body，`GptsApp`）: 请求体对象，使用模型 `GptsApp`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:330`
- `GET /api/v1/native_scenes`
  - 作用：处理应用市场/DBGPTS相关操作
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:345`
- `POST /api/v1/app/admins/update`
  - 作用：更新应用市场/DBGPTS相关操作
  - 参数：
    - `gpts_app`（body，`GptsApp`）: 请求体对象，使用模型 `GptsApp`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:350`
- `GET /api/v1/app/{app_code}/admins`
  - 作用：查询应用市场/DBGPTS相关操作
  - 参数：
    - `app_code`（path，`str`）: 应用编码
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:357`
- `GET /api/v1/dbgpts/list`
  - 作用：处理应用市场/DBGPTS相关操作
  - 参数：
    - `user_code`（query，`str`）: 用户编码
    - `sys_code`（query，`str`）: 系统编码/租户编码
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/controller.py:369`

### 应用服务 v2 API

基础前缀：`/api`

- `GET /api/v2/serve/apps`
  - 作用：列表查询应用服务 v2相关操作
  - 参数：
    - `user_name`（query，`Optional[str]`）: user name，默认值 `Query(default=None, description='user name')`
    - `sys_code`（query，`Optional[str]`）: system code，默认值 `Query(default=None, description='system code')`
    - `is_collected`（query，`Optional[str]`）: system code，默认值 `Query(default=None, description='system code')`
    - `page`（query，`int`）: current page，默认值 `Query(default=1, description='current page')`
    - `page_size`（query，`int`）: page size，默认值 `Query(default=20, description='page size')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/endpoints.py:19`
- `GET /api/v2/serve/apps/{app_id}`
  - 作用：查看详情应用服务 v2相关操作
  - 参数：
    - `app_id`（path，`str`）: 应用 ID
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/endpoints.py:36`
- `PUT /api/v2/serve/apps/{app_id}`
  - 作用：更新应用服务 v2相关操作
  - 参数：
    - `app_id`（path，`str`）: 应用 ID
    - `gpts_app`（body，`GptsApp`）: 请求体对象，使用模型 `GptsApp`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/endpoints.py:44`
- `POST /api/v2/serve/apps`
  - 作用：创建应用服务 v2相关操作
  - 参数：
    - `gpts_app`（body，`GptsApp`）: 请求体对象，使用模型 `GptsApp`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/endpoints.py:52`
- `DELETE /api/v2/serve/apps/{app_id}`
  - 作用：删除应用服务 v2相关操作
  - 参数：
    - `app_id`（path，`str`）: 应用 ID
    - `user_code`（query，`Optional[str]`）: 用户编码
    - `sys_code`（query，`Optional[str]`）: 系统编码/租户编码
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/endpoints.py:60`

### 我的 DBGPTS API

基础前缀：`/api/v1/serve/dbgpts/my`

- `GET /api/v1/serve/dbgpts/my/health`
  - 作用：Health check endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/dbgpts/my/api/endpoints.py:89`
- `GET /api/v1/serve/dbgpts/my/test_auth`
  - 作用：Test auth endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/dbgpts/my/api/endpoints.py:95`
- `POST /api/v1/serve/dbgpts/my/`
  - 作用：Create a new DbgptsMy entity
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/dbgpts/my/api/endpoints.py:103`
- `PUT /api/v1/serve/dbgpts/my/`
  - 作用：Update a DbgptsMy entity
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/dbgpts/my/api/endpoints.py:120`
- `POST /api/v1/serve/dbgpts/my/query`
  - 作用：Query DbgptsMy entities
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/dbgpts/my/api/endpoints.py:139`
- `POST /api/v1/serve/dbgpts/my/query_page`
  - 作用：Query DbgptsMy entities
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
    - `page`（query，`Optional[int]`）: current page，默认值 `Query(default=1, description='current page')`
    - `page_size`（query，`Optional[int]`）: page size，默认值 `Query(default=20, description='page size')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/dbgpts/my/api/endpoints.py:158`
- `POST /api/v1/serve/dbgpts/my/uninstall`
  - 作用：卸载我的 DBGPTS相关操作
  - 参数：
    - `name`（body，`str`）: 参数含义需结合同名模型/业务字段理解
    - `type`（body，`unknown`）: 参数含义需结合同名模型/业务字段理解，默认值 `str`
    - `user`（body，`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/dbgpts/my/api/endpoints.py:178`

### 技能/分享/React Agent API

基础前缀：`/api`

- `GET /api/v1/skills/list`
  - 作用：List all available skills from the skills directory.
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/agentic_data_api.py:142`
- `GET /api/v1/skills/detail`
  - 作用：Load a skill detail, including file tree and SKILL.md content.
  - 参数：
    - `skill_name`（query，`str`）: Skill name，默认值 `Query('', description='Skill name')`
    - `file_path`（query，`str`）: Skill file path，默认值 `Query('', description='Skill file path')`
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/agentic_data_api.py:225`
- `POST /api/v1/skills/upload`
  - 作用：Upload a skill package (.zip, .skill) or a single file to pilot/tmp/.
  - 参数：
    - `file`（file，`UploadFile`）: 参数含义需结合同名模型/业务字段理解，默认值 `File(...)`
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/agentic_data_api.py:381`
- `POST /api/v1/skills/import_github`
  - 作用：Import a skill from a GitHub or skills.sh URL.
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/agentic_data_api.py:672`
- `POST /api/v1/chat/share`
  - 作用：Create (or return existing) share link for a conversation.
  - 参数：
    - `body`（body，`ShareCreateRequest`）: 请求体对象，使用模型 `ShareCreateRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/agentic_data_api.py:3305`
- `GET /api/v1/chat/share/{token}`
  - 作用：Public endpoint — no authentication required.
  - 参数：
    - `token`（path，`str`）: 分享 Token 或访问令牌
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/agentic_data_api.py:3329`
- `DELETE /api/v1/chat/share/{token}`
  - 作用：Revoke a share link.  Only the owner (or any authenticated user) may delete.
  - 参数：
    - `token`（path，`str`）: 分享 Token 或访问令牌
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/agentic_data_api.py:3361`
- `GET /api/v1/agent/files/download`
  - 作用：Download a file created by agent tools (shell_interpreter, code_interpreter).
  - 参数：
    - `file_path`（query，`str`）: Absolute path to the file to download，默认值 `Query(..., description='Absolute path to the file to download')`
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/agentic_data_api.py:3376`
- `GET /api/v1/agent/skills/download`
  - 作用：Download a skill folder as a .zip archive.
  - 参数：
    - `skill_name`（query，`str`）: Skill folder name，默认值 `Query(..., description='Skill folder name')`
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/agentic_data_api.py:3424`
- `POST /api/v1/chat/react-agent`
  - 作用：处理技能/分享/React Agent相关操作
  - 参数：
    - `dialogue`（body，`ConversationVo`）: 请求体对象，使用模型 `ConversationVo`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/agentic_data_api.py:3466`

### 推荐问题 API

基础前缀：`/api`

- `POST /api/v1/question/create`
  - 作用：创建推荐问题相关操作
  - 参数：
    - `recommend_question`（body，`RecommendQuestion`）: 请求体对象，使用模型 `RecommendQuestion`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/recommend_question/controller.py:19`
- `GET /api/v1/question/list`
  - 作用：查询推荐问题相关操作
  - 参数：
    - `valid`（query，`str`）: 参数含义需结合同名模型/业务字段理解
    - `app_code`（query，`str`）: 应用编码
    - `chat_mode`（query，`str`）: 聊天模式
    - `is_hot_question`（query，`str`）: 参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/recommend_question/controller.py:32`
- `POST /api/v1/question/update`
  - 作用：更新推荐问题相关操作
  - 参数：
    - `recommend_question`（body，`RecommendQuestion`）: 请求体对象，使用模型 `RecommendQuestion`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/recommend_question/controller.py:55`
- `POST /api/v1/question/delete`
  - 作用：删除推荐问题相关操作
  - 参数：
    - `recommend_question`（body，`RecommendQuestion`）: 请求体对象，使用模型 `RecommendQuestion`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/recommend_question/controller.py:69`

### 数据源 API

基础前缀：`/api/v2/serve`

- `GET /api/v2/serve/health`
  - 作用：Health check endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/datasource/api/endpoints.py:88`
- `GET /api/v2/serve/test_auth`
  - 作用：Test auth endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/datasource/api/endpoints.py:94`
- `POST /api/v2/serve/datasources`
  - 作用：Create a new Space entity
  - 参数：
    - `request`（body，`Union[DatasourceCreateRequest, DatasourceServeRequest]`）: 请求体对象，使用模型 `DatasourceCreateRequest` / `DatasourceServeRequest`。The request to create a datasource. DatasourceServeRequest is deprecated.
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/datasource/api/endpoints.py:104`
- `PUT /api/v2/serve/datasources`
  - 作用：Update a Space entity
  - 参数：
    - `request`（body，`Union[DatasourceCreateRequest, DatasourceServeRequest]`）: 请求体对象，使用模型 `DatasourceCreateRequest` / `DatasourceServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/datasource/api/endpoints.py:126`
- `DELETE /api/v2/serve/datasources/{datasource_id}`
  - 作用：Delete a Space entity
  - 参数：
    - `datasource_id`（path，`str`）: 数据源 ID
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/datasource/api/endpoints.py:147`
- `GET /api/v2/serve/datasources/{datasource_id}`
  - 作用：Query Space entities
  - 参数：
    - `datasource_id`（path，`str`）: 数据源 ID
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/datasource/api/endpoints.py:167`
- `GET /api/v2/serve/datasources`
  - 作用：Query Space entities
  - 参数：
    - `db_type`（query，`Optional[str]`）: Database type, e.g. sqlite, mysql, etc.，默认值 `Query(None, description='Database type, e.g. sqlite, mysql, etc.')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/datasource/api/endpoints.py:187`
- `GET /api/v2/serve/datasource-types`
  - 作用：Get the datasource types.
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/datasource/api/endpoints.py:211`
- `POST /api/v2/serve/datasources/test-connection`
  - 作用：Test the connection using datasource configuration before creating it
  - 参数：
    - `request`（body，`DatasourceCreateRequest`）: 请求体对象，使用模型 `DatasourceCreateRequest`。The datasource configuration to test
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/datasource/api/endpoints.py:224`
- `POST /api/v2/serve/datasources/{datasource_id}/refresh`
  - 作用：Refresh a datasource by its ID
  - 参数：
    - `datasource_id`（path，`str`）: The ID of the datasource to refresh
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/datasource/api/endpoints.py:250`

### 文件服务 API

基础前缀：`/api/v2/serve/file`

- `GET /api/v2/serve/file/health`
  - 作用：Health check endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/file/api/endpoints.py:94`
- `GET /api/v2/serve/file/test_auth`
  - 作用：Test auth endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/file/api/endpoints.py:100`
- `POST /api/v2/serve/file/files/{bucket}`
  - 作用：Upload files by a list of UploadFile.
  - 参数：
    - `bucket`（path，`str`）: 文件桶名称
    - `files`（file，`List[UploadFile]`）: 参数含义需结合同名模型/业务字段理解
    - `user_name`（query，`Optional[str]`）: user name，默认值 `Query(default=None, description='user name')`
    - `sys_code`（query，`Optional[str]`）: system code，默认值 `Query(default=None, description='system code')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/file/api/endpoints.py:110`
- `GET /api/v2/serve/file/files/{bucket}/{file_id}`
  - 作用：Download a file by file_id.
  - 参数：
    - `bucket`（path，`str`）: 文件桶名称
    - `file_id`（path，`str`）: 文件 ID
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/file/api/endpoints.py:131`
- `DELETE /api/v2/serve/file/files/{bucket}/{file_id}`
  - 作用：Delete a file by file_id.
  - 参数：
    - `bucket`（path，`str`）: 文件桶名称
    - `file_id`（path，`str`）: 文件 ID
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/file/api/endpoints.py:156`
- `GET /api/v2/serve/file/files/metadata`
  - 作用：Get file metadata by URI or by bucket and file_id.
  - 参数：
    - `uri`（query，`Optional[str]`）: File URI，默认值 `Query(None, description='File URI')`
    - `bucket`（query，`Optional[str]`）: Bucket name，默认值 `Query(None, description='Bucket name')`
    - `file_id`（query，`Optional[str]`）: File ID，默认值 `Query(None, description='File ID')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/file/api/endpoints.py:171`
- `POST /api/v2/serve/file/files/metadata/batch`
  - 作用：Get metadata for multiple files by URIs or bucket and file_id pairs.
  - 参数：
    - `request`（body，`FileMetadataBatchRequest`）: 请求体对象，使用模型 `FileMetadataBatchRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/file/api/endpoints.py:195`

### 新版反馈 API

基础前缀：`/api/v1/conv/feedback`

- `GET /api/v1/conv/feedback/health`
  - 作用：Health check endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/feedback/api/endpoints.py:88`
- `GET /api/v1/conv/feedback/test_auth`
  - 作用：Test auth endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/feedback/api/endpoints.py:94`
- `POST /api/v1/conv/feedback/query`
  - 作用：Query Feedback entities
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/feedback/api/endpoints.py:104`
- `POST /api/v1/conv/feedback/query_page`
  - 作用：Query Feedback entities
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。The request
    - `page`（query，`Optional[int]`）: current page，默认值 `Query(default=1, description='current page')`
    - `page_size`（query，`Optional[int]`）: page size，默认值 `Query(default=20, description='page size')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/feedback/api/endpoints.py:123`
- `POST /api/v1/conv/feedback/add`
  - 作用：新增反馈相关操作
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/feedback/api/endpoints.py:143`
- `GET /api/v1/conv/feedback/list`
  - 作用：列表查询反馈相关操作
  - 参数：
    - `conv_uid`（query，`Optional[str]`）: 会话唯一 ID
    - `feedback_type`（query，`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/feedback/api/endpoints.py:152`
- `GET /api/v1/conv/feedback/reasons`
  - 作用：处理反馈相关操作
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/feedback/api/endpoints.py:166`
- `POST /api/v1/conv/feedback/cancel`
  - 作用：处理反馈相关操作
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/feedback/api/endpoints.py:174`
- `POST /api/v1/conv/feedback/update`
  - 作用：更新反馈相关操作
  - 参数：
    - `request`（body，`ServeRequest`）: 请求体对象，使用模型 `ServeRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/feedback/api/endpoints.py:185`

### 旧版反馈 API

基础前缀：`/api`

- `GET /api/v1/feedback/find`
  - 作用：处理反馈相关操作
  - 参数：
    - `conv_uid`（query，`str`）: 会话唯一 ID
    - `conv_index`（query，`int`）: 参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/feedback/api_fb_v1.py:12`
- `POST /api/v1/feedback/commit`
  - 作用：处理反馈相关操作
  - 参数：
    - `feed_back_body`（body，`FeedBackBody`）: 请求体对象，使用模型 `FeedBackBody`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/feedback/api_fb_v1.py:31`
- `GET /api/v1/feedback/select`
  - 作用：处理反馈相关操作
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/feedback/api_fb_v1.py:37`

### 旧版聊天/OpenAPI v1

基础前缀：`/api`

- `GET /api/v1/chat/db/list`
  - 作用：列表查询聊天/OpenAPI v1相关操作
  - 参数：
    - `db_name`（query，`Optional[str]`）: database name，默认值 `Query(default=None, description='database name')`
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py:175`
- `POST /api/v1/chat/db/add`
  - 作用：新增聊天/OpenAPI v1相关操作
  - 参数：
    - `db_config`（body，`DBConfig`）: 请求体对象，使用模型 `DBConfig`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py:193`
- `GET /api/v1/permission/db/list`
  - 作用：列表查询聊天/OpenAPI v1相关操作
  - 参数：
    - `db_name`（query，`str`）: 数据库名称
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py:201`
- `POST /api/v1/chat/db/edit`
  - 作用：编辑聊天/OpenAPI v1相关操作
  - 参数：
    - `db_config`（body，`DBConfig`）: 请求体对象，使用模型 `DBConfig`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py:209`
- `POST /api/v1/chat/db/delete`
  - 作用：删除聊天/OpenAPI v1相关操作
  - 参数：
    - `db_name`（body，`str`）: 数据库名称
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py:217`
- `POST /api/v1/chat/db/refresh`
  - 作用：刷新聊天/OpenAPI v1相关操作
  - 参数：
    - `db_config`（body，`DBConfig`）: 请求体对象，使用模型 `DBConfig`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py:223`
- `POST /api/v1/chat/db/test/connect`
  - 作用：测试聊天/OpenAPI v1相关操作
  - 参数：
    - `db_config`（body，`DBConfig`）: 请求体对象，使用模型 `DBConfig`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py:237`
- `POST /api/v1/chat/db/summary`
  - 作用：处理聊天/OpenAPI v1相关操作
  - 参数：
    - `db_name`（body，`str`）: 数据库名称
    - `db_type`（body，`str`）: 数据库类型
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py:250`
- `GET /api/v1/chat/db/support/type`
  - 作用：处理聊天/OpenAPI v1相关操作
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py:257`
- `POST /api/v1/chat/dialogue/scenes`
  - 作用：处理聊天/OpenAPI v1相关操作
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py:268`
- `POST /api/v1/resource/params/list`
  - 作用：列表查询聊天/OpenAPI v1相关操作
  - 参数：
    - `resource_type`（body，`str`）: 参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py:291`
- `POST /api/v1/chat/mode/params/list`
  - 作用：列表查询聊天/OpenAPI v1相关操作
  - 参数：
    - `chat_mode`（body，`str`）: 聊天模式，默认值 `ChatScene.ChatNormal.value()`
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py:307`
- `POST /api/v1/resource/file/upload`
  - 作用：上传聊天/OpenAPI v1相关操作
  - 参数：
    - `chat_mode`（body，`str`）: 聊天模式
    - `conv_uid`（body，`str`）: 会话唯一 ID
    - `temperature`（body，`Optional[float]`）: 参数含义需结合同名模型/业务字段理解
    - `max_new_tokens`（body，`Optional[int]`）: 参数含义需结合同名模型/业务字段理解
    - `sys_code`（body，`Optional[str]`）: 系统编码/租户编码
    - `model_name`（body，`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
    - `doc_files`（file，`List[UploadFile]`）: 参数含义需结合同名模型/业务字段理解，默认值 `File(...)`
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py:329`
- `POST /api/v1/resource/file/delete`
  - 作用：删除聊天/OpenAPI v1相关操作
  - 参数：
    - `conv_uid`（body，`str`）: 会话唯一 ID
    - `file_key`（body，`str`）: 参数含义需结合同名模型/业务字段理解
    - `user_name`（body，`Optional[str]`）: 用户名
    - `sys_code`（body，`Optional[str]`）: 系统编码/租户编码
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py:407`
- `POST /api/v1/resource/file/read`
  - 作用：处理聊天/OpenAPI v1相关操作
  - 参数：
    - `conv_uid`（body，`str`）: 会话唯一 ID
    - `file_key`（body，`str`）: 参数含义需结合同名模型/业务字段理解
    - `user_name`（body，`Optional[str]`）: 用户名
    - `sys_code`（body，`Optional[str]`）: 系统编码/租户编码
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py:423`
- `POST /api/v1/chat/prepare`
  - 作用：处理聊天/OpenAPI v1相关操作
  - 参数：
    - `dialogue`（body，`ConversationVo`）: 请求体对象，使用模型 `ConversationVo`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py:509`
- `POST /api/v1/chat/completions`
  - 作用：处理聊天/OpenAPI v1相关操作
  - 参数：
    - `dialogue`（body，`ConversationVo`）: 请求体对象，使用模型 `ConversationVo`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py:527`
- `POST /api/v1/chat/topic/terminate`
  - 作用：处理聊天/OpenAPI v1相关操作
  - 参数：
    - `conv_id`（body，`str`）: 参数含义需结合同名模型/业务字段理解
    - `round_index`（body，`int`）: 参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py:645`
- `GET /api/v1/model/types`
  - 作用：处理聊天/OpenAPI v1相关操作
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py:661`
- `GET /api/v1/test`
  - 作用：测试聊天/OpenAPI v1相关操作
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py:680`
- `GET /api/v1/model/supports`
  - 作用：处理聊天/OpenAPI v1相关操作
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py:690`

### 模型服务 API

基础前缀：`/api/v1/worker`, `/api/v2/serve/model`

- `GET /api/v1/worker/health` / `GET /api/v2/serve/model/health`
  - 作用：Health check endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/model/api/endpoints.py:115`
- `GET /api/v1/worker/test_auth` / `GET /api/v2/serve/model/test_auth`
  - 作用：Test auth endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/model/api/endpoints.py:121`
- `GET /api/v1/worker/model-types` / `GET /api/v2/serve/model/model-types`
  - 作用：处理模型服务相关操作
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/model/api/endpoints.py:127`
- `GET /api/v1/worker/models` / `GET /api/v2/serve/model/models`
  - 作用：列表查询模型服务相关操作
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/model/api/endpoints.py:143`
- `POST /api/v1/worker/models/stop` / `POST /api/v2/serve/model/models/stop`
  - 作用：处理模型服务相关操作
  - 参数：
    - `request`（body，`WorkerStartupRequest`）: 参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/model/api/endpoints.py:178`
- `POST /api/v1/worker/models` / `POST /api/v2/serve/model/models`
  - 作用：Create a model.
  - 参数：
    - `request`（body，`WorkerStartupRequest`）: 参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/model/api/endpoints.py:191`
- `POST /api/v1/worker/models/start` / `POST /api/v2/serve/model/models/start`
  - 作用：Start an existing model.
  - 参数：
    - `request`（body，`WorkerStartupRequest`）: 参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/model/api/endpoints.py:209`

### 知识库 API

基础前缀：`/`

- `POST /knowledge/space/add`
  - 作用：新增知识库相关操作
  - 参数：
    - `request`（body，`KnowledgeSpaceRequest`）: 请求体对象，使用模型 `KnowledgeSpaceRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/knowledge/api.py:84`
- `POST /knowledge/space/list`
  - 作用：列表查询知识库相关操作
  - 参数：
    - `request`（body，`KnowledgeSpaceRequest`）: 请求体对象，使用模型 `KnowledgeSpaceRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/knowledge/api.py:96`
- `POST /knowledge/space/delete`
  - 作用：删除知识库相关操作
  - 参数：
    - `request`（body，`KnowledgeSpaceRequest`）: 请求体对象，使用模型 `KnowledgeSpaceRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/knowledge/api.py:109`
- `POST /knowledge/retrieve_strategy_list`
  - 作用：列表查询知识库相关操作
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-app/src/dbgpt_app/knowledge/api.py:130`
- `POST /knowledge/{space_id}/arguments`
  - 作用：处理知识库相关操作
  - 参数：
    - `space_id`（path，`str`）: 知识空间 ID
  - 源码：`packages/dbgpt-app/src/dbgpt_app/knowledge/api.py:141`
- `POST /knowledge/{space_name}/recall_test`
  - 作用：测试知识库相关操作
  - 参数：
    - `space_name`（path，`str`）: 知识空间名称
    - `request`（body，`DocumentRecallTestRequest`）: 请求体对象，使用模型 `DocumentRecallTestRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/knowledge/api.py:153`
- `GET /knowledge/{space_id}/recall_retrievers`
  - 作用：处理知识库相关操作
  - 参数：
    - `space_id`（path，`str`）: 知识空间 ID
  - 源码：`packages/dbgpt-app/src/dbgpt_app/knowledge/api.py:167`
- `POST /knowledge/{space_id}/argument/save`
  - 作用：处理知识库相关操作
  - 参数：
    - `space_id`（path，`str`）: 知识空间 ID
    - `argument_request`（body，`SpaceArgumentRequest`）: 请求体对象，使用模型 `SpaceArgumentRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/knowledge/api.py:207`
- `POST /knowledge/{space_name}/document/add`
  - 作用：新增知识库相关操作
  - 参数：
    - `space_name`（path，`str`）: 知识空间名称
    - `request`（body，`KnowledgeDocumentRequest`）: 请求体对象，使用模型 `KnowledgeDocumentRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/knowledge/api.py:222`
- `POST /knowledge/{space_name}/document/edit`
  - 作用：编辑知识库相关操作
  - 参数：
    - `space_name`（path，`str`）: 知识空间名称
    - `request`（body，`KnowledgeDocumentRequest`）: 请求体对象，使用模型 `KnowledgeDocumentRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/knowledge/api.py:238`
- `GET /knowledge/document/chunkstrategies`
  - 作用：Get chunk strategies
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-app/src/dbgpt_app/knowledge/api.py:259`
- `GET /knowledge/space/config`
  - 作用：Get space config
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-app/src/dbgpt_app/knowledge/api.py:292`
- `POST /knowledge/{space_name}/document/list`
  - 作用：列表查询知识库相关操作
  - 参数：
    - `space_name`（path，`str`）: 知识空间名称
    - `query_request`（body，`DocumentQueryRequest`）: 请求体对象，使用模型 `DocumentQueryRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/knowledge/api.py:345`
- `POST /knowledge/{space_name}/graphvis`
  - 作用：处理知识库相关操作
  - 参数：
    - `space_name`（path，`str`）: 知识空间名称
    - `query_request`（body，`GraphVisRequest`）: 请求体对象，使用模型 `GraphVisRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/knowledge/api.py:357`
- `POST /knowledge/{space_name}/document/delete`
  - 作用：删除知识库相关操作
  - 参数：
    - `space_name`（path，`str`）: 知识空间名称
    - `query_request`（body，`DocumentQueryRequest`）: 请求体对象，使用模型 `DocumentQueryRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/knowledge/api.py:370`
- `POST /knowledge/{space_name}/document/upload`
  - 作用：上传知识库相关操作
  - 参数：
    - `space_name`（path，`str`）: 知识空间名称
    - `doc_name`（form，`str`）: 参数含义需结合同名模型/业务字段理解，默认值 `Form(...)`
    - `doc_type`（form，`str`）: 参数含义需结合同名模型/业务字段理解，默认值 `Form(...)`
    - `doc_file`（file，`UploadFile`）: 参数含义需结合同名模型/业务字段理解，默认值 `File(...)`
  - 源码：`packages/dbgpt-app/src/dbgpt_app/knowledge/api.py:381`
- `POST /knowledge/{space_name}/document/sync`
  - 作用：处理知识库相关操作
  - 参数：
    - `space_name`（path，`str`）: 知识空间名称
    - `request`（body，`DocumentSyncRequest`）: 请求体对象，使用模型 `DocumentSyncRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/knowledge/api.py:451`
- `POST /knowledge/{space_name}/document/sync_batch`
  - 作用：处理知识库相关操作
  - 参数：
    - `space_name`（path，`str`）: 知识空间名称
    - `request`（body，`List[KnowledgeSyncRequest]`）: 请求体对象，使用模型 `KnowledgeSyncRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/knowledge/api.py:480`
- `POST /knowledge/{space_name}/chunk/list`
  - 作用：列表查询知识库相关操作
  - 参数：
    - `space_name`（path，`str`）: 知识空间名称
    - `query_request`（body，`ChunkQueryRequest`）: 请求体对象，使用模型 `ChunkQueryRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/knowledge/api.py:501`
- `POST /knowledge/{space_name}/chunk/edit`
  - 作用：编辑知识库相关操作
  - 参数：
    - `space_name`（path，`str`）: 知识空间名称
    - `edit_request`（body，`ChunkEditRequest`）: 请求体对象，使用模型 `ChunkEditRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/knowledge/api.py:529`
- `POST /knowledge/{vector_name}/query`
  - 作用：查询知识库相关操作
  - 参数：
    - `space_name`（body，`str`）: 知识空间名称
    - `query_request`（body，`KnowledgeQueryRequest`）: 请求体对象，使用模型 `KnowledgeQueryRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/knowledge/api.py:544`
- `POST /knowledge/document/summary`
  - 作用：处理知识库相关操作
  - 参数：
    - `request`（body，`DocumentSummaryRequest`）: 请求体对象，使用模型 `DocumentSummaryRequest`。参数含义需结合同名模型/业务字段理解
  - 源码：`packages/dbgpt-app/src/dbgpt_app/knowledge/api.py:560`

### 示例数据 API

基础前缀：`/api`

- `POST /api/v1/examples/use`
  - 作用：Copy an example file to user's upload directory and return its path.
  - 参数：
    - `example_id`（body，`str`）: 参数含义需结合同名模型/业务字段理解，默认值 `Body(..., embed=True)`
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/examples_api.py:101`

### 聊天 OpenAPI v2 兼容层

基础前缀：`/api`

- `POST /api/v2/chat/completions`
  - 作用：Chat V2 completions
  - 参数：
    - `request`（body，`ChatCompletionRequestBody`）: 请求体对象，使用模型 `ChatCompletionRequestBody`。The chat request.
  - 源码：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v2.py:72`

### 评测/Benchmark API

基础前缀：`/api/v1/evaluate`, `/api/v2/serve/evaluate`

- `GET /api/v1/evaluate/health` / `GET /api/v2/serve/evaluate/health`
  - 作用：Health check endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/evaluate/api/endpoints.py:161`
- `GET /api/v1/evaluate/test_auth` / `GET /api/v2/serve/evaluate/test_auth`
  - 作用：Test auth endpoint
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/evaluate/api/endpoints.py:167`
- `GET /api/v1/evaluate/scenes` / `GET /api/v2/serve/evaluate/scenes`
  - 作用：处理评测/Benchmark相关操作
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/evaluate/api/endpoints.py:173`
- `POST /api/v1/evaluate/evaluation` / `POST /api/v2/serve/evaluate/evaluation`
  - 作用：Evaluate results by the scene
  - 参数：
    - `request`（body，`EvaluateServeRequest`）: 请求体对象，使用模型 `EvaluateServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/evaluate/api/endpoints.py:180`
- `GET /api/v1/evaluate/benchmark/result/{evaluate_code}` / `GET /api/v2/serve/evaluate/benchmark/result/{evaluate_code}`
  - 作用：查看详情评测/Benchmark相关操作
  - 参数：
    - `evaluate_code`（path，`str`）: 评测任务编码
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/evaluate/api/endpoints.py:204`
- `POST /api/v1/evaluate/execute_benchmark_task` / `POST /api/v2/serve/evaluate/execute_benchmark_task`
  - 作用：execute benchmark task
  - 参数：
    - `request`（body，`BenchmarkServeRequest`）: 请求体对象，使用模型 `BenchmarkServeRequest`。The request
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/evaluate/api/endpoints.py:257`
- `GET /api/v1/evaluate/benchmark_task_list` / `GET /api/v2/serve/evaluate/benchmark_task_list`
  - 作用：Query benchmark task list
  - 参数：
    - `state`（query，`Optional[str]`）: benchmark task state，默认值 `Query(default=None, description='benchmark task state')`
    - `page`（query，`Optional[int]`）: current page，默认值 `Query(default=1, description='current page')`
    - `page_size`（query，`Optional[int]`）: page size，默认值 `Query(default=20, description='page size')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/evaluate/api/endpoints.py:280`
- `GET /api/v1/evaluate/benchmark/list_datasets` / `GET /api/v2/serve/evaluate/benchmark/list_datasets`
  - 作用：列表查询评测/Benchmark相关操作
  - 参数：无显式业务参数
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/evaluate/api/endpoints.py:302`
- `GET /api/v1/evaluate/benchmark/dataset/{dataset_id}` / `GET /api/v2/serve/evaluate/benchmark/dataset/{dataset_id}`
  - 作用：列表查询评测/Benchmark相关操作
  - 参数：
    - `dataset_id`（path，`str`）: 数据集 ID
    - `limit`（query，`int`）: 参数含义需结合同名模型/业务字段理解，默认值 `200`
    - `offset`（query，`int`）: 参数含义需结合同名模型/业务字段理解，默认值 `0`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/evaluate/api/endpoints.py:310`
- `GET /api/v1/evaluate/benchmark/dataset/{dataset_id}/{table}/rows` / `GET /api/v2/serve/evaluate/benchmark/dataset/{dataset_id}/{table}/rows`
  - 作用：处理评测/Benchmark相关操作
  - 参数：
    - `dataset_id`（path，`str`）: 数据集 ID
    - `table`（path，`str`）: 数据表名
    - `limit`（query，`int`）: 参数含义需结合同名模型/业务字段理解，默认值 `10`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/evaluate/api/endpoints.py:333`
- `GET /api/v1/evaluate/benchmark_result_download` / `GET /api/v2/serve/evaluate/benchmark_result_download`
  - 作用：Download benchmark result file
  - 参数：
    - `evaluate_code`（query，`Optional[str]`）: evaluate code，默认值 `Query(default=None, description='evaluate code')`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/evaluate/api/endpoints.py:347`
- `GET /api/v1/evaluate/benchmark/list_results` / `GET /api/v2/serve/evaluate/benchmark/list_results`
  - 作用：列表查询评测/Benchmark相关操作
  - 参数：
    - `limit`（query，`int`）: 参数含义需结合同名模型/业务字段理解，默认值 `50`
    - `offset`（query，`int`）: 参数含义需结合同名模型/业务字段理解，默认值 `0`
  - 源码：`packages/dbgpt-serve/src/dbgpt_serve/evaluate/api/endpoints.py:397`

## 请求体模型字段

### `ChunkEditRequest`

定义位置：`packages/dbgpt-app/src/dbgpt_app/knowledge/request/request.py`
类说明：id: id
- 字段：
  - `chunk_id`（`Optional[int]`）: 参数含义需结合同名模型/业务字段理解
  - `content`（`Optional[str]`）: 正文内容
  - `label`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `questions`（`Optional[List[str]]`）: 参数含义需结合同名模型/业务字段理解

### `ChunkQueryRequest`

定义位置：`packages/dbgpt-app/src/dbgpt_app/knowledge/request/request.py`
类说明：id: id
- 字段：
  - `id`（`Optional[int]`）: 主键 ID
  - `document_id`（`Optional[int]`）: 文档 ID
  - `doc_name`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `doc_type`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `content`（`Optional[str]`）: 正文内容
  - `page`（`int`）: 分页页码，默认值 `1`
  - `page_size`（`int`）: 每页条数，默认值 `20`

### `DocumentQueryRequest`

定义位置：`packages/dbgpt-app/src/dbgpt_app/knowledge/request/request.py`
类说明：doc_name: doc path
- 字段：
  - `doc_name`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `doc_ids`（`Optional[List]`）: 参数含义需结合同名模型/业务字段理解
  - `doc_type`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `status`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `page`（`int`）: 分页页码，默认值 `1`
  - `page_size`（`int`）: 每页条数，默认值 `20`

### `DocumentRecallTestRequest`

定义位置：`packages/dbgpt-app/src/dbgpt_app/knowledge/request/request.py`
- 字段：
  - `question`（`Optional[str]`）: 问题文本
  - `recall_top_k`（`Optional[int]`）: 参数含义需结合同名模型/业务字段理解，默认值 `1`
  - `recall_retrievers`（`Optional[List[str]]`）: 参数含义需结合同名模型/业务字段理解
  - `recall_score_threshold`（`Optional[float]`）: 参数含义需结合同名模型/业务字段理解，默认值 `-100`

### `DocumentSummaryRequest`

定义位置：`packages/dbgpt-app/src/dbgpt_app/knowledge/request/request.py`
类说明：Sync request
- 字段：
  - `doc_id`（`int`）: 参数含义需结合同名模型/业务字段理解
  - `model_name`（`str`）: 参数含义需结合同名模型/业务字段理解
  - `conv_uid`（`str`）: 会话唯一 ID

### `DocumentSyncRequest`

定义位置：`packages/dbgpt-app/src/dbgpt_app/knowledge/request/request.py`
类说明：Sync request
- 字段：
  - `doc_ids`（`List`）: 参数含义需结合同名模型/业务字段理解
  - `model_name`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `pre_separator`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `separators`（`Optional[List[str]]`）: 参数含义需结合同名模型/业务字段理解
  - `chunk_size`（`Optional[int]`）: 参数含义需结合同名模型/业务字段理解
  - `chunk_overlap`（`Optional[int]`）: 参数含义需结合同名模型/业务字段理解

### `GraphVisRequest`

定义位置：`packages/dbgpt-app/src/dbgpt_app/knowledge/request/request.py`
- 字段：
  - `limit`（`int`）: 参数含义需结合同名模型/业务字段理解，默认值 `100`

### `KnowledgeDocumentRequest`

定义位置：`packages/dbgpt-app/src/dbgpt_app/knowledge/request/request.py`
类说明：doc_name: doc path
- 字段：
  - `doc_name`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `doc_id`（`Optional[int]`）: 参数含义需结合同名模型/业务字段理解
  - `doc_type`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `doc_token`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `content`（`Optional[str]`）: 正文内容
  - `source`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `labels`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `questions`（`Optional[List[str]]`）: 参数含义需结合同名模型/业务字段理解

### `KnowledgeQueryRequest`

定义位置：`packages/dbgpt-app/src/dbgpt_app/knowledge/request/request.py`
类说明：query: knowledge query
- 字段：
  - `query`（`str`）: 查询条件
  - `space`（`str`）: 参数含义需结合同名模型/业务字段理解
  - `top_k`（`int`）: 参数含义需结合同名模型/业务字段理解

### `KnowledgeSpaceRequest`

定义位置：`packages/dbgpt-app/src/dbgpt_app/knowledge/request/request.py`
类说明：name: knowledge space name
- 字段：
  - `id`（`Optional[int]`）: 主键 ID
  - `name`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `vector_type`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `domain_type`（`str`）: 参数含义需结合同名模型/业务字段理解，默认值 `'Normal'`
  - `desc`（`str`）: 参数含义需结合同名模型/业务字段理解
  - `owner`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `space_id`（`Optional[Union[int, str]]`）: 知识空间 ID

### `SpaceArgumentRequest`

定义位置：`packages/dbgpt-app/src/dbgpt_app/knowledge/request/request.py`
类说明：argument: argument
- 字段：
  - `argument`（`str`）: 参数含义需结合同名模型/业务字段理解

### `ShareCreateRequest`

定义位置：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/agentic_data_api.py`
类说明：Request body for creating a share link.
- 字段：
  - `conv_uid`（`str`）: 会话唯一 ID

### `FeedBackBody`

定义位置：`packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/feedback/feed_back_model.py`
类说明：conv_uid: conversation id
- 字段：
  - `conv_uid`（`Optional[str]`）: 会话唯一 ID
  - `conv_index`（`Optional[int]`）: 参数含义需结合同名模型/业务字段理解
  - `question`（`Optional[str]`）: 问题文本
  - `score`（`Optional[int]`）: 参数含义需结合同名模型/业务字段理解
  - `ques_type`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `user_name`（`Optional[str]`）: 用户名
  - `messages`（`Optional[str]`）: 消息列表
  - `knowledge_space`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解

### `ConversationVo`

定义位置：`packages/dbgpt-app/src/dbgpt_app/openapi/api_view_model.py`
- 字段：
  - `conv_uid`（`str`）: 会话唯一 ID，默认值 `''`
  - `user_input`（`Union[str, ChatCompletionUserMessageParam]`）: User input messages.，默认值 `Field(default='', description='User input messages.')`
  - `user_name`（`Optional[str]`）: user name，默认值 `Field(None, description='user name')`
  - `chat_mode`（`Optional[str]`）: 聊天模式，默认值 `''`
  - `app_code`（`Optional[str]`）: 应用编码，默认值 `''`
  - `temperature`（`Optional[float]`）: 参数含义需结合同名模型/业务字段理解，默认值 `0.5`
  - `max_new_tokens`（`Optional[int]`）: 参数含义需结合同名模型/业务字段理解，默认值 `4000`
  - `select_param`（`Optional[Any]`）: chat scene select param，默认值 `Field(None, description='chat scene select param')`
  - `model_name`（`Optional[str]`）: llm model name，默认值 `Field(None, description='llm model name')`
  - `incremental`（`bool`）: 参数含义需结合同名模型/业务字段理解，默认值 `False`
  - `sys_code`（`Optional[str]`）: System code，默认值 `Field(None, description='System code')`
  - `prompt_code`（`Optional[str]`）: prompt code，默认值 `Field(None, description='prompt code')`
  - `ext_info`（`Optional[dict]`）: 参数含义需结合同名模型/业务字段理解，默认值 `{}`

### `ChatChartEditContext`

定义位置：`packages/dbgpt-app/src/dbgpt_app/openapi/editor_view_model.py`
- 字段：
  - `conv_uid`（`str`）: 会话唯一 ID
  - `chart_title`（`str`）: 参数含义需结合同名模型/业务字段理解
  - `db_name`（`str`）: 数据库名称
  - `old_sql`（`str`）: 参数含义需结合同名模型/业务字段理解
  - `new_chart_type`（`str`）: 参数含义需结合同名模型/业务字段理解
  - `new_sql`（`str`）: 参数含义需结合同名模型/业务字段理解
  - `new_comment`（`str`）: 参数含义需结合同名模型/业务字段理解
  - `gmt_create`（`int`）: 参数含义需结合同名模型/业务字段理解

### `ChatSqlEditContext`

定义位置：`packages/dbgpt-app/src/dbgpt_app/openapi/editor_view_model.py`
- 字段：
  - `conv_uid`（`str`）: 会话唯一 ID
  - `db_name`（`str`）: 数据库名称
  - `conv_round`（`int`）: 参数含义需结合同名模型/业务字段理解
  - `old_sql`（`str`）: 参数含义需结合同名模型/业务字段理解
  - `old_speak`（`str`）: 参数含义需结合同名模型/业务字段理解
  - `gmt_create`（`int`）: 参数含义需结合同名模型/业务字段理解，默认值 `0`
  - `new_sql`（`str`）: 参数含义需结合同名模型/业务字段理解
  - `new_speak`（`str`）: 参数含义需结合同名模型/业务字段理解，默认值 `''`

### `ChatCompletionRequestBody`

定义位置：`packages/dbgpt-client/src/dbgpt_client/schema.py`
类说明：ChatCompletion LLM http request body.
- 字段：
  - `model`（`str`）: Model name，默认值 `Field(..., description='Model name')`
  - `messages`（`Union[str, List[ChatCompletionMessageParam]]`）: User input messages，默认值 `Field(..., description='User input messages')`
  - `temperature`（`Optional[float]`）: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic.，默认值 `Field(0.7, description='What sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic.')`
  - `top_p`（`Optional[float]`）: Top p，默认值 `Field(1.0, description='Top p')`
  - `top_k`（`Optional[int]`）: Top k，默认值 `Field(-1, description='Top k')`
  - `n`（`Optional[int]`）: Number of completions，默认值 `Field(1, description='Number of completions')`
  - `max_tokens`（`Optional[int]`）: Max tokens，默认值 `Field(None, description='Max tokens')`
  - `stop`（`Optional[Union[str, List[str]]]`）: Stop，默认值 `Field(None, description='Stop')`
  - `stream`（`Optional[bool]`）: Stream，默认值 `Field(False, description='Stream')`
  - `user`（`Optional[str]`）: User，默认值 `Field(None, description='User')`
  - `repetition_penalty`（`Optional[float]`）: Repetition penalty，默认值 `Field(1.0, description='Repetition penalty')`
  - `frequency_penalty`（`Optional[float]`）: Frequency penalty，默认值 `Field(0.0, description='Frequency penalty')`
  - `presence_penalty`（`Optional[float]`）: Presence penalty，默认值 `Field(0.0, description='Presence penalty')`
  - `max_new_tokens`（`Optional[int]`）: The maximum number of tokens that can be generated in the chat completion.，默认值 `Field(default=None, description='The maximum number of tokens that can be generated in the chat completion.', deprecated="'max_new_tokens' is deprecated. Use 'max_tokens' instead.")`
  - `conv_uid`（`Optional[str]`）: The conversation id of the model inference，默认值 `Field(default=None, description='The conversation id of the model inference')`
  - `span_id`（`Optional[str]`）: The span id of the model inference，默认值 `Field(default=None, description='The span id of the model inference')`
  - `chat_mode`（`Optional[str]`）: The chat mode，默认值 `Field(default='chat_normal', description='The chat mode', examples=['chat_awel_flow', 'chat_normal'])`
  - `chat_param`（`Optional[str]`）: The chat param of chat mode，默认值 `Field(default=None, description='The chat param of chat mode')`
  - `user_name`（`Optional[str]`）: The user name of the model inference，默认值 `Field(default=None, description='The user name of the model inference')`
  - `sys_code`（`Optional[str]`）: The system code of the model inference，默认值 `Field(default=None, description='The system code of the model inference')`
  - `incremental`（`bool`）: Used to control whether the content is returned incrementally or in full each time. If this parameter is not provided, the default is full return.，默认值 `Field(default=True, description='Used to control whether the content is returned incrementally or in full each time. If this parameter is not provided, the default is full return.')`
  - `enable_vis`（`bool`）: response content whether to output vis label，默认值 `Field(default=True, description='response content whether to output vis label')`

### `RecommendQuestion`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/agent/app/recommend_question/recommend_question.py`
- 字段：
  - `id`（`Optional[int]`）: id，默认值 `Field(None, description='id')`
  - `app_code`（`Optional[str]`）: The unique identify of app，默认值 `Field(None, description='The unique identify of app')`
  - `question`（`Optional[str]`）: The question you may ask，默认值 `Field(None, description='The question you may ask')`
  - `user_code`（`Optional[str]`）: The user code，默认值 `Field(None, description='The user code')`
  - `sys_code`（`Optional[str]`）: The system code，默认值 `Field(None, description='The system code')`
  - `gmt_create`（`datetime`）: 参数含义需结合同名模型/业务字段理解，默认值 `datetime.now()`
  - `gmt_modified`（`datetime`）: 参数含义需结合同名模型/业务字段理解，默认值 `datetime.now()`
  - `params`（`Optional[dict]`）: The params of app，默认值 `Field(default={}, description='The params of app')`
  - `valid`（`Optional[Union[str, bool]]`）: is the question valid to display, default is true，默认值 `Field(default=None, description='is the question valid to display, default is true')`
  - `chat_mode`（`Optional[str]`）: is the question valid to display, default is true，默认值 `Field(default=None, description='is the question valid to display, default is true')`
  - `is_hot_question`（`Optional[str]`）: is hot question.，默认值 `Field(default=None, description='is hot question.')`

### `ServeRequest`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/agent/chat/api/schemas.py`
类说明：Agent/chat request model
- 字段：

### `GptsApp`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/agent/db/gpts_app.py`
- 字段：
  - `app_code`（`Optional[str]`）: 应用编码
  - `app_name`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `app_describe`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `team_mode`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `language`（`Optional[str]`）: 语言
  - `team_context`（`Optional[Union[str, AWELTeamContext, NativeTeamContext]]`）: 参数含义需结合同名模型/业务字段理解
  - `user_code`（`Optional[str]`）: 用户编码
  - `sys_code`（`Optional[str]`）: 系统编码/租户编码
  - `is_collected`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `icon`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `created_at`（`datetime`）: 参数含义需结合同名模型/业务字段理解，默认值 `datetime.now()`
  - `updated_at`（`datetime`）: 参数含义需结合同名模型/业务字段理解，默认值 `datetime.now()`
  - `details`（`List[GptsAppDetail]`）: 参数含义需结合同名模型/业务字段理解，默认值 `[]`
  - `published`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `user_name`（`Optional[str]`）: 用户名
  - `user_icon`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `hot_value`（`Optional[int]`）: 参数含义需结合同名模型/业务字段理解
  - `param_need`（`Optional[List[dict]]`）: 参数含义需结合同名模型/业务字段理解，默认值 `[]`
  - `owner_name`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `owner_avatar_url`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `recommend_questions`（`Optional[List[RecommendQuestion]]`）: 参数含义需结合同名模型/业务字段理解，默认值 `[]`
  - `admins`（`List[str]`）: 参数含义需结合同名模型/业务字段理解，默认值 `Field(default_factory=list)`
  - `keep_start_rounds`（`int`）: 参数含义需结合同名模型/业务字段理解，默认值 `0`
  - `keep_end_rounds`（`int`）: 参数含义需结合同名模型/业务字段理解，默认值 `0`

### `GptsAppQuery`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/agent/db/gpts_app.py`
- 字段：
  - `app_code`（`Optional[str]`）: 应用编码
  - `app_name`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `app_describe`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `team_mode`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `language`（`Optional[str]`）: 语言
  - `team_context`（`Optional[Union[str, AWELTeamContext, NativeTeamContext]]`）: 参数含义需结合同名模型/业务字段理解
  - `user_code`（`Optional[str]`）: 用户编码
  - `sys_code`（`Optional[str]`）: 系统编码/租户编码
  - `is_collected`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `icon`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `created_at`（`datetime`）: 参数含义需结合同名模型/业务字段理解，默认值 `datetime.now()`
  - `updated_at`（`datetime`）: 参数含义需结合同名模型/业务字段理解，默认值 `datetime.now()`
  - `details`（`List[GptsAppDetail]`）: 参数含义需结合同名模型/业务字段理解，默认值 `[]`
  - `published`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `user_name`（`Optional[str]`）: 用户名
  - `user_icon`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `hot_value`（`Optional[int]`）: 参数含义需结合同名模型/业务字段理解
  - `param_need`（`Optional[List[dict]]`）: 参数含义需结合同名模型/业务字段理解，默认值 `[]`
  - `owner_name`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `owner_avatar_url`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `recommend_questions`（`Optional[List[RecommendQuestion]]`）: 参数含义需结合同名模型/业务字段理解，默认值 `[]`
  - `admins`（`List[str]`）: 参数含义需结合同名模型/业务字段理解，默认值 `Field(default_factory=list)`
  - `keep_start_rounds`（`int`）: 参数含义需结合同名模型/业务字段理解，默认值 `0`
  - `keep_end_rounds`（`int`）: 参数含义需结合同名模型/业务字段理解，默认值 `0`
  - `page_size`（`int`）: 每页条数，默认值 `100`
  - `page`（`int`）: 分页页码，默认值 `1`
  - `is_recent_used`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `ignore_user`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解
  - `app_codes`（`Optional[List[str]]`）: 参数含义需结合同名模型/业务字段理解，默认值 `[]`
  - `hot_map`（`Optional[Dict[str, int]]`）: 参数含义需结合同名模型/业务字段理解，默认值 `{}`
  - `need_owner_info`（`Optional[str]`）: 参数含义需结合同名模型/业务字段理解，默认值 `'true'`

### `PagenationFilter`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/agent/model.py`
- 字段：
  - `page_index`（`int`）: 参数含义需结合同名模型/业务字段理解，默认值 `1`
  - `page_size`（`int`）: 每页条数，默认值 `20`
  - `filter`（`T`）: 参数含义需结合同名模型/业务字段理解

### `PluginHubParam`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/agent/model.py`
- 字段：
  - `channel`（`Optional[str]`）: Plugin storage channel，默认值 `Field('git', description='Plugin storage channel')`
  - `url`（`Optional[str]`）: Plugin storage url，默认值 `Field('https://github.com/eosphoros-ai/DB-GPT-Plugins.git', description='Plugin storage url')`
  - `branch`（`Optional[str]`）: github download branch，默认值 `Field('main', description='github download branch', nullable=True)`
  - `authorization`（`Optional[str]`）: github download authorization，默认值 `Field(None, description='github download authorization', nullable=True)`

### `ServeRequest`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/conversation/api/schemas.py`
类说明：Conversation request model
- 字段：
  - `chat_mode`（`str`）: The chat mode.，默认值 `Field(default=None, description='The chat mode.', examples=['chat_normal'])`
  - `conv_uid`（`Optional[str]`）: The conversation uid.，默认值 `Field(default=None, description='The conversation uid.', examples=['5e7100bc-9017-11ee-9876-8fe019728d79'])`
  - `user_name`（`Optional[str]`）: The user name.，默认值 `Field(default=None, description='The user name.', examples=['zhangsan'])`
  - `sys_code`（`Optional[str]`）: The system code.，默认值 `Field(default=None, description='The system code.', examples=['dbgpt'])`

### `DatasourceCreateRequest`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/datasource/api/schemas.py`
类说明：Request model for datasource connection
- 字段：
  - `type`（`str`）: The type of datasource (e.g., 'mysql', 'tugraph')，默认值 `Field(..., description="The type of datasource (e.g., 'mysql', 'tugraph')")`
  - `params`（`Dict[str, Any]`）: Dynamic parameters for the datasource connection.，默认值 `Field(..., description='Dynamic parameters for the datasource connection.')`
  - `description`（`Optional[str]`）: Optional description of the datasource.，默认值 `Field(None, description='Optional description of the datasource.')`
  - `id`（`Optional[int]`）: The datasource id，默认值 `Field(None, description='The datasource id')`

### `DatasourceServeRequest`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/datasource/api/schemas.py`
类说明：name: knowledge space name
- 字段：
  - `id`（`Optional[int]`）: The datasource id，默认值 `Field(None, description='The datasource id')`
  - `db_type`（`str`）: Database type, e.g. sqlite, mysql, etc.，默认值 `Field(..., description='Database type, e.g. sqlite, mysql, etc.')`
  - `db_name`（`str`）: Database name.，默认值 `Field(..., description='Database name.')`
  - `db_path`（`Optional[str]`）: File path for file-based database.，默认值 `Field('', description='File path for file-based database.')`
  - `db_host`（`Optional[str]`）: Database host.，默认值 `Field('', description='Database host.')`
  - `db_port`（`Optional[int]`）: Database port.，默认值 `Field(0, description='Database port.')`
  - `db_user`（`Optional[str]`）: Database user.，默认值 `Field('', description='Database user.')`
  - `db_pwd`（`Optional[str]`）: Database password.，默认值 `Field('', description='Database password.')`
  - `comment`（`Optional[str]`）: Comment for the database.，默认值 `Field('', description='Comment for the database.')`
  - `ext_config`（`Optional[Dict[str, Any]]`）: Extra configuration for the datasource.，默认值 `Field(None, description='Extra configuration for the datasource.')`

### `DBConfig`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/datasource/manages/db_conn_info.py`
类说明：Database connection configuration.
- 字段：
  - `db_type`（`str`）: Database type, e.g. sqlite, mysql, etc.，默认值 `Field(..., description='Database type, e.g. sqlite, mysql, etc.')`
  - `db_name`（`str`）: Database name.，默认值 `Field(..., description='Database name.')`
  - `file_path`（`str`）: File path for file-based database.，默认值 `Field('', description='File path for file-based database.')`
  - `db_host`（`str`）: Database host.，默认值 `Field('', description='Database host.')`
  - `db_port`（`int`）: Database port.，默认值 `Field(0, description='Database port.')`
  - `db_user`（`str`）: Database user.，默认值 `Field('', description='Database user.')`
  - `db_pwd`（`str`）: Database password.，默认值 `Field('', description='Database password.')`
  - `comment`（`str`）: Comment for the database.，默认值 `Field('', description='Comment for the database.')`

### `ServeRequest`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/dbgpts/hub/api/schemas.py`
类说明：DbgptsHub request model
- 字段：
  - `id`（`Optional[int]`）: id，默认值 `Field(None, description='id')`
  - `name`（`Optional[str]`）: Dbgpts name，默认值 `Field(None, description='Dbgpts name')`
  - `type`（`Optional[str]`）: Dbgpts type，默认值 `Field(None, description='Dbgpts type')`
  - `version`（`Optional[str]`）: Dbgpts version，默认值 `Field(None, description='Dbgpts version')`
  - `description`（`Optional[str]`）: Dbgpts description，默认值 `Field(None, description='Dbgpts description')`
  - `author`（`Optional[str]`）: Dbgpts author，默认值 `Field(None, description='Dbgpts author')`
  - `email`（`Optional[str]`）: Dbgpts email，默认值 `Field(None, description='Dbgpts email')`
  - `storage_channel`（`Optional[str]`）: Dbgpts storage channel，默认值 `Field(None, description='Dbgpts storage channel')`
  - `storage_url`（`Optional[str]`）: Dbgpts storage url，默认值 `Field(None, description='Dbgpts storage url')`
  - `download_param`（`Optional[str]`）: Dbgpts download param，默认值 `Field(None, description='Dbgpts download param')`
  - `installed`（`Optional[int]`）: Dbgpts installed，默认值 `Field(None, description='Dbgpts installed')`

### `ServeRequest`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/dbgpts/my/api/schemas.py`
类说明：DbgptsMy request model
- 字段：
  - `id`（`Optional[int]`）: id，默认值 `Field(None, description='id')`
  - `user_name`（`Optional[str]`）: My gpts user name，默认值 `Field(None, description='My gpts user name')`
  - `sys_code`（`Optional[str]`）: My gpts sys code，默认值 `Field(None, description='My gpts sys code')`
  - `name`（`Optional[str]`）: My gpts name，默认值 `Field(None, description='My gpts name')`
  - `file_name`（`Optional[str]`）: My gpts file name，默认值 `Field(None, description='My gpts file name')`
  - `type`（`Optional[str]`）: My gpts type，默认值 `Field(None, description='My gpts type')`
  - `version`（`Optional[str]`）: My gpts version，默认值 `Field(None, description='My gpts version')`
  - `use_count`（`Optional[int]`）: My gpts use count，默认值 `Field(None, description='My gpts use count')`
  - `succ_count`（`Optional[int]`）: My gpts succ count，默认值 `Field(None, description='My gpts succ count')`

### `BenchmarkServeRequest`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/evaluate/api/schemas.py`
- 字段：
  - `evaluate_code`（`Optional[str]`）: evaluation code，默认值 `Field(None, description='evaluation code')`
  - `scene_key`（`Optional[str]`）: evaluation scene key，默认值 `Field(None, description='evaluation scene key')`
  - `scene_value`（`Optional[str]`）: evaluation scene value，默认值 `Field(None, description='evaluation scene value')`
  - `datasets_name`（`Optional[str]`）: evaluation datasets name，默认值 `Field(None, description='evaluation datasets name')`
  - `input_file_path`（`Optional[str]`）: input benchmark file path，默认值 `Field(None, description='input benchmark file path')`
  - `output_file_path`（`Optional[str]`）: output result file path，默认值 `Field(None, description='output result file path')`
  - `model_list`（`Optional[List[str]]`）: execute benchmark model name list，默认值 `Field(None, description='execute benchmark model name list')`
  - `context`（`Optional[dict]`）: The context of the evaluate，默认值 `Field(None, description='The context of the evaluate')`
  - `user_name`（`Optional[str]`）: user name，默认值 `Field(None, description='user name')`
  - `user_id`（`Optional[str]`）: user id，默认值 `Field(None, description='user id')`
  - `sys_code`（`Optional[str]`）: system code，默认值 `Field(None, description='system code')`
  - `parallel_num`（`Optional[int]`）: task parallel num，默认值 `Field(None, description='task parallel num')`
  - `state`（`Optional[str]`）: evaluation state，默认值 `Field(None, description='evaluation state')`
  - `temperature`（`Optional[float]`）: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic.，默认值 `Field(0.7, description='What sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic.')`
  - `max_tokens`（`Optional[int]`）: Max tokens，默认值 `Field(None, description='Max tokens')`
  - `log_info`（`Optional[str]`）: evaluation task error message，默认值 `Field(None, description='evaluation task error message')`
  - `gmt_create`（`Optional[str]`）: create time，默认值 `Field(None, description='create time')`
  - `gmt_modified`（`Optional[str]`）: modified time，默认值 `Field(None, description='modified time')`
  - `evaluation_env`（`Optional[str]`）: benchmark dataset env, e.g. DEV, TEST，默认值 `Field(None, description='benchmark dataset env, e.g. DEV, TEST')`
  - `benchmark_type`（`Optional[str]`）: execute benchmark type, llm or agent，默认值 `Field(None, description='execute benchmark type, llm or agent')`
  - `api_url`（`Optional[str]`）: api url，默认值 `Field(None, description='api url')`
  - `http_method`（`Optional[str]`）: http method，默认值 `Field(None, description='http method')`
  - `headers`（`Optional[dict]`）: http headers，默认值 `Field(None, description='http headers')`
  - `parse_strategy`（`Optional[str]`）: agent response parse strategy，默认值 `Field(None, description='agent response parse strategy')`
  - `response_mapping`（`Optional[dict]`）: agent  response extract result mapping，默认值 `Field(None, description='agent  response extract result mapping')`

### `EvaluateServeRequest`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/evaluate/api/schemas.py`
- 字段：
  - `evaluate_code`（`Optional[str]`）: evaluation code，默认值 `Field(None, description='evaluation code')`
  - `scene_key`（`Optional[str]`）: evaluation scene key，默认值 `Field(None, description='evaluation scene key')`
  - `scene_value`（`Optional[str]`）: evaluation scene value，默认值 `Field(None, description='evaluation scene value')`
  - `datasets_name`（`Optional[str]`）: evaluation datasets name，默认值 `Field(None, description='evaluation datasets name')`
  - `datasets`（`Optional[Union[str, List[dict]]]`）: datasets，默认值 `Field(None, description='datasets')`
  - `evaluate_metrics`（`Optional[List[str]]`）: evaluation metrics，默认值 `Field(None, description='evaluation metrics')`
  - `context`（`Optional[dict]`）: The context of the evaluate，默认值 `Field(None, description='The context of the evaluate')`
  - `user_name`（`Optional[str]`）: user name，默认值 `Field(None, description='user name')`
  - `user_id`（`Optional[str]`）: user id，默认值 `Field(None, description='user id')`
  - `sys_code`（`Optional[str]`）: system code，默认值 `Field(None, description='system code')`
  - `parallel_num`（`Optional[int]`）: system code，默认值 `Field(None, description='system code')`
  - `state`（`Optional[str]`）: evaluation state，默认值 `Field(None, description='evaluation state')`
  - `result`（`Optional[str]`）: evaluation result，默认值 `Field(None, description='evaluation result')`
  - `storage_type`（`Optional[str]`）: datasets storage type，默认值 `Field(None, comment='datasets storage type')`
  - `average_score`（`Optional[str]`）: evaluation average score，默认值 `Field(None, description='evaluation average score')`
  - `log_info`（`Optional[str]`）: evaluation log_info，默认值 `Field(None, description='evaluation log_info')`
  - `gmt_create`（`Optional[str]`）: create time，默认值 `Field(None, description='create time')`
  - `gmt_modified`（`Optional[str]`）: create time，默认值 `Field(None, description='create time')`

### `ServeRequest`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/feedback/api/schemas.py`
类说明：Feedback request model
- 字段：
  - `id`（`Optional[int]`）: Primary Key，默认值 `Field(None, description='Primary Key')`
  - `gmt_created`（`Optional[str]`）: Creation time，默认值 `Field(None, description='Creation time')`
  - `gmt_modified`（`Optional[str]`）: Modification time，默认值 `Field(None, description='Modification time')`
  - `user_code`（`Optional[str]`）: User ID，默认值 `Field(None, description='User ID')`
  - `user_name`（`Optional[str]`）: User Name，默认值 `Field(None, description='User Name')`
  - `conv_uid`（`Optional[str]`）: Conversation ID，默认值 `Field(None, description='Conversation ID')`
  - `message_id`（`Optional[str]`）: Message ID, round_index for table chat_history_message，默认值 `Field(None, description='Message ID, round_index for table chat_history_message')`
  - `score`（`Optional[float]`）: Rating of answers，默认值 `Field(None, description='Rating of answers')`
  - `question`（`Optional[str]`）: User question，默认值 `Field(None, description='User question')`
  - `ques_type`（`Optional[str]`）: User question type，默认值 `Field(None, description='User question type')`
  - `knowledge_space`（`Optional[str]`）: Use resource，默认值 `Field(None, description='Use resource')`
  - `feedback_type`（`Optional[str]`）: Feedback type like or unlike，默认值 `Field(None, description='Feedback type like or unlike')`
  - `reason_type`（`Optional[str]`）: Feedback reason category，默认值 `Field(None, description='Feedback reason category')`
  - `remark`（`Optional[str]`）: Remarks，默认值 `Field(None, description='Remarks')`
  - `reason_types`（`Optional[List[str]]`）: Feedback reason categories，默认值 `Field(default=[], description='Feedback reason categories')`
  - `reason`（`Optional[List[Dict]]`）: Feedback reason category，默认值 `Field(default=[], description='Feedback reason category')`

### `FileMetadataBatchRequest`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/file/api/schemas.py`
类说明：File metadata batch request model
- 字段：
  - `uris`（`Optional[List[str]]`）: The URIs of the files，默认值 `Field(None, title='The URIs of the files')`
  - `bucket_file_pairs`（`Optional[List[_BucketFilePair]]`）: The bucket file pairs，默认值 `Field(None, title='The bucket file pairs')`

### `FlowDebugRequest`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/flow/api/schemas.py`
类说明：Flow response model
- 字段：
  - `flow`（`ServeRequest`）: The flow to debug，默认值 `Field(..., title='The flow to debug', description='The flow to debug')`
  - `request`（`Union[CommonLLMHttpRequestBody, Dict[str, Any]]`）: The request to debug，默认值 `Field(..., title='The request to debug', description='The request to debug')`
  - `variables`（`Optional[Dict[str, Any]]`）: The variables to debug，默认值 `Field(None, title='The variables to debug', description='The variables to debug')`
  - `user_name`（`Optional[str]`）: User name，默认值 `Field(None, description='User name')`
  - `sys_code`（`Optional[str]`）: System code，默认值 `Field(None, description='System code')`

### `RefreshNodeRequest`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/flow/api/schemas.py`
类说明：Flow response model
- 字段：
  - `id`（`str`）: The id of the node，默认值 `Field(..., title='The id of the node', description='The id of the node to refresh', examples=['operator_llm_operator___$$___llm___$$___v1'])`
  - `flow_type`（`Literal['operator', 'resource']`）: The type of the node，默认值 `Field('operator', title='The type of the node', description='The type of the node to refresh', examples=['operator', 'resource'])`
  - `type_name`（`str`）: The type of the node，默认值 `Field(..., title='The type of the node', description='The type of the node to refresh', examples=['LLMOperator'])`
  - `type_cls`（`str`）: The class of the node，默认值 `Field(..., title='The class of the node', description='The class of the node to refresh', examples=['dbgpt.core.operator.llm.LLMOperator'])`
  - `refresh`（`List[RefreshOptionRequest]`）: The refresh options，默认值 `Field(..., title='The refresh options', description='The refresh options')`

### `ServeRequest`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/libro/api/schemas.py`
类说明：Libro request model
- 字段：

### `PromptDebugInput`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/prompt/api/schemas.py`
- 字段：
  - `chat_scene`（`Optional[str]`）: The chat scene, e.g. chat_with_db_execute, chat_excel, chat_with_db_qa.，默认值 `Field(None, description='The chat scene, e.g. chat_with_db_execute, chat_excel, chat_with_db_qa.', examples=['chat_with_db_execute', 'chat_excel', 'chat_with_db_qa'])`
  - `sub_chat_scene`（`Optional[str]`）: The sub chat scene.，默认值 `Field(None, description='The sub chat scene.', examples=['sub_scene_1', 'sub_scene_2', 'sub_scene_3'])`
  - `prompt_code`（`Optional[str]`）: The prompt code.，默认值 `Field(None, description='The prompt code.', examples=['test123', 'test456'])`
  - `prompt_type`（`Optional[str]`）: The prompt type, either common or private.，默认值 `Field(None, description='The prompt type, either common or private.', examples=['common', 'private'])`
  - `prompt_name`（`Optional[str]`）: The prompt name.，默认值 `Field(None, description='The prompt name.', examples=['code_assistant', 'joker', 'data_analysis_expert'])`
  - `content`（`Optional[str]`）: The prompt content.，默认值 `Field(None, description='The prompt content.', examples=['Write a qsort function in python', 'Tell me a joke about AI', 'You are a data analysis expert.'])`
  - `prompt_desc`（`Optional[str]`）: The prompt description.，默认值 `Field(None, description='The prompt description.', examples=['This is a prompt for code assistant.', 'This is a prompt for joker.', 'This is a prompt for data analysis expert.'])`
  - `response_schema`（`Optional[str]`）: The prompt response schema.，默认值 `Field(None, description='The prompt response schema.', examples=['None', '{"xx": "123"}'])`
  - `input_variables`（`Optional[str]`）: The prompt variables.，默认值 `Field(None, description='The prompt variables.', examples=['display_type', 'resources'])`
  - `model`（`Optional[str]`）: The prompt can use model.，默认值 `Field(None, description='The prompt can use model.', examples=['vicuna13b', 'chatgpt'])`
  - `prompt_language`（`Optional[str]`）: The prompt language.，默认值 `Field(None, description='The prompt language.', examples=['en', 'zh'])`
  - `user_code`（`Optional[str]`）: The user id.，默认值 `Field(None, description='The user id.', examples=[''])`
  - `user_name`（`Optional[str]`）: The user name.，默认值 `Field(None, description='The user name.', examples=['zhangsan', 'lisi', 'wangwu'])`
  - `sys_code`（`Optional[str]`）: The system code.，默认值 `Field(None, description='The system code.', examples=['dbgpt', 'auth_manager', 'data_platform'])`
  - `input_values`（`Optional[dict]`）: The prompt variables debug value.，默认值 `Field(None, description='The prompt variables debug value.')`
  - `temperature`（`Optional[float]`）: The prompt debug temperature.，默认值 `Field(default=0.5, description='The prompt debug temperature.')`
  - `debug_model`（`Optional[str]`）: The prompt debug model.，默认值 `Field(None, description='The prompt debug model.', examples=['vicuna13b', 'chatgpt'])`
  - `user_input`（`Optional[str]`）: The prompt debug user input.，默认值 `Field(None, description='The prompt debug user input.')`

### `PromptVerifyInput`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/prompt/api/schemas.py`
- 字段：
  - `chat_scene`（`Optional[str]`）: The chat scene, e.g. chat_with_db_execute, chat_excel, chat_with_db_qa.，默认值 `Field(None, description='The chat scene, e.g. chat_with_db_execute, chat_excel, chat_with_db_qa.', examples=['chat_with_db_execute', 'chat_excel', 'chat_with_db_qa'])`
  - `sub_chat_scene`（`Optional[str]`）: The sub chat scene.，默认值 `Field(None, description='The sub chat scene.', examples=['sub_scene_1', 'sub_scene_2', 'sub_scene_3'])`
  - `prompt_code`（`Optional[str]`）: The prompt code.，默认值 `Field(None, description='The prompt code.', examples=['test123', 'test456'])`
  - `prompt_type`（`Optional[str]`）: The prompt type, either common or private.，默认值 `Field(None, description='The prompt type, either common or private.', examples=['common', 'private'])`
  - `prompt_name`（`Optional[str]`）: The prompt name.，默认值 `Field(None, description='The prompt name.', examples=['code_assistant', 'joker', 'data_analysis_expert'])`
  - `content`（`Optional[str]`）: The prompt content.，默认值 `Field(None, description='The prompt content.', examples=['Write a qsort function in python', 'Tell me a joke about AI', 'You are a data analysis expert.'])`
  - `prompt_desc`（`Optional[str]`）: The prompt description.，默认值 `Field(None, description='The prompt description.', examples=['This is a prompt for code assistant.', 'This is a prompt for joker.', 'This is a prompt for data analysis expert.'])`
  - `response_schema`（`Optional[str]`）: The prompt response schema.，默认值 `Field(None, description='The prompt response schema.', examples=['None', '{"xx": "123"}'])`
  - `input_variables`（`Optional[str]`）: The prompt variables.，默认值 `Field(None, description='The prompt variables.', examples=['display_type', 'resources'])`
  - `model`（`Optional[str]`）: The prompt can use model.，默认值 `Field(None, description='The prompt can use model.', examples=['vicuna13b', 'chatgpt'])`
  - `prompt_language`（`Optional[str]`）: The prompt language.，默认值 `Field(None, description='The prompt language.', examples=['en', 'zh'])`
  - `user_code`（`Optional[str]`）: The user id.，默认值 `Field(None, description='The user id.', examples=[''])`
  - `user_name`（`Optional[str]`）: The user name.，默认值 `Field(None, description='The user name.', examples=['zhangsan', 'lisi', 'wangwu'])`
  - `sys_code`（`Optional[str]`）: The system code.，默认值 `Field(None, description='The system code.', examples=['dbgpt', 'auth_manager', 'data_platform'])`
  - `llm_out`（`Optional[str]`）: The llm out of prompt.，默认值 `Field(None, description='The llm out of prompt.')`

### `ServeRequest`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/prompt/api/schemas.py`
类说明：Prompt request model.
- 字段：
  - `chat_scene`（`Optional[str]`）: The chat scene, e.g. chat_with_db_execute, chat_excel, chat_with_db_qa.，默认值 `Field(None, description='The chat scene, e.g. chat_with_db_execute, chat_excel, chat_with_db_qa.', examples=['chat_with_db_execute', 'chat_excel', 'chat_with_db_qa'])`
  - `sub_chat_scene`（`Optional[str]`）: The sub chat scene.，默认值 `Field(None, description='The sub chat scene.', examples=['sub_scene_1', 'sub_scene_2', 'sub_scene_3'])`
  - `prompt_code`（`Optional[str]`）: The prompt code.，默认值 `Field(None, description='The prompt code.', examples=['test123', 'test456'])`
  - `prompt_type`（`Optional[str]`）: The prompt type, either common or private.，默认值 `Field(None, description='The prompt type, either common or private.', examples=['common', 'private'])`
  - `prompt_name`（`Optional[str]`）: The prompt name.，默认值 `Field(None, description='The prompt name.', examples=['code_assistant', 'joker', 'data_analysis_expert'])`
  - `content`（`Optional[str]`）: The prompt content.，默认值 `Field(None, description='The prompt content.', examples=['Write a qsort function in python', 'Tell me a joke about AI', 'You are a data analysis expert.'])`
  - `prompt_desc`（`Optional[str]`）: The prompt description.，默认值 `Field(None, description='The prompt description.', examples=['This is a prompt for code assistant.', 'This is a prompt for joker.', 'This is a prompt for data analysis expert.'])`
  - `response_schema`（`Optional[str]`）: The prompt response schema.，默认值 `Field(None, description='The prompt response schema.', examples=['None', '{"xx": "123"}'])`
  - `input_variables`（`Optional[str]`）: The prompt variables.，默认值 `Field(None, description='The prompt variables.', examples=['display_type', 'resources'])`
  - `model`（`Optional[str]`）: The prompt can use model.，默认值 `Field(None, description='The prompt can use model.', examples=['vicuna13b', 'chatgpt'])`
  - `prompt_language`（`Optional[str]`）: The prompt language.，默认值 `Field(None, description='The prompt language.', examples=['en', 'zh'])`
  - `user_code`（`Optional[str]`）: The user id.，默认值 `Field(None, description='The user id.', examples=[''])`
  - `user_name`（`Optional[str]`）: The user name.，默认值 `Field(None, description='The user name.', examples=['zhangsan', 'lisi', 'wangwu'])`
  - `sys_code`（`Optional[str]`）: The system code.，默认值 `Field(None, description='The system code.', examples=['dbgpt', 'auth_manager', 'data_platform'])`

### `KnowledgeRetrieveRequest`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/rag/api/schemas.py`
类说明：Retrieve request
- 字段：
  - `space_id`（`int`）: space id，默认值 `Field(None, description='space id')`
  - `query`（`str`）: query，默认值 `Field(None, description='query')`
  - `top_k`（`Optional[int]`）: top k，默认值 `Field(5, description='top k')`
  - `score_threshold`（`Optional[float]`）: score threshold，默认值 `Field(0.0, description='score threshold')`

### `KnowledgeSyncRequest`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/rag/api/schemas.py`
类说明：Sync request
- 字段：
  - `doc_id`（`Optional[int]`）: The doc id，默认值 `Field(None, description='The doc id')`
  - `space_id`（`Optional[str]`）: space id，默认值 `Field(None, description='space id')`
  - `model_name`（`Optional[str]`）: model name，默认值 `Field(None, description='model name')`
  - `chunk_parameters`（`Optional[ChunkParameters]`）: chunk parameters，默认值 `Field(None, description='chunk parameters')`

### `SpaceServeRequest`

定义位置：`packages/dbgpt-serve/src/dbgpt_serve/rag/api/schemas.py`
类说明：name: knowledge space name
- 字段：
  - `id`（`Optional[int]`）: The space id，默认值 `Field(None, description='The space id')`
  - `name`（`str`）: The space name，默认值 `Field(None, description='The space name')`
  - `vector_type`（`str`）: The vector type，默认值 `Field(None, description='The vector type')`
  - `domain_type`（`str`）: The domain type，默认值 `Field(None, description='The domain type')`
  - `desc`（`Optional[str]`）: The description，默认值 `Field(None, description='The description')`
  - `owner`（`Optional[str]`）: The owner，默认值 `Field(None, description='The owner')`
  - `context`（`Optional[str]`）: The context，默认值 `Field(None, description='The context')`
  - `gmt_created`（`Optional[str]`）: The created time，默认值 `Field(None, description='The created time')`
  - `gmt_modified`（`Optional[str]`）: The modified time，默认值 `Field(None, description='The modified time')`
