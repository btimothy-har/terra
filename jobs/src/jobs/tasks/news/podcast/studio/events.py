from llama_index.core.schema import BaseNode
from llama_index.core.workflow import Event
from pydantic import BaseModel
from pydantic import Field


class StudioState(BaseModel):
    community: BaseNode
    conversation: list[dict] = Field(default_factory=list)
    expert: str | None = Field(default=None)
    active: bool = Field(default=True)
    brief: str | None = Field(default=None)
    metadata: dict = Field(default_factory=dict)

    @property
    def conversation_text(self) -> str:
        return "\n\n".join(
            [f"{c['role'].upper()}: {c['content']}" for c in self.conversation]
        )


class HostTurnEvent(Event):
    pass


class CoHostTurnEvent(Event):
    pass


class ExpertTurnEvent(Event):
    pass


class StudioEndEvent(Event):
    pass
