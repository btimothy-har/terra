from datetime import UTC
from datetime import datetime

import ell

from ..events import StudioState
from .base import BaseStudioAgent
from .base import invoke_llm
from .prompts import COHOST_PROMPT


class CoHostAgent(BaseStudioAgent):
    @ell.complex(
        model="google/gemini-flash-1.5-8b",
        exempt_from_tracking=True,
        temperature=1,
    )
    def cohost_agent(self, **kwargs):
        return [
            ell.system(
                COHOST_PROMPT.format(
                    date=kwargs.get("date", datetime.now(UTC).strftime("%-d %B %Y")),
                    podcast_topic=kwargs.get("podcast_topic"),
                    topic_description=kwargs.get("brief"),
                )
            ),
            ell.user(f"The podcast so far: {kwargs.get('transcript', '')}"),
        ]

    async def _run_agent(self, **kwargs) -> StudioState:
        args = {
            "date": datetime.now(UTC).strftime("%-d %B %Y"),
            "podcast_topic": self.state.community.metadata["title"],
            "brief": self.state.brief,
            "transcript": self.state.conversation_text,
        }

        cohost_response = await invoke_llm(self.cohost_agent, **args)
        cohost_response = cohost_response[0]

        self.state.conversation.append(
            {"role": "cohost", "content": cohost_response.text}
        )

        return self.state
