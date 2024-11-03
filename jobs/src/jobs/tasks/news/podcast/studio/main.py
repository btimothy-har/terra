from llama_index.core.workflow import Context
from llama_index.core.workflow import StartEvent
from llama_index.core.workflow import StopEvent
from llama_index.core.workflow import Workflow
from llama_index.core.workflow import step

from .agents import CoHostAgent
from .agents import ExpertAgent
from .agents import HostAgent
from .events import CoHostTurnEvent
from .events import ExpertTurnEvent
from .events import HostTurnEvent
from .events import StudioEndEvent
from .events import StudioState


class PodcastStudioFlow(Workflow):
    @step
    async def start_studio_session(self, ctx: Context, ev: StartEvent) -> HostTurnEvent:
        state = StudioState(
            community=ev.community,
            conversation=[],
            expert=None,
        )
        await ctx.set("state", state)
        return HostTurnEvent()

    @step
    async def host_turn(
        self, ctx: Context, ev: HostTurnEvent
    ) -> CoHostTurnEvent | ExpertTurnEvent | StudioEndEvent:
        state = await ctx.get("state")

        agent = HostAgent(state=state)
        new_state = await agent.invoke()

        await ctx.set("state", new_state)

        if not new_state.active:
            return StudioEndEvent()
        elif new_state.expert:
            return ExpertTurnEvent()
        else:
            return CoHostTurnEvent()

    @step
    async def cohost_turn(self, ctx: Context, ev: CoHostTurnEvent) -> HostTurnEvent:
        state = await ctx.get("state")

        agent = CoHostAgent(state=state)
        new_state = await agent.invoke()

        await ctx.set("state", new_state)
        return HostTurnEvent()

    @step
    async def expert_turn(self, ctx: Context, ev: ExpertTurnEvent) -> HostTurnEvent:
        state = await ctx.get("state")

        agent = ExpertAgent(state=state)
        new_state = await agent.invoke()

        await ctx.set("state", new_state)
        return HostTurnEvent()

    @step
    async def end_event(self, ctx: Context, ev: StudioEndEvent) -> StopEvent:
        state = await ctx.get("state")
        return StopEvent(result=state.conversation)
