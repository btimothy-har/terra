import os

from chat.states import AgentAction
from chat.states import ChatState
from langchain_community.chat_models import ChatPerplexity
from langchain_core.tools import tool
from typing_extensions import Annotated

from .base import BaseAgent

PPLX = ChatPerplexity(
    temperature=0,
    pplx_api_key=os.getenv("PPLX_API_KEY"),
    model="llama-3.1-sonar-small-128k-online"
    )

class ResearchAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name = "Rachel",
            title = "Research Assistant",
            sys_prompt = """
            You are Rachel, a Research Assistant working as part of a team of agents.

            - You are proficient in conducting research and presenting information in a clear and concise manner.
            - You have access to a research tool that allows you to gather information from the internet.
            - You strongly believe in providing unbiased and accurate information, grounded in facts that you yourself \
            have found.

            Given the assigned context and on-going conversation with other agents, your task is to \
            gather information from the internet about the context and prepare a report of your findings.

            You will not be allowed to repeat searches. If you need to make multiple searches, \
            provide multiple search queries instead.

            The report should be concise and informative, providing a summary of the key points and \
            relevant details in an unbiased manner. Include links or resources where relevant to the content.
            """,
            tools = [ResearchAgent.research_topic]
            )
        self.model = PPLX

    async def respond(self, state:ChatState):
        messages = [
            self.sys_prompt,
            {
                "role": "user",
                "content": f"Prepare a report based on this on-going conversation: {state["workspace"].copy()}"
            }]

        response = await self.model.ainvoke(messages)
        state["agent_logs"].append(
            AgentAction(
                agent=self.title,
                action="output",
                output=response.content
                )
            )
        return {
            "role": "assistant",
            "name": self.name,
            "title": self.title,
            "content": response.content
        }

    @tool
    @staticmethod
    def research_topic(
        topic:Annotated[str, "The topic to research, best phrased as a question."],
        reason:Annotated[str, "Explain the reason for choosing this tool."]
        ) -> str:
        """Research a topic on the internet from various sources."""

        messages = [
            {
            "role": "system",
            "content": """
            You are Rachel, a Research Assistant working as part of a team of agents.

            Your primary role is to gather information from the internet about the topic assigned and \
            prepare a report of your findings.

            The report should be concise and informative, providing a summary of the key points and \
            relevant details in an unbiased manner.
            """
            },
            {
                "role": "user",
                "content": topic
                }
            ]

        response = PPLX.invoke(messages)
        return response.content
