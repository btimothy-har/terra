import asyncio
from datetime import UTC
from datetime import datetime

import ell
from pydantic import BaseModel
from pydantic import Field

from ..events import StudioState
from .base import BaseStudioAgent
from .base import invoke_llm
from .prompts import ASSISTANT_BRIEF_PROMPT
from .prompts import ASSISTANT_TAGS_PROMPT
from .tools import AgentToolResponse
from .tools import search_knowledge_base


class PodcastTags(BaseModel):
    title: str = Field(description="The title of the podcast episode.")
    summary: str = Field(
        description="A short summary of the podcast episode, no more than 3 sentences."
    )
    tags: list[str] = Field(
        description="A list of tags that best describe the podcast episode."
    )


@ell.tool()
def submit_brief():
    """
    Submit your brief. Use this tool only when you are satisfied with the current
    state of your brief.
    """
    response = AgentToolResponse(
        function="submit_brief",
        response=None,
    )
    return response.model_dump()


class PodcastBriefAgent(BaseStudioAgent):
    def _build_brief_agent(self):
        context_tool = self.build_context_tool()

        @ell.complex(
            model="gpt-4o-mini",
            tools=[context_tool, search_knowledge_base, submit_brief],
            exempt_from_tracking=True,
            temperature=1,
            tool_choice="auto",
        )
        def assistant_agent(**kwargs):
            return [
                ell.system(
                    ASSISTANT_BRIEF_PROMPT.format(
                        date=kwargs.get(
                            "date", datetime.now(UTC).strftime("%-d %B %Y")
                        ),
                        podcast_topic=kwargs.get("podcast_topic"),
                        topic_description=kwargs.get("topic_description"),
                    )
                ),
                ell.user(f"Your current brief:\n\n {kwargs.get('brief', '')}"),
            ] + kwargs.get("tool_messages", [])

        return assistant_agent

    async def _run_agent(self, **kwargs) -> StudioState:
        step_active = True
        agent = self._build_brief_agent()
        tool_messages = []

        while step_active:
            args = {
                "date": datetime.now(UTC).strftime("%-d %B %Y"),
                "podcast_topic": self.state.community.metadata["title"],
                "topic_description": self.state.community.text,
                "brief": self.state.brief,
                "tool_messages": tool_messages,
            }
            response = await invoke_llm(agent, **args)
            response = response[0]
            tool_messages = []

            if response.tool_calls:
                tool_responses = await asyncio.to_thread(
                    response.call_tools_and_collect_as_message
                )
                tool_messages = [response, tool_responses]

                for r in tool_responses.content:
                    tool_response = AgentToolResponse.model_validate_json(
                        r.tool_result.text
                    )

                    if tool_response.function == "submit_brief":
                        step_active = False
            else:
                self.state.brief = response.text_only

        return self.state


class PodcastTagsAgent(BaseStudioAgent):
    @ell.complex(
        model="gpt-4o-mini",
        exempt_from_tracking=True,
        temperature=0,
        response_format=PodcastTags,
    )
    def assistant_tags_agent(self, **kwargs):
        return [
            ell.system(
                ASSISTANT_TAGS_PROMPT.format(
                    date=kwargs.get("date", datetime.now(UTC).strftime("%-d %B %Y")),
                    podcast_topic=kwargs.get("podcast_topic"),
                    topic_description=kwargs.get("topic_description"),
                )
            ),
            ell.user(
                f"The transcript of the podcast episode:\n\n"
                f"{kwargs.get('transcript', '')}"
            ),
        ]

    async def _run_agent(self, **kwargs) -> StudioState:
        args = {
            "date": datetime.now(UTC).strftime("%-d %B %Y"),
            "podcast_topic": self.state.community.metadata["title"],
            "topic_description": self.state.community.text,
            "transcript": self.state.conversation_text,
        }

        response = await invoke_llm(self.assistant_tags_agent, **args)
        response = response[0]
        self.state.metadata["title"] = response.parsed.title
        self.state.metadata["summary"] = response.parsed.summary
        self.state.metadata["tags"] = response.parsed.tags

        return self.state
