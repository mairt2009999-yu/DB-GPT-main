"""DBSummaryClient class."""

import logging
import time
import traceback
from typing import Any, Dict, List, Optional, Tuple

from dbgpt.component import SystemApp
from dbgpt.core import Embeddings
from dbgpt.rag.embedding.embedding_factory import EmbeddingFactory
from dbgpt.rag.text_splitter.text_splitter import RDBTextSplitter
from dbgpt.storage.vector_store.base import VectorStoreBase
from dbgpt_ext.rag import ChunkParameters
from dbgpt_ext.rag.summary.gdbms_db_summary import GdbmsSummary
from dbgpt_ext.rag.summary.rdbms_db_summary import RdbmsSummary
from dbgpt_serve.datasource.manages import ConnectorManager
from dbgpt_serve.rag.storage_manager import StorageManager

logger = logging.getLogger(__name__)
_LOG_PREFIX = "[DB_SUMMARY_EMBED]"


class DBSummaryClient:
    """The client for DBSummary.

    DB Summary client, provide db_summary_embedding(put db profile and table profile
    summary into vector store), get_similar_tables method(get user query related tables
    info)

    Args:
        system_app (SystemApp): Main System Application class that manages the
            lifecycle and registration of components..
    """

    def __init__(self, system_app: SystemApp):
        """Create a new DBSummaryClient."""
        self.system_app = system_app

        self.app_config = self.system_app.config.configs.get("app_config")
        self.storage_config = self.app_config.rag.storage

    @property
    def embeddings(self) -> Embeddings:
        """Get the embeddings."""
        embedding_factory: EmbeddingFactory = self.system_app.get_component(
            "embedding_factory", component_type=EmbeddingFactory
        )
        return embedding_factory.create()

    def db_summary_embedding(
        self,
        dbname: str,
        db_type: str,
        trigger: str = "unknown",
        force_refresh: bool = False,
        raise_on_error: bool = True,
    ) -> None:
        """Put db profile and table profile summary into vector store."""
        start_time = time.perf_counter()
        logger.info(
            "%s START trigger=%s db_name=%s db_type=%s force_refresh=%s",
            _LOG_PREFIX,
            trigger,
            dbname,
            db_type,
            force_refresh,
        )
        try:
            read_schema_start = time.perf_counter()
            logger.info(
                "%s READ_SCHEMA_BEGIN trigger=%s db_name=%s db_type=%s",
                _LOG_PREFIX,
                trigger,
                dbname,
                db_type,
            )
            db_summary_client = self.create_summary_client(dbname, db_type)
            table_names = sorted(db_summary_client.db.get_table_names())
            read_schema_elapsed_ms = int(
                (time.perf_counter() - read_schema_start) * 1000
            )
            logger.info(
                "%s READ_SCHEMA_DONE trigger=%s db_name=%s db_type=%s elapsed_ms=%s "
                "table_count=%s",
                _LOG_PREFIX,
                trigger,
                dbname,
                db_type,
                read_schema_elapsed_ms,
                len(table_names),
            )
            logger.info(
                "%s TABLES trigger=%s db_name=%s db_type=%s table_count=%s tables=%s",
                _LOG_PREFIX,
                trigger,
                dbname,
                db_type,
                len(table_names),
                table_names,
            )
            for idx, table_name in enumerate(table_names, 1):
                logger.info(
                    "%s TABLE_ITEM trigger=%s db_name=%s db_type=%s index=%s/%s "
                    "table=%s",
                    _LOG_PREFIX,
                    trigger,
                    dbname,
                    db_type,
                    idx,
                    len(table_names),
                    table_name,
                )

            self.init_db_profile(
                db_summary_client,
                dbname,
                db_type=db_type,
                trigger=trigger,
                table_names=table_names,
                force_refresh=force_refresh,
            )

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(
                "%s SUCCESS trigger=%s db_name=%s db_type=%s elapsed_ms=%s",
                _LOG_PREFIX,
                trigger,
                dbname,
                db_type,
                elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            trace = traceback.format_exc()
            if not raise_on_error:
                logger.warning(
                    "%s SKIP_UNAVAILABLE trigger=%s db_name=%s db_type=%s "
                    "elapsed_ms=%s error=%s",
                    _LOG_PREFIX,
                    trigger,
                    dbname,
                    db_type,
                    elapsed_ms,
                    str(e),
                )
                logger.debug(
                    "%s SKIP_UNAVAILABLE traceback=%s",
                    _LOG_PREFIX,
                    trace,
                )
                return
            logger.error(
                "%s FAILED trigger=%s db_name=%s db_type=%s elapsed_ms=%s "
                "error=%s traceback=%s",
                _LOG_PREFIX,
                trigger,
                dbname,
                db_type,
                elapsed_ms,
                str(e),
                trace,
            )
            raise

    def get_db_summary(self, dbname, query, topk):
        """Get user query related tables info."""
        import re

        from dbgpt_ext.rag.retriever.db_schema import DBSchemaRetriever

        print(
            f"\n{'>'*60}"
            f"\n>>>>>>>> [DB Schema检索] 开始检索数据库向量库"
            f"\n>>>>>>>> 召回引擎: DBSchemaRetriever"
            f"\n>>>>>>>> 检索数据库: {dbname}"
            f"\n>>>>>>>> 检索向量库: 表索引({dbname}_profile), "
            f"字段索引({dbname}_profile_field)"
            f"\n>>>>>>>> 检索参数: top_k={topk}, query='{query[:120]}'"
            f"\n{'>'*60}"
        )

        table_vector_connector, field_vector_connector = (
            self._get_vector_connector_by_db(dbname)
        )

        # 🩺 Vector Store Health Check
        try:
            table_count = table_vector_connector._get_collection_safe().count()
            if table_count == 0:
                logger.warning(
                    "Vector store '%s_profile' is empty. "
                    "Please vectorize the database.",
                    dbname,
                )
        except Exception as _e:
            logger.warning(f"Failed to check vector store health: {_e}")

        retriever = DBSchemaRetriever(
            top_k=topk,
            table_vector_store_connector=table_vector_connector,
            field_vector_store_connector=field_vector_connector,
            separator="--table-field-separator--",
        )

        table_docs = retriever.retrieve(query)
        ans = [d.content for d in table_docs]

        # 提取命中的表名：优先从 metadata，其次从 DDL 内容解析
        def _extract_table_name(doc, content: str) -> str:
            # 1. 尝试从 chunk metadata 中获取
            meta = getattr(doc, "metadata", {}) or {}
            for key in ("table_name", "source", "name"):
                if meta.get(key):
                    return str(meta[key])
            # 2. 从 CREATE TABLE DDL 中提取（支持反引号/双引号/方括号/无符号）
            m = re.search(
                r"CREATE\s+TABLE\s+[`\"\[]?(\w+)[`\"\]]?",
                content,
                re.IGNORECASE,
            )
            if m:
                return m.group(1)
            # 3. 从我们的跳过注释格式中提取
            m2 = re.search(r"--\s*Table:\s*(\S+)", content)
            if m2:
                return m2.group(1)
            return "(未知表名)"

        table_names = [
            _extract_table_name(doc, content)
            for doc, content in zip(table_docs, ans)
        ]

        print(
            f"\n>>>>>>>> [DB Schema检索] 检索完成"
            f"\n>>>>>>>> 召回来源: {dbname}_profile / {dbname}_profile_field"
            f"\n>>>>>>>> 命中表数量: {len(ans)}"
            f"\n>>>>>>>> 命中表名列表: {table_names}"
        )
        for i, (name, content) in enumerate(zip(table_names, ans)):
            preview = content[:200].replace("\n", " ")
            print(f">>>>>>>> 表[{i+1}] 表名={name} | 内容预览: {preview}")
        print(f"{'>'*60}\n")

        return ans


    def init_db_summary(self):
        """Initialize db summary profile."""
        local_db_manager = ConnectorManager.get_instance(self.system_app)
        db_mange = local_db_manager
        dbs = db_mange.get_db_list()
        for item in dbs:
            try:
                self.db_summary_embedding(
                    item["db_name"],
                    item["db_type"],
                    trigger="serve.datasource.init_db_summary",
                    raise_on_error=False,
                )
            except Exception as e:
                trace = traceback.format_exc()
                logger.error(
                    "%s FAILED trigger=%s db_name=%s db_type=%s error=%s "
                    "traceback=%s",
                    _LOG_PREFIX,
                    "serve.datasource.init_db_summary",
                    item["db_name"],
                    item["db_type"],
                    str(e),
                    trace,
                )

    def init_db_profile(
        self,
        db_summary_client: Any,
        dbname: str,
        db_type: str = "unknown",
        trigger: str = "unknown",
        table_names: Optional[List[str]] = None,
        force_refresh: bool = False,
    ) -> None:
        """Initialize db summary profile.

        Args:
            db_summary_client: DB summary client.
            dbname: Database name.
            db_type: Database type.
            trigger: Trigger source.
            table_names: Tables to vectorize.
        """
        vector_store_name = dbname + "_profile"
        field_vector_store_name = dbname + "_profile_field"
        table_names = table_names or []

        table_vector_connector, field_vector_connector = (
            self._get_vector_connector_by_db(dbname)
        )
        table_vector_exists_before = table_vector_connector.vector_name_exists()
        field_vector_exists_before = field_vector_connector.vector_name_exists()
        print(
            f"\n{'─'*60}"
            f"\n[DBSchema向量化检查] db={dbname} | trigger={trigger}"
            f"\n[DBSchema向量化检查] table向量是否存在: {table_vector_exists_before} "
            f"| field向量是否存在: {field_vector_exists_before}"
            f"\n[DBSchema向量化检查] force_refresh={force_refresh}"
            f"\n{'─'*60}"
        )
        logger.info(
            "%s VECTOR_TARGET trigger=%s db_name=%s db_type=%s "
            "table_vector_name=%s field_vector_name=%s force_refresh=%s",
            _LOG_PREFIX,
            trigger,
            dbname,
            db_type,
            vector_store_name,
            field_vector_store_name,
            force_refresh,
        )
        # ─── force_refresh: 无条件先清缓存取全新连接器 ─────────────────────
        # BUG ROOT CAUSE: 旧连接器的 self._collection 指向已删除的 collection。
        # ChromaDB 0.6.x 隐式重建 collection 时不会保留 hnsw:space=cosine，
        # 导致数据以 L2 写入，查询距离 ~7106，score = 1-7106 << -1 全部被过滤。
        if force_refresh:
            storage_manager_inst = StorageManager.get_instance(self.system_app)
            storage_manager_inst.delete_from_cache(vector_store_name)
            storage_manager_inst.delete_from_cache(field_vector_store_name)
            # 取全新连接器（新 ChromaStore 实例，含正确 hnsw:space=cosine 元数据）
            table_vector_connector, field_vector_connector = (
                self._get_vector_connector_by_db(dbname)
            )
            # 用新连接器重新检查是否存在数据
            table_vector_exists_before = table_vector_connector.vector_name_exists()
            field_vector_exists_before = field_vector_connector.vector_name_exists()

            if table_vector_exists_before or field_vector_exists_before:
                print(
                    f"[DBSchema向量化] 🔁 FORCE_REFRESH: 删除旧向量 | db={dbname}"
                )
                logger.info(
                    "%s PERSIST_STATS trigger=%s db_name=%s db_type=%s status=%s "
                    "table_vector_name=%s field_vector_name=%s",
                    _LOG_PREFIX,
                    trigger,
                    dbname,
                    db_type,
                    "FORCE_REFRESH_DELETE",
                    vector_store_name,
                    field_vector_store_name,
                )
                table_vector_connector.delete_vector_name(vector_store_name)
                field_vector_connector.delete_vector_name(field_vector_store_name)
                # 删除后再次清缓存，确保下次获取的是全新空实例
                storage_manager_inst.delete_from_cache(vector_store_name)
                storage_manager_inst.delete_from_cache(field_vector_store_name)
                table_vector_connector, field_vector_connector = (
                    self._get_vector_connector_by_db(dbname)
                )
                table_vector_exists_before = False
                field_vector_exists_before = False
        # ──────────────────────────────────────────────────────────────────────

        if not table_vector_exists_before:
            print(
                "[DBSchema向量化] ❌ 向量不存在 → "
                f"开始重新对数据库 Schema 进行向量化 | db={dbname}"
            )
            from dbgpt_ext.rag.assembler.db_schema import DBSchemaAssembler
            from dbgpt_ext.rag.summary.rdbms_db_summary import _DEFAULT_COLUMN_SEPARATOR

            chunk_parameters = ChunkParameters(
                text_splitter=RDBTextSplitter(
                    column_separator=_DEFAULT_COLUMN_SEPARATOR,
                    separator="--table-field-separator--",
                )
            )
            build_chunks_start = time.perf_counter()
            logger.info(
                "%s BUILD_CHUNKS_BEGIN trigger=%s db_name=%s db_type=%s table_count=%s",
                _LOG_PREFIX,
                trigger,
                dbname,
                db_type,
                len(table_names),
            )
            db_assembler = DBSchemaAssembler.load_from_connection(
                connector=db_summary_client.db,
                table_vector_store_connector=table_vector_connector,
                field_vector_store_connector=field_vector_connector,
                chunk_parameters=chunk_parameters,
                max_seq_length=self.app_config.service.web.embedding_model_max_seq_len,
            )

            chunks = db_assembler.get_chunks()
            chunk_stats = self._calculate_chunk_stats(chunks)
            build_chunks_elapsed_ms = int(
                (time.perf_counter() - build_chunks_start) * 1000
            )
            logger.info(
                "%s BUILD_CHUNKS_DONE trigger=%s db_name=%s db_type=%s elapsed_ms=%s "
                "total_chunks=%s table_chunks=%s field_chunks=%s",
                _LOG_PREFIX,
                trigger,
                dbname,
                db_type,
                build_chunks_elapsed_ms,
                chunk_stats["total_chunks"],
                chunk_stats["table_chunks"],
                chunk_stats["field_chunks"],
            )
            logger.info(
                "%s PERSIST_STATS trigger=%s db_name=%s db_type=%s status=%s "
                "table_count=%s total_chunks=%s table_chunks=%s field_chunks=%s "
                "table_vector_name=%s field_vector_name=%s "
                "table_vector_exists_before=%s field_vector_exists_before=%s "
                "tables=%s",
                _LOG_PREFIX,
                trigger,
                dbname,
                db_type,
                "PERSISTING",
                len(table_names),
                chunk_stats["total_chunks"],
                chunk_stats["table_chunks"],
                chunk_stats["field_chunks"],
                vector_store_name,
                field_vector_store_name,
                table_vector_exists_before,
                field_vector_exists_before,
                table_names,
            )
            persisted_table_chunk_ids: List[str] = []
            persist_start = time.perf_counter()
            if chunk_stats["total_chunks"] > 0:
                print(
                    f"[DBSchema向量化] → 正在内嵌并写入向量库 | db={dbname} | "
                    f"total_chunks={chunk_stats['total_chunks']} | "
                    f"table_chunks={chunk_stats['table_chunks']} | "
                    f"field_chunks={chunk_stats['field_chunks']}"
                )
                logger.info(
                    "%s EMBED_PERSIST_BEGIN trigger=%s db_name=%s db_type=%s "
                    "total_chunks=%s table_chunks=%s field_chunks=%s",
                    _LOG_PREFIX,
                    trigger,
                    dbname,
                    db_type,
                    chunk_stats["total_chunks"],
                    chunk_stats["table_chunks"],
                    chunk_stats["field_chunks"],
                )
                persisted_table_chunk_ids = db_assembler.persist()
                print(
                    f"[DBSchema向量化] ✔ 向量化完成 | db={dbname} | "
                    f"写入 {len(persisted_table_chunk_ids)} 条 chunk"
                )
            persist_elapsed_ms = int((time.perf_counter() - persist_start) * 1000)

            table_vector_exists_after = table_vector_connector.vector_name_exists()
            field_vector_exists_after = field_vector_connector.vector_name_exists()
            logger.info(
                "%s PERSIST_STATS trigger=%s db_name=%s db_type=%s status=%s "
                "persisted_table_chunk_ids=%s table_vector_exists_after=%s "
                "field_vector_exists_after=%s persist_elapsed_ms=%s",
                _LOG_PREFIX,
                trigger,
                dbname,
                db_type,
                "DONE",
                len(persisted_table_chunk_ids),
                table_vector_exists_after,
                field_vector_exists_after,
                persist_elapsed_ms,
            )
        else:
            print(
                "[DBSchema向量化] ✅ SKIP: 向量已存在，"
                f"跳过向量化 → 直接查询已有向量数据 | db={dbname}"
            )
            logger.info(
                "%s PERSIST_STATS trigger=%s db_name=%s db_type=%s status=%s "
                "table_count=%s total_chunks=%s table_chunks=%s field_chunks=%s "
                "table_vector_name=%s field_vector_name=%s "
                "table_vector_exists_before=%s field_vector_exists_before=%s "
                "tables=%s",
                _LOG_PREFIX,
                trigger,
                dbname,
                db_type,
                "SKIP_EXIST",
                len(table_names),
                0,
                0,
                0,
                vector_store_name,
                field_vector_store_name,
                table_vector_exists_before,
                field_vector_exists_before,
                table_names,
            )

    @staticmethod
    def _calculate_chunk_stats(chunks: List[Any]) -> Dict[str, int]:
        total_chunks = len(chunks)
        field_chunks = 0
        for chunk in chunks:
            metadata = getattr(chunk, "metadata", {}) or {}
            if metadata.get("separated") and metadata.get("part") != "table":
                field_chunks += 1
        table_chunks = total_chunks - field_chunks
        return {
            "total_chunks": total_chunks,
            "table_chunks": table_chunks,
            "field_chunks": field_chunks,
        }

    def delete_db_profile(self, dbname):
        """Delete db profile."""
        table_vector_store_name = dbname + "_profile"
        field_vector_store_name = dbname + "_profile_field"

        table_vector_connector, field_vector_connector = (
            self._get_vector_connector_by_db(dbname)
        )

        table_vector_connector.delete_vector_name(table_vector_store_name)
        field_vector_connector.delete_vector_name(field_vector_store_name)
        logger.info(f"delete db profile {dbname} success")

    @staticmethod
    def create_summary_client(dbname: str, db_type: str):
        """
        Create a summary client based on the database type.

        Args:
            dbname (str): The name of the database.
            db_type (str): The type of the database.
        """
        if "graph" in db_type:
            return GdbmsSummary(dbname, db_type)
        else:
            return RdbmsSummary(dbname, db_type)

    def _get_vector_connector_by_db(
        self, dbname
    ) -> Tuple[VectorStoreBase, VectorStoreBase]:
        vector_store_name = dbname + "_profile"
        storage_manager = StorageManager.get_instance(self.system_app)
        table_vector_store = storage_manager.create_vector_store(
            index_name=vector_store_name
        )
        field_vector_store_name = dbname + "_profile_field"
        field_vector_store = storage_manager.create_vector_store(
            index_name=field_vector_store_name
        )
        return table_vector_store, field_vector_store
