import asyncio

import streamlit as st
from clients.ai import get_client
from langgraph.graph import END
from langgraph.graph import StateGraph

from .agents.programmer import ProgrammerAgent
from .agents.research import ResearchAgent
from .agents.supervisor import Supervisor
from .states import ChatState


async def enter_loop(state:ChatState) -> ChatState:
    supervisor = Supervisor()
    state = await supervisor.start_loop(state)
    return state

def route_loop(state:ChatState) -> str:
    if state["completed"]:
        return "stop"
    return "work"

async def route_to_agents(state:ChatState) -> ChatState:
    research_agent = ResearchAgent()
    programmer_agent = ProgrammerAgent()

    raw_resp = await asyncio.gather(
        research_agent.respond(state),
        programmer_agent.respond(state)
        )

    state["workspace"].extend(raw_resp)
    return state

async def exit_loop(state:ChatState) -> ChatState:
    st.caption("Analyzing context...")

    supervisor = Supervisor()
    state = await supervisor.evaluate_loop(state)
    return state

async def respond_to_user(state:ChatState) -> ChatState:
    agent = get_client(**state["agent"])

    messages = [{
        "role": "system",
        "content": "You are Anthony, a helpful AI Personal Assistant. \
            Be proactively helpful as much as possible, but do not provide any information that does not exist \
            in the context."
        }]

    user_messages = state["conversation"].copy()
    agent_messages = state["workspace"].copy()

    messages.extend(user_messages)

    if agent_messages:
        messages[0]['content'] += f"""
            Your support team has prepared some useful background information for you as reference \
            to use in your response.

            Your response should:
            - Be conversational and casual in nature, continuing the existing conversation with the user.
            - Include any relevant resources that may have been surfaced from agents.
            - Not mention the agents or their work directly.
            - Be as comprehensive as possible. You should aim to be as proactive as possible in your response.

            ### SUPPORTING INFORMATION
            {agent_messages}
            """

    state["output"] = agent.stream(messages)
    return state

agent_flow = StateGraph(ChatState)
agent_flow.add_node("enter_loop", enter_loop)
agent_flow.add_node("route_to_agents", route_to_agents)
agent_flow.add_node("exit_loop", exit_loop)
agent_flow.add_node("respond_to_user", respond_to_user)

agent_flow.add_conditional_edges(
    "enter_loop",
    route_loop,
    {
        "stop": "respond_to_user",
        "work": "route_to_agents"
        }
    )

agent_flow.add_edge("route_to_agents", "exit_loop")

agent_flow.add_conditional_edges(
    "exit_loop",
    route_loop,
    {
        "stop": "respond_to_user",
        "work": "route_to_agents"
        }
    )

agent_flow.add_edge("respond_to_user", END)

agent_flow.set_entry_point("enter_loop")
CHAT_AGENT = agent_flow.compile()
