import asyncio
from abc import ABC
from abc import abstractmethod

from pydantic import BaseModel

from ..events import StudioState


class BaseStudioAgent(BaseModel, ABC):
    state: StudioState

    @abstractmethod
    def _run_agent(self, **kwargs):
        pass

    async def invoke(self, **kwargs):
        return await asyncio.to_thread(self._run_agent, **kwargs)
