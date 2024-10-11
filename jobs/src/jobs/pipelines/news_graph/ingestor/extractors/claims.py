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
from jobs.pipelines.news_graph.models import Claim
from jobs.pipelines.news_graph.prompts import EXTRACT_CLAIMS_PROMPT
from jobs.pipelines.utils import rate_limited_task
from jobs.pipelines.utils import tqdm_iterable

CLAIM_EXTRACTION_MESSAGE = """
ENTITIES
----------
{entities_json}

TEXT
----------
{text_unit}
"""


class ClaimOutput(BaseModel):
    claims: list[Claim] = Field(
        title="Claims", description="List of claims identified."
    )


@ell.complex(
    model="meta-llama/llama-3.1-70b-instruct",
    response_format={"type": "json_object"},
    extra_body=openrouter_extra_body,
)
def extract_claims(entities_json: str, text_unit: str):
    return [
        ell.system(
            EXTRACT_CLAIMS_PROMPT.format(
                current_date=datetime.now(UTC).strftime("%Y-%m-%d"),
                output_schema=ClaimOutput.model_json_schema(),
            )
        ),
        ell.user(
            CLAIM_EXTRACTION_MESSAGE.format(
                entities_json=entities_json,
                text_unit=text_unit,
            )
        ),
    ]


class ClaimsExtractor(BaseExtractor):
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

        claims = []
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
                extract_claims, entities_json, node.text
            )
        except Exception as e:
            raise NewsGraphLLMError(f"Failed to invoke LLM: {e}") from e

        try:
            raw_claims = json.loads(raw_result.text_only)
        except json.JSONDecodeError as e:
            raise NewsGraphExtractionError(
                f"Failed to parse claims JSON from LLM output: {raw_result.text_only}"
            ) from e
        else:
            try:
                for r in raw_claims["claims"]:
                    if isinstance(r, dict):
                        try:
                            claims.append(Claim.model_validate(r))
                        except pydantic.ValidationError as e:
                            raise NewsGraphExtractionError(
                                f"Failed to validate entity: {r}"
                            ) from e
            except KeyError as e:
                raise NewsGraphExtractionError(
                    f"Failed to parse claims from LLM output: {raw_claims}"
                ) from e
        return claims

    async def aextract(self, nodes):
        claims = []

        tasks = [
            asyncio.create_task(self.invoke_and_parse_results(node)) for node in nodes
        ]
        async for task in tqdm_iterable(tasks, "Extracting claims"):
            try:
                raw_results = await task
                claims.append({"claims": raw_results})
            except Exception:
                claims.append({"claims": None})

        return claims
