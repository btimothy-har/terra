import asyncio
import json
from datetime import UTC
from datetime import datetime

import pydantic
from llama_index.core.extractors import BaseExtractor
from llama_index.core.utils import get_tqdm_iterable
from pydantic import BaseModel
from pydantic import Field
from retry import retry

from jobs.pipelines.news_graph.config import llm
from jobs.pipelines.news_graph.exceptions import NewsGraphExtractionError
from jobs.pipelines.news_graph.exceptions import NewsGraphLLMError
from jobs.pipelines.news_graph.models import Relationship
from jobs.pipelines.news_graph.prompts import EXTRACT_RELATIONSHIPS_PROMPT
from jobs.pipelines.utils import openrouter_limiter

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


output_llm = llm.with_structured_output(
    RelationshipOutput, method="json_mode", include_raw=True
)


class RelationshipExtractor(BaseExtractor):
    @retry((NewsGraphExtractionError, NewsGraphLLMError), tries=3, delay=1, backoff=2)
    async def invoke_and_parse_results(self, node, prompt):
        if not node.metadata.get("entities"):
            return None

        node_content = RELATIONSHIP_EXTRACTION_MESSAGE.format(
            entities_json="\n".join(
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
            ),
            text_unit=node.text,
        )

        llm_input = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": node_content},
        ]
        try:
            async with openrouter_limiter:
                result = await output_llm.ainvoke(llm_input)
        except Exception as e:
            raise NewsGraphLLMError(f"Failed to invoke LLM: {e}") from e

        if result["parsed"]:
            return result["parsed"].relationships

        try:
            raw_relationships = json.loads(result["raw"].content)
        except json.JSONDecodeError as e:
            raise NewsGraphExtractionError(
                f"Failed to parse relationships from LLM output: "
                f"{result['raw'].content}"
            ) from e
        else:
            relationships = []
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
        prompt = EXTRACT_RELATIONSHIPS_PROMPT.format(
            current_date=datetime.now(UTC).strftime("%Y-%m-%d"),
            output_schema=RelationshipOutput.model_json_schema(),
        )
        nodes_with_progress = get_tqdm_iterable(nodes, True, "Extracting relationships")
        tasks = [
            self.invoke_and_parse_results(node, prompt) for node in nodes_with_progress
        ]

        raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        relationships = [None if isinstance(r, Exception) else r for r in raw_results]
        return [{"relationships": r} for r in relationships]
