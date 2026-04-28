import logging
from concurrent.futures import Executor, ThreadPoolExecutor
from typing import List, Optional

from dbgpt.core import Chunk
from dbgpt.rag.retriever.base import BaseRetriever
from dbgpt.storage.vector_store.filters import MetadataFilters

logger = logging.getLogger(__name__)


class RetrieverChain(BaseRetriever):
    """Retriever chain class."""

    def __init__(
        self,
        retrievers: Optional[List[BaseRetriever]] = None,
        executor: Optional[Executor] = None,
    ):
        """Create retriever chain instance."""
        self._retrievers = retrievers or []
        self._executor = executor or ThreadPoolExecutor()

    def _retrieve(
        self, query: str, filters: Optional[MetadataFilters] = None
    ) -> List[Chunk]:
        """Retrieve knowledge chunks.
        Args:
            query (str): query text
            filters: (Optional[MetadataFilters]) metadata filters.
        Return:
            List[Chunk]: list of chunks
        """
        for retriever in self._retrievers:
            candidates = retriever.retrieve(query, filters)
            if candidates:
                return candidates
        return []

    async def _aretrieve(
        self, query: str, filters: Optional[MetadataFilters] = None
    ) -> List[Chunk]:
        """Async retrieve knowledge chunks.
        Args:
            query (str): query text
            filters: (Optional[MetadataFilters]) metadata filters.
        Return:
            List[Chunk]: list of chunks
        """
        for retriever in self._retrievers:
            candidates = await retriever.aretrieve(query=query, filters=filters)
            if candidates:
                return candidates
        return []

    def _retrieve_with_score(
        self,
        query: str,
        score_threshold: float,
        filters: Optional[MetadataFilters] = None,
    ) -> List[Chunk]:
        """Retrieve knowledge chunks.
        Args:
            query (str): query text
            filters: (Optional[MetadataFilters]) metadata filters.
        Return:
            List[Chunk]: list of chunks
        """
        print(
            f"[RetrieverChain] 开始检索链路 | query='{query[:80]}' | "
            f"score_threshold={score_threshold} | retriever_count={len(self._retrievers)}"
        )
        for retriever in self._retrievers:
            retriever_name = retriever.name() if hasattr(retriever, 'name') else type(retriever).__name__
            print(f"[RetrieverChain] 尝试 retriever: {retriever_name}")
            candidates_with_scores = retriever.retrieve_with_scores(
                query=query, score_threshold=score_threshold, filters=filters
            )
            if candidates_with_scores:
                print(
                    f"[RetrieverChain] ✅ {retriever_name} 命中！返回 "
                    f"{len(candidates_with_scores)} 条结果，不再继续后续 retriever"
                )
                return candidates_with_scores
            print(f"[RetrieverChain] ❌ {retriever_name} 未命中，继续下一个 retriever")
        print("[RetrieverChain] ⚠️  所有 retriever 均未命中，返回空列表")
        return []

    async def _aretrieve_with_score(
        self,
        query: str,
        score_threshold: float,
        filters: Optional[MetadataFilters] = None,
    ) -> List[Chunk]:
        """Retrieve knowledge chunks with score.
        Args:
            query (str): query text
            score_threshold (float): score threshold
            filters: (Optional[MetadataFilters]) metadata filters.
        Return:
            List[Chunk]: list of chunks with score
        """
        print(
            f"[RetrieverChain] [async] 开始检索链路 | query='{query[:80]}' | "
            f"score_threshold={score_threshold} | retriever_count={len(self._retrievers)}"
        )
        for retriever in self._retrievers:
            retriever_name = retriever.name() if hasattr(retriever, 'name') else type(retriever).__name__
            print(f"[RetrieverChain] [async] 尝试 retriever: {retriever_name}")
            candidates_with_scores = await retriever.aretrieve_with_scores(
                query=query, score_threshold=score_threshold, filters=filters
            )
            if candidates_with_scores:
                print(
                    f"[RetrieverChain] [async] ✅ {retriever_name} 命中！返回 "
                    f"{len(candidates_with_scores)} 条结果，不再继续后续 retriever"
                )
                return candidates_with_scores
            print(f"[RetrieverChain] [async] ❌ {retriever_name} 未命中，继续下一个 retriever")
        print("[RetrieverChain] [async] ⚠️  所有 retriever 均未命中，返回空列表")
        return []
