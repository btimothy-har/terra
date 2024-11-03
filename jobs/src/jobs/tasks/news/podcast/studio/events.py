from llama_index.core.schema import BaseNode
from llama_index.core.workflow import Event
from pydantic import BaseModel


class StudioState(BaseModel):
    active: bool = True
    community: BaseNode
    conversation: list[dict]
    expert: str | None


class HostTurnEvent(Event):
    pass


class CoHostTurnEvent(Event):
    pass


class ExpertTurnEvent(Event):
    pass


class StudioEndEvent(Event):
    pass
