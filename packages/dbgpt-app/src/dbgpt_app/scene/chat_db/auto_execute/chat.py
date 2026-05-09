import logging
from typing import Dict, Type

from dbgpt import SystemApp
from dbgpt.agent.util.api_call import ApiCall
from dbgpt.util.executor_utils import blocking_func_to_async
from dbgpt.util.tracer import root_tracer, trace
from dbgpt_app.scene import BaseChat, ChatScene
from dbgpt_app.scene.base_chat import ChatParam
from dbgpt_app.scene.chat_db.auto_execute.config import ChatWithDBExecuteConfig
from dbgpt_serve.core.config import GPTsAppCommonConfig
from dbgpt_serve.datasource.manages import ConnectorManager

logger = logging.getLogger(__name__)


class ChatWithDbAutoExecute(BaseChat):
    chat_scene: str = ChatScene.ChatWithDbExecute.value()

    """Number of results to return from the query"""

    @classmethod
    def param_class(cls) -> Type[GPTsAppCommonConfig]:
        return ChatWithDBExecuteConfig

    def __init__(self, chat_param: ChatParam, system_app: SystemApp):
        """Chat Data Module Initialization
        Args:
           - chat_param: Dict
            - chat_session_id: (str) chat session_id
            - current_user_input: (str) current user input
            - model_name:(str) llm model name
            - select_param:(str) dbname
        """
        self.db_name = chat_param.select_param
        self.curr_config = chat_param.real_app_config(ChatWithDBExecuteConfig)
        super().__init__(chat_param=chat_param, system_app=system_app)
        if not self.db_name:
            raise ValueError(
                f"{ChatScene.ChatWithDbExecute.value} mode should chose db!"
            )
        with root_tracer.start_span(
            "ChatWithDbAutoExecute.get_connect", metadata={"db_name": self.db_name}
        ):
            local_db_manager = ConnectorManager.get_instance(self.system_app)
            self.database = local_db_manager.get_connector(self.db_name)
        self.api_call = ApiCall()

    @trace()
    async def generate_input_values(self) -> Dict:
        """
        generate input values
        """
        try:
            from dbgpt_serve.datasource.service.db_summary_client import DBSummaryClient
        except ImportError:
            raise ValueError("Could not import DBSummaryClient. ")
        user_input = self.current_user_input.last_text
        client = DBSummaryClient(system_app=self.system_app)

        print(
            f"\n{'>' * 60}"
            f"\n>>>>>>>> [DB对话任务] 开始加载数据库 Schema 向量上下文"
            f"\n>>>>>>>> 数据库: {self.db_name}"
            f"\n>>>>>>>> 用户问题: {user_input[:120]}"
            f"\n>>>>>>>> top_k={self.curr_config.schema_retrieve_top_k}"
            f"\n{'>' * 60}"
        )

        try:
            with root_tracer.start_span("ChatWithDbAutoExecute.get_db_summary"):
                table_infos = await blocking_func_to_async(
                    self._executor,
                    client.get_db_summary,
                    self.db_name,
                    user_input,
                    self.curr_config.schema_retrieve_top_k,
                )
            print(
                f"\n>>>>>>>> [DB对话任务] Schema 向量检索成功"
                f"\n>>>>>>>> 命中相关表数量: {len(table_infos)}"
                f"\n>>>>>>>> 检索路径: 向量数据库 → DBSchemaRetriever"
                f"\n{'>' * 60}\n"
            )
            # ── 零命中降级：vector检索失败时直接读取数据库所有表结构 ──────────
            if not table_infos:
                logger.warning(
                    "Vector search returned 0 results for db=%s query='%s', "
                    "falling back to full DDL scan.",
                    self.db_name,
                    user_input[:80],
                )
                table_infos = await blocking_func_to_async(
                    self._executor, self.database.table_simple_info
                )
                if len(table_infos) > self.curr_config.schema_max_tokens:
                    table_infos = table_infos[: self.curr_config.schema_max_tokens]
                print(
                    ">>>>>>>> [DB对话任务] 零命中降级完成 | "
                    f"获取 {len(table_infos)} 条表结构"
                    f"\n{'>' * 60}\n"
                )
            # ─────────────────────────────────────────────────────────────────
        except Exception as e:
            print(
                f"\n>>>>>>>> [DB对话任务] ⚠️  向量检索失败，降级到全量 DDL 读取！"
                f"\n>>>>>>>> 失败原因: {e}"
                f"\n>>>>>>>> 降级路径: table_simple_info() 直接读取数据库表结构"
                f"\n{'>' * 60}"
            )
            logger.error(f"Retrieved table info error: {str(e)}")
            table_infos = await blocking_func_to_async(
                self._executor, self.database.table_simple_info
            )
            if len(table_infos) > self.curr_config.schema_max_tokens:
                table_infos = table_infos[: self.curr_config.schema_max_tokens]
            print(
                f">>>>>>>> [DB对话任务] 降级读取完成 | 获取 {len(table_infos)} 条表信息"
                f"\n{'>' * 60}\n"
            )

        input_values = {
            "db_name": self.db_name,
            "user_input": user_input,
            "top_k": self.curr_config.max_num_results,
            "dialect": self.database.dialect,
            "table_info": table_infos,
            "display_type": self._generate_numbered_list(),
        }
        return input_values

    def do_action(self, prompt_response):
        print(f"do_action:{prompt_response}")
        return self._make_rls_runner()

    def _make_rls_runner(self):
        """返回一个同步 callable(sql) -> DataFrame，内部经过 RLSAwareSQLExecutor。"""
        import asyncio

        from dbgpt_app.security.config import RLSConfig
        from dbgpt_app.security.principal import current_principal
        from dbgpt_app.security.rls_client import RLSClient
        from dbgpt_app.security.rls_executor import RLSAwareSQLExecutor
        from dbgpt_app.security.stub_rls_client import StubRLSClient

        # 1. 取 RLSClient（已注册到 SystemApp；mode=off 时是 StubRLSClient）
        try:
            rls_client = self.system_app.get_component(
                RLSClient.name, RLSClient, default_component=None
            )
        except Exception:
            rls_client = None
        if rls_client is None:
            try:
                rls_client = self.system_app.get_component(
                    StubRLSClient.name, StubRLSClient, default_component=None
                )
            except Exception:
                rls_client = None
        if rls_client is None:
            rls_client = StubRLSClient()

        # 2. 取 RLSConfig
        try:
            cfg = self.system_app.get_component(
                RLSConfig.name, RLSConfig, default_component=None
            )
        except Exception:
            cfg = None
        if cfg is None:
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
