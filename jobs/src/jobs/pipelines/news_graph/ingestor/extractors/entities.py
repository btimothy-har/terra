import asyncio
import json
from datetime import UTC
from datetime import datetime

import ell
import pydantic
from llama_index.core.extractors import BaseExtractor
from pydantic import BaseModel
from pydantic import Field
from retry_async import retry

from jobs.config import openrouter_extra_body
from jobs.pipelines.news_graph.exceptions import NewsGraphExtractionError
from jobs.pipelines.news_graph.exceptions import NewsGraphLLMError
from jobs.pipelines.news_graph.models import Entity
from jobs.pipelines.news_graph.prompts import EXTRACT_ENTITIES_PROMPT
from jobs.pipelines.utils import rate_limited_task
from jobs.pipelines.utils import tqdm_iterable


class EntityOutput(BaseModel):
    entities: list[Entity] = Field(
        title="Entities", description="List of entities identified."
    )
    no_entities: bool = Field(
        title="No Entities Flag",
        description="If there are no entities to identify, set this to True.",
    )


@ell.complex(
    model="meta-llama/llama-3.1-70b-instruct",
    response_format={"type": "json_object"},
    extra_body=openrouter_extra_body,
)
def extract_entities(node_text: str):
    return [
        ell.system(
            EXTRACT_ENTITIES_PROMPT.format(
                current_date=datetime.now(UTC).strftime("%Y-%m-%d"),
                output_schema=EntityOutput.model_json_schema(),
            )
        ),
        ell.user(node_text),
    ]


class EntityExtractor(BaseExtractor):
    @retry(
        (NewsGraphExtractionError, NewsGraphLLMError),
        is_async=True,
        tries=3,
        delay=1,
        backoff=2,
    )
    @rate_limited_task()
    async def invoke_and_parse_results(self, node):
        entities = []

        try:
            raw_result = await asyncio.to_thread(extract_entities, node.text)
        except Exception as e:
            raise NewsGraphLLMError(f"Failed to invoke LLM: {e}") from e

        try:
            raw_entities = json.loads(raw_result.text_only)
        except json.JSONDecodeError as e:
            raise NewsGraphExtractionError(
                f"Failed to parse entities from LLM output: {raw_result.text_only}"
            ) from e
        else:
            try:
                if raw_entities["no_entities"]:
                    return []
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
        entities = []

        tasks = [
            asyncio.create_task(self.invoke_and_parse_results(node)) for node in nodes
        ]
        async for task in tqdm_iterable(tasks, "Extracting entities"):
            try:
                raw_results = await task
                entities.append({"entities": raw_results})
            except Exception as e:
                print(f"Error: {e}")
                entities.append({"entities": None})

        return entities
