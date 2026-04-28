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
            f"\n{'>'*60}"
            f"\n>>>>>>>> [DB对话任务] 开始加载数据库 Schema 向量上下文"
            f"\n>>>>>>>> 数据库: {self.db_name}"
            f"\n>>>>>>>> 用户问题: {user_input[:120]}"
            f"\n>>>>>>>> top_k={self.curr_config.schema_retrieve_top_k}"
            f"\n{'>'*60}"
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
                f"\n{'>'*60}\n"
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
                    f">>>>>>>> [DB对话任务] 零命中降级完成 | 获取 {len(table_infos)} 条表结构"
                    f"\n{'>'*60}\n"
                )
            # ─────────────────────────────────────────────────────────────────
        except Exception as e:
            print(
                f"\n>>>>>>>> [DB对话任务] ⚠️  向量检索失败，降级到全量 DDL 读取！"
                f"\n>>>>>>>> 失败原因: {e}"
                f"\n>>>>>>>> 降级路径: table_simple_info() 直接读取数据库表结构"
                f"\n{'>'*60}"
            )
            logger.error(f"Retrieved table info error: {str(e)}")
            table_infos = await blocking_func_to_async(
                self._executor, self.database.table_simple_info
            )
            if len(table_infos) > self.curr_config.schema_max_tokens:
                table_infos = table_infos[: self.curr_config.schema_max_tokens]
            print(
                f">>>>>>>> [DB对话任务] 降级读取完成 | 获取 {len(table_infos)} 条表信息"
                f"\n{'>'*60}\n"
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
        return self.database.run_to_df
