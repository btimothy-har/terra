import asyncio
import json
from datetime import UTC
from datetime import datetime

import pydantic
from llama_index.core.extractors import BaseExtractor
from pydantic import BaseModel
from pydantic import Field
from retry import retry

from jobs.pipelines.news_graph.config import llm
from jobs.pipelines.news_graph.exceptions import NewsGraphExtractionError
from jobs.pipelines.news_graph.exceptions import NewsGraphLLMError
from jobs.pipelines.news_graph.models import Entity
from jobs.pipelines.news_graph.prompts import EXTRACT_ENTITIES_PROMPT
from jobs.pipelines.utils import openrouter_limiter


class EntityOutput(BaseModel):
    entities: list[Entity] = Field(
        title="Entities", description="List of entities identified."
    )


class EntityExtractor(BaseExtractor):
    def __init__(self):
        super().__init__()
        self.llm = llm.with_structured_output(
            EntityOutput, method="json_mode", include_raw=True
        )
        self.prompt = EXTRACT_ENTITIES_PROMPT.format(
            current_date=datetime.now(UTC).strftime("%Y-%m-%d"),
            output_schema=EntityOutput.model_json_schema(),
        )

    @retry((NewsGraphExtractionError, NewsGraphLLMError), tries=3, delay=1, backoff=2)
    async def invoke_and_parse_results(self, node):
        llm_input = [
            {"role": "system", "content": self.prompt},
            {"role": "user", "content": node.text},
        ]
        try:
            async with openrouter_limiter:
                result = await self.llm.ainvoke(llm_input)
        except Exception as e:
            raise NewsGraphLLMError(f"Failed to invoke LLM: {e}") from e

        if result["parsed"]:
            return result["parsed"].entities

        try:
            raw_entities = json.loads(result["raw"].content)
        except json.JSONDecodeError as e:
            raise NewsGraphExtractionError(
                f"Failed to parse entities from LLM output: {result['raw'].content}"
            ) from e
        else:
            entities = []
            try:
                for r in raw_entities["entities"]:
                    if isinstance(r, dict):
                        try:
                            entities.append(Entity.model_validate(r))
                        except pydantic.ValidationError as e:
                            raise NewsGraphExtractionError(
                                f"Failed to validate entity: {r}"
                            ) from e
            except KeyError as e:
                raise NewsGraphExtractionError(
                    f"Failed to parse entities from LLM output: {raw_entities}"
                ) from e
            return entities

    async def aextract(self, nodes):
        tasks = [self.invoke_and_parse_results(node) for node in nodes]

        raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        entities = [None if isinstance(r, Exception) else r for r in raw_results]
        return [{"entities": e} for e in entities]