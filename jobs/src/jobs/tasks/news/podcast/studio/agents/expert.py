import asyncio
from datetime import UTC
from datetime import datetime

import ell

from .base import BaseStudioAgent
from .base import invoke_llm
from .prompts import EXPERT_PROMPT
from .tools import AgentToolResponse
from .tools import search_knowledge_base
from .tools import speak_in_podcast


class ExpertAgent(BaseStudioAgent):
    @ell.complex(
        model="gpt-4o-mini",
        tools=[search_knowledge_base, speak_in_podcast],
        exempt_from_tracking=True,
        temperature=1,
        tool_choice="required",
    )
    def expert_agent(self, **kwargs):
        return [
            ell.system(
                EXPERT_PROMPT.format(
                    date=kwargs.get("date", datetime.now(UTC).strftime("%-d %B %Y")),
                    expert_profile=kwargs.get("expert_profile"),
                    podcast_topic=kwargs.get("podcast_topic"),
                    topic_description=kwargs.get("brief"),
                )
            ),
            ell.user(f"The podcast so far: {kwargs.get('transcript', '')}"),
        ] + kwargs.get("tool_messages", [])

    async def _run_agent(self, **kwargs):
        step_active = True
        tool_messages = []

        while step_active:
            args = {
                "date": datetime.now(UTC).strftime("%-d %B %Y"),
                "expert_profile": self.state.expert,
                "podcast_topic": self.state.community.metadata["title"],
                "brief": self.state.brief,
                "transcript": self.state.conversation_text,
                "tool_messages": tool_messages,
            }
            expert_response = await invoke_llm(self.expert_agent, **args)
            expert_response = expert_response[0]
            tool_messages = []

            tool_responses = await asyncio.to_thread(
                expert_response.call_tools_and_collect_as_message
            )
            tool_messages = [expert_response, tool_responses]

            for r in tool_responses.content:
                tool_response = AgentToolResponse.model_validate_json(
                    r.tool_result.text
                )

                if tool_response.function == "speak_in_podcast":
                    self.state.conversation.append(
                        {"role": "expert", "content": tool_response.response}
                    )
                    step_active = False

        return self.state
