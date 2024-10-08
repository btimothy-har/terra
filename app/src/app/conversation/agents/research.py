import os

import streamlit as st
from conversation.states import AgentAction
from conversation.states import ChatState
from langchain_community.chat_models import ChatPerplexity

from .base import BaseAgent
from .prompts.research import RESARCH_AGENT_PROMPT


class ResearchAgent(BaseAgent):
    """
    Rachel, Research Assistant
    - Proficient in analyzing a variety of internet sources to identify important \
facts and information.
    - Primary role: use information available on the internet to provide accurate \
and unbiased information.
    - Believes in providing unbiased and accurate information, grounded in facts.
    """

    def __init__(self):
        super().__init__(
            name="Rachel",
            title="Research Assistant",
            sys_prompt=RESARCH_AGENT_PROMPT,
        )
        # TODO: Switch to OpenRouter when PPLX Credits are finished
        # self.model = ChatOpenAI(
        #     model="perplexity/llama-3.1-sonar-large-128k-online",
        #     temperature=0,
        #     timeout=30,
        #     api_key=os.getenv("OPENROUTER_API_KEY"),
        #     base_url=os.getenv("OPENROUTER_BASE_URL"),
        # )
        self.model = ChatPerplexity(
            temperature=0,
            pplx_api_key=os.getenv("PPLX_API_KEY"),
            model="llama-3.1-sonar-small-128k-online",
        )

    async def respond(self, state: ChatState):
        status_text = st.empty()
        status_text.caption(f"{self.title} is working...")

        supervisor_context = [
            m for m in state["workspace"].copy() if m["agent"] == "Supervisor"
        ]

        messages = [
            self.sys_prompt,
            {
                "role": "user",
                "content": supervisor_context[-1]["content"],
            },
        ]

        response = await self.model.ainvoke(messages)
        state["agent_logs"].append(
            AgentAction(agent=self.title, action="output", output=response.content)
        )

        status_text.caption(f"{self.title} is working... Done!")

        return {
            "role": "assistant",
            "name": self.name,
            "agent": self.title,
            "content": response.content,
        }
