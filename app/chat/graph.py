import asyncio
from functools import partial

import streamlit as st
from clients.ai import get_client
from langgraph.graph import END
from langgraph.graph import StateGraph

from .agents.archivist import ArchivistAgent
from .agents.engineer import ProgrammerAgent
from .agents.prompts import assistant as assistant_prompts
from .agents.research import ResearchAgent
from .agents.supervisor import Supervisor
from .states import ChatState


async def enter_loop(state: ChatState) -> ChatState:
    if state["use_multi_agent"]:
        state["loop_count"] = 0
        supervisor = Supervisor()
        state = await supervisor.start_loop(state)
    return state


def route_loop(state: ChatState) -> str:
    if state["completed"]:
        return "stop"
    if not state["use_multi_agent"]:
        return "stop"
    return "work"


async def route_to_agents(state: ChatState) -> ChatState:
    research_agent = ResearchAgent()
    programmer_agent = ProgrammerAgent()
    archivist_agent = ArchivistAgent()

    agent_tasks = [
        asyncio.create_task(research_agent.respond(state)),
        asyncio.create_task(programmer_agent.respond(state)),
        asyncio.create_task(archivist_agent.respond(state)),
    ]
    raw_resp = await asyncio.gather(*agent_tasks)

    state["workspace"].extend(raw_resp)
    return state


async def exit_loop(state: ChatState) -> ChatState:
    st.caption("Analyzing context...")
    state["loop_count"] += 1

    supervisor = Supervisor()
    state = await supervisor.evaluate_loop(state)
    return state


async def respond_to_user(state: ChatState) -> ChatState:
    agent = get_client(**state["agent"])

    user_messages = state["conversation"].copy()
    agent_messages = state["workspace"].copy()

    if agent_messages:
        sys_prompt = {
            "role": "system",
            "content": assistant_prompts.ASSISTANT_WITH_AGENT.format(
                context=agent_messages
            ),
        }
    else:
        sys_prompt = {
            "role": "system",
            "content": assistant_prompts.ASSISTANT_WITHOUT_AGENT,
        }

    messages = [sys_prompt] + user_messages
    state["output"] = partial(agent.stream, messages)
    return state


agent_flow = StateGraph(ChatState)
agent_flow.add_node("enter_loop", enter_loop)
agent_flow.add_node("route_to_agents", route_to_agents)
agent_flow.add_node("exit_loop", exit_loop)
agent_flow.add_node("respond_to_user", respond_to_user)

agent_flow.add_conditional_edges(
    "enter_loop", route_loop, {"stop": "respond_to_user", "work": "route_to_agents"}
)

agent_flow.add_edge("route_to_agents", "exit_loop")

agent_flow.add_conditional_edges(
    "exit_loop", route_loop, {"stop": "respond_to_user", "work": "route_to_agents"}
)

agent_flow.add_edge("respond_to_user", END)

agent_flow.set_entry_point("enter_loop")
CHAT_AGENT = agent_flow.compile()
