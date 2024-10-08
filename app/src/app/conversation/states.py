from typing import Any
from typing import Optional
from typing import TypedDict

from langchain_core.messages import BaseMessage
from models.message import ThreadMessage


class AgentConfig(TypedDict):
    model: str
    temp: float


class ChatState(TypedDict):
    loop_count: int = 0
    agent: AgentConfig | dict
    conversation: list[ThreadMessage]
    workspace: list[BaseMessage] = []
    agent_logs: list[BaseMessage] = []
    use_multi_agent: bool = True
    completed: bool = False
    output: Any = None


class AgentAction(TypedDict):
    agent: str
    action: list[str] | str
    reason: Optional[list[str] | str] = None
    output: Optional[str] = None
