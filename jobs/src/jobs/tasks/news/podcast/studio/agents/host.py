import asyncio
from datetime import UTC
from datetime import datetime

import ell

from ..events import StudioState
from .base import BaseStudioAgent
from .base import invoke_llm
from .prompts import HOST_PROMPT
from .tools import AgentToolResponse
from .tools import end_expert_interview
from .tools import end_podcast
from .tools import invite_expert
from .tools import speak_in_podcast


class HostAgent(BaseStudioAgent):
    def _build_agent(self):
        context_tool = self.build_context_tool()
        base_tools = [context_tool, end_podcast, speak_in_podcast]

        if self.state.expert:
            base_tools.append(end_expert_interview)
        else:
            base_tools.append(invite_expert)

        @ell.complex(
            model="gpt-4o-mini",
            tools=base_tools,
            exempt_from_tracking=True,
            temperature=1,
            tool_choice="required",
        )
        def host_agent(**kwargs):
            return [
                ell.system(
                    HOST_PROMPT.format(
                        date=kwargs.get(
                            "date", datetime.now(UTC).strftime("%-d %B %Y")
                        ),
                        podcast_topic=kwargs.get("podcast_topic"),
                        topic_description=kwargs.get("brief"),
                    )
                ),
                ell.user(f"The podcast so far: {kwargs.get('transcript', '')}"),
            ] + kwargs.get("tool_messages", [])

        return host_agent

    async def _run_agent(self, **kwargs) -> StudioState:
        step_active = True
        agent = self._build_agent()
        tool_messages = []

        while step_active:
            args = {
                "date": datetime.now(UTC).strftime("%-d %B %Y"),
                "podcast_topic": self.state.community.metadata["title"],
                "brief": self.state.brief,
                "transcript": self.state.conversation_text,
                "tool_messages": tool_messages,
            }
            host_response = await invoke_llm(agent, **args)
            host_response = host_response[0]
            tool_messages = []

            tool_responses = await asyncio.to_thread(
                host_response.call_tools_and_collect_as_message
            )
            tool_messages = [host_response, tool_responses]

            for r in tool_responses.content:
                tool_response = AgentToolResponse.model_validate_json(
                    r.tool_result.text
                )

                if tool_response.function == "speak_in_podcast":
                    self.state.conversation.append(
                        {"role": "host", "content": tool_response.response}
                    )
                    step_active = False
                elif tool_response.function == "invite_expert":
                    self.state.expert = tool_response.response
                elif tool_response.function == "end_expert_interview":
                    self.state.expert = None
                elif tool_response.function == "end_podcast":
                    self.state.active = False

        return self.state
