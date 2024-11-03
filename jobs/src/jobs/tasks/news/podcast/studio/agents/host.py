from datetime import UTC
from datetime import datetime

import ell

from ..events import StudioState
from .base import BaseStudioAgent
from .prompts import HOST_PROMPT
from .tools import AgentToolResponse
from .tools import end_expert_interview
from .tools import end_podcast
from .tools import invite_expert
from .tools import search_context
from .tools import speak_in_podcast


class HostAgent(BaseStudioAgent):
    def _build_agent(self):
        base_tools = [search_context, end_podcast, speak_in_podcast]

        if self.state.expert:
            base_tools.append(end_expert_interview)
        else:
            base_tools.append(invite_expert)

        @ell.complex(
            model="gpt-4o-mini",
            temperature=1,
            tools=base_tools,
            tool_choice="required",
        )
        def host_agent(**kwargs):
            return [
                ell.system(
                    HOST_PROMPT.format(
                        date=datetime.now(UTC).strftime("%-d %B %Y"),
                        podcast_topic=self.state.community.metadata["title"],
                        topic_description=self.state.community.text,
                    )
                ),
                ell.user(f"The podcast so far: {self.state.conversation}"),
            ] + kwargs.get("tool_messages", [])

        return host_agent

    def _run_agent(self, **kwargs) -> StudioState:
        step_active = True
        agent = self._build_agent()
        tool_messages = []

        while step_active:
            host_response = agent(tool_messages=tool_messages, **kwargs)

            tool_responses = host_response.call_tools_and_collect_as_message()
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
