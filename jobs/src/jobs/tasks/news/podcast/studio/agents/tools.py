import os

import ell
from pydantic import BaseModel
from pydantic import Field
from tavily import TavilyClient

tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


class AgentToolResponse(BaseModel):
    function: str
    response: str | None


@ell.tool()
def search_context(
    query: str = Field(description="The query to search the episode context for."),
) -> AgentToolResponse:
    """
    Search the episode context for more information about the topic.
    """
    print(f"Searching context for: {query}")
    response = AgentToolResponse(
        function="search_context",
        response=tavily_client.qna_search(query, search_depth="advanced"),
    )

    return response.model_dump()


@ell.tool()
def search_knowledge_base(
    query: str = Field(description="The query to search the knowledge base for."),
) -> AgentToolResponse:
    """
    Search a public knowledge base for information.
    """
    print(f"Searching knowledge base for: {query}")
    response = AgentToolResponse(
        function="search_knowledge_base",
        response=tavily_client.qna_search(query, search_depth="advanced"),
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
    print(f"Inviting expert: {profile_description}")
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
