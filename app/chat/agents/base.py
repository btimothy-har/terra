import asyncio
from typing import Optional

import streamlit as st
from chat.states import AgentAction
from chat.states import ChatState
from clients.ai import get_client
from langchain_core.tools import tool
from typing_extensions import Annotated

MODEL = get_client(model="gpt-4o-mini")

@tool
async def do_nothing(
    reason:Annotated[str, "Explain the reason for choosing this tool."]
    ):
    """Do nothing. Use this when there is no task required from you."""
    return

@tool
async def ask_question(
    question:Annotated[str, "The question you want ask the other Agents."],
    reason:Annotated[str, "Explain the reason for choosing this tool."]
    ):
    """Ask a question to other Agents. Use this if you need to get clarification on the task requested of you."""
    return

@tool
async def reply_agents(
    message:Annotated[str, "The message to send to the other Agents."],
    reason:Annotated[str, "Explain the reason for choosing this tool."]
    ):
    """Reply to other Agents. Use this to send a message to the other Agents."""
    return

class BaseAgent:
    def __init__(self, name:str, title:str, sys_prompt:str, tools:Optional[list]=None):
        tools = tools or []

        self.name = name
        self.title = title
        self.sys_prompt = {
            "role": "system",
            "content": sys_prompt
            }

        self.tools = {
            "do_nothing": do_nothing,
            "ask_question": ask_question,
            "reply_agents": reply_agents
            }
        self.agent_tools = {tool.func.__name__: tool for tool in tools}
        self.tools.update(self.agent_tools)
        self.model = MODEL

    async def respond(self, state:ChatState):
        messages = [self.sys_prompt] + state["workspace"].copy()

        with_tools = self.model.bind_tools(
            list(self.tools.values()),
            tool_choice="any")
        ai_msg = await with_tools.ainvoke(messages)

        messages.append(ai_msg)
        tool_calls = ai_msg.tool_calls

        if "do_nothing" in [ai_action["name"] for ai_action in tool_calls]:
            state["agent_logs"].append(
                AgentAction(
                    agent=self.title,
                    action="do_nothing",
                    reason=[ai_action["args"]["reason"] for ai_action in tool_calls
                        if ai_action["name"] == "do_nothing"][0]
                        )
                    )

        elif "ask_question" in [ai_action["name"] for ai_action in tool_calls]:
            question = ""
            for ai_action in tool_calls:
                if ai_action["name"] == "ask_question":
                    question += ai_action["args"]["question"]
                    state["agent_logs"].append(
                        AgentAction(
                            agent=self.title,
                            action=ai_action["name"],
                            reason=ai_action["args"]["reason"],
                            output=ai_action["args"]["question"]
                            )
                        )
            ai_msg.content = question

        elif "reply_agents" in [ai_action["name"] for ai_action in tool_calls]:
            reply = ""
            for ai_action in tool_calls:
                if ai_action["name"] == "reply_agents":
                    reply += ai_action["args"]["message"]
                    state["agent_logs"].append(
                        AgentAction(
                            agent=self.title,
                            action=ai_action["name"],
                            reason=ai_action["args"]["reason"],
                            output=ai_action["args"]["message"]
                            )
                        )
            ai_msg.content = reply

        else:
            st.caption(f"{self.title} is working...")

            tool_funcs = [(ai_action, self.tools[ai_action["name"]]) for ai_action in tool_calls
                if ai_action["name"] in self.agent_tools.keys()
                ]
            tool_resp = await asyncio.gather(*[tool_func[1].ainvoke(tool_func[0]) for tool_func in tool_funcs])
            messages.extend(tool_resp)

            for i, res in enumerate(tool_resp):
                state["agent_logs"].append(
                    AgentAction(
                        agent=self.title,
                        action=tool_funcs[i][0]["name"],
                        reason=tool_funcs[i][0]["args"]["reason"],
                        output=res.content
                        )
                    )

            ai_msg = await self.model.ainvoke(messages)
            state["agent_logs"].append(
                AgentAction(
                    agent=self.title,
                    action="output",
                    output=ai_msg.content
                    )
                )

        return {
            "role": "assistant",
            "name": self.name,
            "title": self.title,
            "content": ai_msg.content
        }