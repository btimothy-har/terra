from llama_index.core.workflow import Context
from llama_index.core.workflow import StartEvent
from llama_index.core.workflow import StopEvent
from llama_index.core.workflow import Workflow
from llama_index.core.workflow import step

from .agents import CoHostAgent
from .agents import ExpertAgent
from .agents import HostAgent
from .agents import PodcastBriefAgent
from .agents import PodcastTagsAgent
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
            metadata={
                "geos": ev.source_countries,
                "node_ids": ev.node_ids,
                "article_ids": ev.article_ids,
            },
        )
        agent = PodcastBriefAgent(state=state)
        new_state = await agent.invoke()

        await ctx.set("state", new_state)
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

        agent = PodcastTagsAgent(state=state)
        new_state = await agent.invoke()

        podcast = {
            "title": new_state.metadata["title"],
            "summary": new_state.metadata["summary"],
            "geos": new_state.metadata["geos"],
            "tags": new_state.metadata["tags"],
            "transcript": new_state.conversation,
            "articles": new_state.metadata["article_ids"],
        }
        return StopEvent(result=podcast)
