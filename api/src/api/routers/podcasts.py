import asyncio
import hashlib
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from api.data.schemas import PodcastSchema
from api.models import PodcastEpisode
from api.utils import database_session

router = APIRouter(tags=["podcasts"], prefix="/podcasts")

DatabaseSession = Annotated[AsyncSession, Depends(database_session)]


class PodcastFilter(BaseModel):
    from_date: datetime | None = None
    to_date: datetime | None = None
    tags: list[str] | None = None
    geos: list[str] | None = None

    def construct_filters(self):
        filters = []
        if self.from_date:
            filters.append(func.date(PodcastSchema.date) >= self.from_date)
        if self.to_date:
            filters.append(func.date(PodcastSchema.date) <= self.to_date)
        if self.tags:
            filters.append(PodcastSchema.tags.overlap(self.tags))
        if self.geos:
            filters.append(PodcastSchema.geos.overlap(self.geos))
        return filters


@router.put(
    "/new",
    summary="Creates a new podcast episode.",
)
async def put_new_podcast(episode: PodcastEpisode, db: DatabaseSession):
    episode.episode_id = hashlib.md5(
        f"{episode.date}{episode.title}".encode()
    ).hexdigest()

    stmt = (
        pg_insert(PodcastSchema)
        .values(**episode.model_dump(exclude={"episode_num"}))
        .on_conflict_do_nothing(index_elements=["episode_id"])
    )

    await db.execute(stmt)
    await db.commit()


@router.get(
    "/tags",
    summary="Fetch all podcast tags.",
)
async def get_podcast_tags(db: DatabaseSession) -> list[str]:
    unnested_tags = func.unnest(PodcastSchema.tags)
    query = select(unnested_tags).distinct().order_by(unnested_tags)

    result = await db.execute(query)
    tags = result.scalars().all()

    return tags


@router.get(
    "/geos",
    summary="Fetch all podcast geos.",
)
async def get_podcast_geos(db: DatabaseSession) -> list[str]:
    unnested_geos = func.unnest(PodcastSchema.geos)
    query = select(unnested_geos).distinct().order_by(unnested_geos)

    result = await db.execute(query)
    geos = result.scalars().all()

    return geos


@router.get(
    "/{episode_id}",
    summary="Fetch a podcast episode by its ID.",
)
async def get_podcast_by_id(episode_id: str, db: DatabaseSession) -> PodcastEpisode:
    query = select(PodcastSchema).where(PodcastSchema.episode_id == episode_id)

    result = await db.execute(query)
    podcast = result.scalar_one_or_none()

    if podcast is None:
        raise HTTPException(status_code=404, detail="Podcast not found.")

    return PodcastEpisode.model_validate(podcast, from_attributes=True)


@router.get(
    "/{episode_id}/audio",
    summary="Fetch the audio of a podcast episode.",
    response_class=Response,
)
async def get_podcast_audio(
    db: DatabaseSession, episode_id: str, create_if_missing: bool = True
) -> Response:
    podcast = await get_podcast_by_id(episode_id, db)
    audio_data = await asyncio.to_thread(podcast.create_audio, create_if_missing)

    if audio_data:
        return Response(audio_data.read(), media_type="audio/mp3")
    else:
        raise HTTPException(status_code=204, detail="Audio file not found.")


@router.post(
    "/filter",
    response_model=list[PodcastEpisode],
    summary="Filters podcasts by date, tags, and geos.",
)
async def filter_podcasts(
    input_filter: PodcastFilter,
    db: DatabaseSession,
) -> list[PodcastEpisode]:
    filters = input_filter.construct_filters()
    query = select(PodcastSchema).where(*filters)

    result = await db.execute(query)
    podcasts = result.scalars().all()

    return [
        PodcastEpisode.model_validate(podcast, from_attributes=True)
        for podcast in podcasts
    ]
