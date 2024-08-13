import asyncio
from enum import Enum

import streamlit as st
from chat.states import AgentAction
from chat.states import ChatState
from langchain_core.tools import InjectedToolArg
from pydantic import BaseModel
from pydantic import Field
from typing_extensions import Annotated

from .base import MODEL
from .base import BaseAgent


class InitialDecisionPaths(Enum):
    ASSIGN_TASKS_TO_AGENTS = "assign_tasks_to_agents"
    RESPOND_TO_USER = "respond_to_user"

class InitialDecision(BaseModel):
    decision: InitialDecisionPaths = Field(description="Your decision based on your assessment of the conversation.")
    reason: str = Field(description="Explain the reason for your decision.")

class EvaluationDecisionPaths(Enum):
    SUFFICIENT_INFORMATION = "sufficient_information"
    NEED_MORE_INFORMATION = "need_more_information"

class EvaluationDecision(BaseModel):
    decision: EvaluationDecisionPaths = Field(description="Your decision based on your assessment of the conversation.")
    reason: str = Field(description="Explain the reason for your decision.")


class Supervisor(BaseAgent):
    def __init__(self):
        super().__init__(
            name = "Alicia",
            title = "Supervisor",
            sys_prompt = "You are Alicia, an Agent Supervisor responsible for managing a team of agents.",
            )

    async def start_loop(self, state:ChatState):
        sys_prompt = {
            "role": "system",
            "content":
            """
            You are Alicia, an Agent Supervisor responsible for managing a team of agents.

            You DO NOT have sufficient knowledge or expertise to respond to the user. \
            However, you may greet or acknowledge the user without providing any information.

            Given the conversation that your Assistant Agent has had with the user, \
            decide your next steps to adequately respond to the conversation:
            - assign_tasks_to_agents to prepare any information you need to continue the conversation with the user; OR
            - respond_to_user if you do not need any information from your agents.
            """
        }

        assign_tasks = asyncio.create_task(Supervisor.assign_tasks(state))

        with_tools = self.model.with_structured_output(InitialDecision)
        ai_msg = await with_tools.ainvoke(
            [sys_prompt] + state["conversation"].copy()
            )

        if ai_msg.decision == InitialDecisionPaths.ASSIGN_TASKS_TO_AGENTS:
            response = await assign_tasks
            state["workspace"].append({
                "role": "assistant",
                "name": "Alicia",
                "title": "Supervisor",
                "content": f"{response}"
                })
            state["agent_logs"].append(
                AgentAction(
                    agent=self.title,
                    action=ai_msg.decision,
                    reason=ai_msg.reason,
                    output=response
                    )
                )
        elif ai_msg.decision == InitialDecisionPaths.RESPOND_TO_USER:
            state["completed"] = True
            state["agent_logs"].append(
                AgentAction(
                    agent=self.title,
                    action=ai_msg.decision,
                    reason=ai_msg.reason
                    )
                )
        return state

    async def evaluate_loop(self, state:ChatState):
        sys_prompt = {
            "role": "system",
            "content": """
            You are Alicia, an Agent Supervisor responsible for managing a team of agents."

            Your agents have completed their assigned tasks and provided their inputs.

            The Agents under your care are:
            1. Rachel, Research Assistant
            - She is capable of researching topics on the internet.
            - Her primary role is to gather information from the internet and prepare a report of her findings.
            - Limited to providing unbiased and accurate information, grounded in facts that she herself has found.

            2. Edmund, Software Engineer
            - Proficient in programming languages, with a focus on Python and Ruby.
            - Capable of using code to solve problems, with access to a Python code execution environment.
            - Limited to providing advice on existing code and executing code.

            Taking into account the context description set by you, determine if \
            your agents have sufficiently met the requirements or \
            if you require additional information from them.

            Use the tools provided to you to make your decision.

            When making your decision, consider that:
            - The user is not part of the conversation and cannot provide any additional information.
            - Your evaluation should be focused on whether there is sufficient information to respond to the user.
            - Your agents are unable to perform tasks outside their proficient skillset.
            """
            }

        request_information = asyncio.create_task(Supervisor.request_more_information(state))

        with_tools = self.model.with_structured_output(EvaluationDecision)
        ai_msg = await with_tools.ainvoke(
            [sys_prompt] + state["workspace"].copy()
            )

        if ai_msg.decision == EvaluationDecisionPaths.NEED_MORE_INFORMATION:
            st.caption("Looking for more information...")
            response = await request_information
            state["workspace"].append({
                "role": "assistant",
                "name": "Alicia",
                "title": "Supervisor",
                "content": f"{response}"
                })
            state["agent_logs"].append(
                AgentAction(
                    agent=self.title,
                    action=ai_msg.decision,
                    reason=ai_msg.reason,
                    output=response
                    )
                )

        elif ai_msg.decision == EvaluationDecisionPaths.SUFFICIENT_INFORMATION:
            state["completed"] = True
            state["agent_logs"].append(
                AgentAction(
                    agent=self.title,
                    action=ai_msg.decision,
                    reason=ai_msg.reason
                    )
                )

        return state

    @staticmethod
    async def assign_tasks(state: Annotated[ChatState, InjectedToolArg]):
        """Assign tasks to your team of agents."""

        sys_prompt = {
            "role": "system",
            "content": """
            You are Alicia, an Agent Supervisor responsible for managing a team of agents. \
            You DO NOT have sufficient knowledge or expertise to respond to the user.

            The Agents under your care are:
            1. Rachel, Research Assistant
            - She is capable of researching topics on the internet.
            - Her primary role is to gather information from the internet and prepare a report of her findings.
            - Limited to providing unbiased and accurate information, grounded in facts that she herself has found.

            2. Edmund, Software Engineer
            - Proficient in programming languages, with a focus on Python and Ruby.
            - Capable of using code to solve problems, with access to a Python code execution environment.
            - Limited to providing advice on existing code and executing code.

            Given the conversation that your Assistant Agent has had with the user, \
            set the context for your other agents to prepare any information might be needed \
            to continue the conversation.

            In the context:
            - Establish a desired outcome for your agents.
            - Provide any relevant information that the user provided that may be useful.
            - Describe the work that your agents should perform, taking into consideration their capabilities. \
            If there is no work for them to do, you may choose to assign nothing.
            - DO NOT provide any suggestions or guidance on how to complete the task.
            """
           }
        response = await MODEL.ainvoke(
            [sys_prompt] + state["conversation"].copy()
            )
        return response.content

    @staticmethod
    async def request_more_information(state: Annotated[ChatState, InjectedToolArg]):
        """
        The information from your agents is inadequate.
        """
        sys_prompt = {
            "role": "system",
            "content": """
            You are Alicia, an Agent Supervisor responsible for managing a team of agents."

            Your agents have completed their assigned tasks and provided their inputs. \
            You are now to evaluate and provide feedback on their work.

            The feedback should:
            - Be constructive, providing guidance on how they can improve their work.
            - Be clear and concise, highlighting the key areas that need improvement.
            - Identify any areas that need further clarification or additional information.
            """
            }
        response = await MODEL.ainvoke(
            [sys_prompt] + state["workspace"].copy()
            )
        return response.content
