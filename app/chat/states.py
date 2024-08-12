from typing import Any
from typing import Optional
from typing import TypedDict

from langchain_core.messages import BaseMessage
from models.message import AppMessage


class AgentConfig(TypedDict):
    model: str
    temp: float
    max_tokens: int

class ChatState(TypedDict):
    agent: AgentConfig | dict
    conversation: list[AppMessage]
    workspace: list[BaseMessage] = []
    agent_logs: list[BaseMessage] = []
    completed: bool = False
    output: Any = None

class AgentAction(TypedDict):
    agent: str
    action: list[str] | str
    reason: Optional[list[str] | str] = None
    output: Optional[str] = None
