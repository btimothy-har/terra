from datetime import UTC
from datetime import datetime

import ell

from ..events import StudioState
from .base import BaseStudioAgent
from .prompts import COHOST_PROMPT


class CoHostAgent(BaseStudioAgent):
    @ell.complex(
        model="gpt-4o-mini",
        temperature=1,
    )
    def agent(self):
        return [
            ell.system(
                COHOST_PROMPT.format(
                    date=datetime.now(UTC).strftime("%-d %B %Y"),
                    podcast_topic=self.state.community.metadata["title"],
                    topic_description=self.state.community.text,
                )
            ),
            ell.user(f"The podcast so far: {self.state.conversation}"),
        ]

    def _run_agent(self, **kwargs) -> StudioState:
        cohost_response = self.agent(**kwargs)

        self.state.conversation.append(
            {"role": "cohost", "content": cohost_response.text}
        )

        return self.state
