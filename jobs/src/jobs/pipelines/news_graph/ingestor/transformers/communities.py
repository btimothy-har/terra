import asyncio
import json
from typing import List

from llama_index.core.schema import BaseNode
from llama_index.core.schema import TransformComponent
from retry_async import retry

from jobs.pipelines.news_graph.config import llm
from jobs.pipelines.news_graph.exceptions import NewsGraphExtractionError
from jobs.pipelines.news_graph.exceptions import NewsGraphLLMError
from jobs.pipelines.news_graph.models import CommunityReport
from jobs.pipelines.news_graph.prompts import COMMUNITY_REPORT
from jobs.pipelines.utils import rate_limited_task
from jobs.pipelines.utils import tqdm_iterable

output_llm = llm.with_structured_output(
    CommunityReport, method="json_mode", include_raw=True
)

prompt = COMMUNITY_REPORT.format(output_schema=CommunityReport.model_json_schema())


class CommunityReportGenerator(TransformComponent):
    def __call__(self, nodes: List[BaseNode], **kwargs) -> List[BaseNode]:
        asyncio.run(self.acall(nodes, **kwargs))

    async def acall(self, nodes: List[BaseNode], **kwargs) -> List[BaseNode]:
        tasks = [
            asyncio.create_task(self.summarize_community(node, **kwargs))
            for node in nodes
        ]

        transformed = []
        async for task in tqdm_iterable(tasks, "Summarizing communities..."):
            try:
                result = await task
                transformed.append(result)
            except Exception as e:
                print(e)
                continue

        return transformed

    @retry(
        (NewsGraphExtractionError, NewsGraphLLMError),
        is_async=True,
        tries=3,
        delay=1,
        backoff=2,
    )
    @rate_limited_task()
    async def summarize_community(self, node: BaseNode, **kwargs) -> BaseNode:
        node.metadata["raw"] = raw_text = node.text

        llm_input = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": raw_text},
        ]
        try:
            raw_result = await output_llm.ainvoke(llm_input)
        except Exception as e:
            raise NewsGraphLLMError(f"Failed to invoke LLM: {e}") from e

        result = raw_result["parsed"]
        if result is None:
            raw_response = raw_result["raw"].content
            if not raw_response:
                raise NewsGraphExtractionError(
                    "Failed to parse LLM output. Did not receive a response."
                )
            parsed_raw = json.loads(raw_response)
            try:
                result = CommunityReport(**parsed_raw["properties"])
            except Exception as e:
                raise NewsGraphExtractionError(
                    f"Failed to parse LLM output. Received: {raw_response}"
                ) from e

        node.text = result.summary
        node.metadata["title"] = result.title
        node.metadata["impact_severity_rating"] = result.impact_severity_rating
        node.metadata["rating_explanation"] = result.rating_explanation

        node.excluded_embed_metadata_keys = ["raw", "impact_severity_rating"]
        node.excluded_llm_metadata_keys = ["raw"]

        return node
