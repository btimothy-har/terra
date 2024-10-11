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
from jobs.pipelines.news_graph.models import Relationship
from jobs.pipelines.news_graph.prompts import EXTRACT_RELATIONSHIPS_PROMPT
from jobs.pipelines.utils import rate_limited_task
from jobs.pipelines.utils import tqdm_iterable

RELATIONSHIP_EXTRACTION_MESSAGE = """
ENTITIES
----------
{entities_json}

TEXT
----------
{text_unit}
"""


class RelationshipOutput(BaseModel):
    relationships: list[Relationship] = Field(
        title="Relationships",
        description="List of relationships identified.",
    )


@ell.complex(
    model="meta-llama/llama-3.1-70b-instruct",
    response_format={"type": "json_object"},
    extra_body=openrouter_extra_body,
)
def extract_relationships(entities_json: str, text_unit: str):
    return [
        ell.system(
            EXTRACT_RELATIONSHIPS_PROMPT.format(
                current_date=datetime.now(UTC).strftime("%Y-%m-%d"),
                output_schema=RelationshipOutput.model_json_schema(),
            )
        ),
        ell.user(
            RELATIONSHIP_EXTRACTION_MESSAGE.format(
                entities_json=entities_json,
                text_unit=text_unit,
            )
        ),
    ]


class RelationshipExtractor(BaseExtractor):
    @retry(
        (NewsGraphExtractionError, NewsGraphLLMError),
        is_async=True,
        tries=3,
        delay=1,
        backoff=2,
    )
    @rate_limited_task()
    async def invoke_and_parse_results(self, node):
        if not node.metadata.get("entities"):
            return None

        relationships = []
        entities_json = "\n".join(
            [
                m.model_dump_json(
                    include={
                        "name",
                        "entity_type",
                        "description",
                    }
                )
                for m in node.metadata["entities"]
            ]
        )

        try:
            raw_result = await asyncio.to_thread(
                extract_relationships, entities_json, node.text
            )
        except Exception as e:
            raise NewsGraphLLMError(f"Failed to invoke LLM: {e}") from e

        try:
            raw_relationships = json.loads(raw_result.text_only)
        except json.JSONDecodeError as e:
            raise NewsGraphExtractionError(
                f"Failed to parse relationships from LLM output: "
                f"{raw_result.text_only}"
            ) from e
        else:
            for r in raw_relationships["relationships"]:
                if isinstance(r, dict):
                    try:
                        relationships.append(Relationship.model_validate(r))
                    except pydantic.ValidationError as e:
                        raise NewsGraphExtractionError(
                            "Failed to validate relationship"
                        ) from e
        return relationships

    async def aextract(self, nodes):
        relationships = []

        tasks = [
            asyncio.create_task(self.invoke_and_parse_results(node)) for node in nodes
        ]
        async for task in tqdm_iterable(tasks, "Extracting relationships"):
            try:
                raw_results = await task
                relationships.append({"relationships": raw_results})
            except Exception:
                relationships.append({"relationships": None})

        return relationships
