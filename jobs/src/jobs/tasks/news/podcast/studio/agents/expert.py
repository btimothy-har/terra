from datetime import UTC
from datetime import datetime

import ell

from .base import BaseStudioAgent
from .prompts import EXPERT_PROMPT
from .tools import AgentToolResponse
from .tools import search_knowledge_base
from .tools import speak_in_podcast


class ExpertAgent(BaseStudioAgent):
    @ell.complex(
        model="gpt-4o-mini",
        temperature=1,
        tools=[search_knowledge_base, speak_in_podcast],
        tool_choice="required",
    )
    def agent(self, **kwargs):
        return [
            ell.system(
                EXPERT_PROMPT.format(
                    date=datetime.now(UTC).strftime("%-d %B %Y"),
                    podcast_topic=self.state.community.metadata["title"],
                    topic_description=self.state.community.text,
                    expert_profile=self.state.expert,
                )
            ),
            ell.user(f"The podcast so far: {self.state.conversation}"),
        ] + kwargs.get("tool_messages", [])

    def _run_agent(self, **kwargs):
        step_active = True
        tool_messages = []

        while step_active:
            expert_response = self.agent(tool_messages=tool_messages, **kwargs)

            tool_responses = expert_response.call_tools_and_collect_as_message()
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
