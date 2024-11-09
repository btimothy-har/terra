import asyncio
import os
from abc import ABC
from abc import abstractmethod
from typing import Callable

import ell
from fargs.utils import token_limited_task
from llama_index.core.schema import MetadataMode
from llama_index.core.vector_stores import FilterOperator
from llama_index.core.vector_stores import MetadataFilter
from llama_index.core.vector_stores import MetadataFilters
from pydantic import BaseModel
from pydantic import Field

from ...config import embeddings
from ...graph import graph_engine
from ..events import StudioState
from .tools import AgentToolResponse


@token_limited_task(max_tokens=os.getenv("FARGS_LLM_TOKEN_LIMIT", 100_000))
async def invoke_llm(func: Callable, **kwargs):
    return await asyncio.to_thread(func, **kwargs)


class BaseStudioAgent(BaseModel, ABC):
    state: StudioState

    def build_context_tool(self):
        filters = MetadataFilters(
            filters=[
                MetadataFilter(
                    key="chunk_id",
                    operator=FilterOperator.IN,
                    value=self.state.community.metadata["sources"],
                ),
            ]
        )
        community_nodes_search = graph_engine.nodes_index.as_retriever(
            similarity_top_k=15,
            filters=filters,
            sparse_top_k=10,
            hybrid_top_k=10,
            embed_model=embeddings,
        )

        @ell.tool()
        def search_topic_context(
            query: str = Field(
                description="The query to search the topic context for."
            ),
        ) -> str:
            """
            Search the source articles of the community for more information
            about the topic. Returns a list of the most relevant articles.
            """
            nodes = community_nodes_search.retrieve(query)
            nodes_dump = [
                n.node.get_content(metadata_mode=MetadataMode.LLM) for n in nodes
            ]

            response = AgentToolResponse(
                function="search_topic_context",
                response="\n\n".join(nodes_dump),
            )
            return response.model_dump()

        return search_topic_context

    @abstractmethod
    async def _run_agent(self, **kwargs):
        pass

    async def invoke(self, **kwargs):
        return await self._run_agent(**kwargs)
