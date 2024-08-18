import asyncio
from enum import Enum

import streamlit as st
from chat.states import AgentAction
from chat.states import ChatState
from langchain_core.tools import InjectedToolArg
from pydantic import BaseModel
from pydantic import Field
from typing_extensions import Annotated

from .archivist import ArchivistAgent
from .base import MODEL
from .base import BaseAgent
from .engineer import ProgrammerAgent
from .prompts import supervisor as prompts
from .research import ResearchAgent

AGENT_DESCRIPTION = (
    ResearchAgent.__doc__ + ArchivistAgent.__doc__ + ProgrammerAgent.__doc__
)


class InitialDecisionPaths(Enum):
    ASSIGN_TASKS_TO_AGENTS = "assign_tasks_to_agents"
    RESPOND_TO_USER = "respond_to_user"


class InitialDecision(BaseModel):
    decision: InitialDecisionPaths = Field(
        description="Your decision based on your assessment of the conversation."
    )
    reason: str = Field(description="Explain the reason for your decision.")


class EvaluationDecisionPaths(Enum):
    SUFFICIENT_INFORMATION = "sufficient_information"
    NEED_MORE_INFORMATION = "need_more_information"


class EvaluationDecision(BaseModel):
    decision: EvaluationDecisionPaths = Field(
        description="Your decision based on your assessment of the conversation."
    )
    reason: str = Field(description="Explain the reason for your decision.")


class Supervisor(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Alicia",
            title="Supervisor",
            sys_prompt="You are Alicia, an Agent Supervisor responsible for managing a team of agents.",
        )

    async def start_loop(self, state: ChatState):
        sys_prompt = {
            "role": "system",
            "content": prompts.SUPERVISOR_START_LOOP.format(agents=AGENT_DESCRIPTION),
        }

        assign_tasks = asyncio.create_task(self.assign_tasks(state))

        with_tools = self.model.with_structured_output(InitialDecision)
        ai_msg = await with_tools.ainvoke([sys_prompt] + state["conversation"].copy())

        if ai_msg.decision == InitialDecisionPaths.ASSIGN_TASKS_TO_AGENTS:
            response = await assign_tasks
            state["workspace"].append(
                {
                    "role": "assistant",
                    "name": "Alicia",
                    "title": "Supervisor",
                    "content": f"{response}",
                }
            )
            state["agent_logs"].append(
                AgentAction(
                    agent=self.title,
                    action=ai_msg.decision,
                    reason=ai_msg.reason,
                    output=response,
                )
            )
        elif ai_msg.decision == InitialDecisionPaths.RESPOND_TO_USER:
            state["completed"] = True
            state["agent_logs"].append(
                AgentAction(
                    agent=self.title, action=ai_msg.decision, reason=ai_msg.reason
                )
            )
        return state

    async def assign_tasks(self, state: Annotated[ChatState, InjectedToolArg]):
        """Assign tasks to your team of agents."""

        sys_prompt = {
            "role": "system",
            "content": prompts.SUPERVISOR_ASSIGN_TASKS.format(agents=AGENT_DESCRIPTION),
        }
        response = await MODEL.ainvoke([sys_prompt] + state["conversation"].copy())
        return response.content

    async def evaluate_loop(self, state: ChatState):
        sys_prompt = {
            "role": "system",
            "content": prompts.SUPERVISOR_EVALUATE_AGENTS.format(
                agents=AGENT_DESCRIPTION
            ),
        }

        if state["loop_count"] >= 2:
            state["completed"] = True
            state["agent_logs"].append(
                AgentAction(
                    agent=self.title,
                    action="terminate",
                    reason="The conversation has exceeded the maximum number of loops.",
                )
            )
        else:
            request_information = asyncio.create_task(
                self.request_more_information(state)
            )

            with_tools = self.model.with_structured_output(EvaluationDecision)
            ai_msg = await with_tools.ainvoke([sys_prompt] + state["workspace"].copy())

            if ai_msg.decision == EvaluationDecisionPaths.NEED_MORE_INFORMATION:
                st.caption("Looking for more information...")
                response = await request_information
                state["workspace"].append(
                    {
                        "role": "assistant",
                        "name": "Alicia",
                        "title": "Supervisor",
                        "content": f"{response}",
                    }
                )
                state["agent_logs"].append(
                    AgentAction(
                        agent=self.title,
                        action=ai_msg.decision,
                        reason=ai_msg.reason,
                        output=response,
                    )
                )

            elif ai_msg.decision == EvaluationDecisionPaths.SUFFICIENT_INFORMATION:
                state["completed"] = True
                state["agent_logs"].append(
                    AgentAction(
                        agent=self.title, action=ai_msg.decision, reason=ai_msg.reason
                    )
                )

        return state

    async def request_more_information(
        self, state: Annotated[ChatState, InjectedToolArg]
    ):
        """
        The information from your agents is inadequate.
        """
        sys_prompt = {
            "role": "system",
            "content": prompts.SUPERVISOR_FEEDBACK.format(agents=AGENT_DESCRIPTION),
        }

        response = await MODEL.ainvoke([sys_prompt] + state["workspace"].copy())
        return response.content
