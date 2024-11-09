from typing import Any

import ell
from pydantic import BaseModel
from pydantic import Field

from jobs.config import pplx_client

from .prompts import RESEARCH_PROMPT


class AgentToolResponse(BaseModel):
    function: str
    response: Any


@ell.complex(
    model="llama-3.1-sonar-large-128k-online",
    client=pplx_client,
    exempt_from_tracking=True,
)
def pplx_search(query: str):
    return [
        ell.system(RESEARCH_PROMPT),
        ell.user(f"{query}"),
    ]


@ell.tool()
def search_knowledge_base(
    query: str = Field(
        description="The query to search the knowledge base for, phrased as a question."
    ),
) -> AgentToolResponse:
    """
    Search a public knowledge base for information.
    """

    pplx_response = pplx_search(query)
    response = AgentToolResponse(
        function="search_knowledge_base",
        response=pplx_response[0].text_only,
    )

    return response.model_dump()


@ell.tool()
def invite_expert(
    profile_description: str = Field(
        description="The profile description of the expert to invite."
    ),
) -> AgentToolResponse:
    """
    Invite an expert to the podcast. You may only have one expert at a time.
    """
    response = AgentToolResponse(
        function="invite_expert",
        response=profile_description,
    )
    return response.model_dump()


@ell.tool()
def speak_in_podcast(
    message: str = Field(description="The message to speak in the podcast."),
) -> AgentToolResponse:
    """
    Speak in the podcast. Your message will be added to the podcast transcript.
    This also ends your speaking turn.
    """
    response = AgentToolResponse(function="speak_in_podcast", response=message)
    return response.model_dump()


@ell.tool()
def end_expert_interview() -> AgentToolResponse:
    """
    End the expert interview. This allows you to invite a new expert.
    """
    response = AgentToolResponse(
        function="end_expert_interview",
        response=None,
    )
    return response.model_dump()


@ell.tool()
def end_podcast() -> AgentToolResponse:
    """
    End the podcast.
    """
    response = AgentToolResponse(
        function="end_podcast",
        response=None,
    )
    return response.model_dump()
