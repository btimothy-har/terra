from io import BytesIO

import requests
import streamlit as st
from config import API_ENDPOINT
from models import PodcastEpisode


def refresh_podcasts():
    from_date = st.session_state.get("pc_podcast_filter_from")
    to_date = st.session_state.get("pc_podcast_filter_to")
    tags = st.session_state.get("pc_podcast_filter_tags")
    geos = st.session_state.get("pc_podcast_filter_geos")

    if from_date > to_date:
        st.error("From date must be less than to date.")
        st.stop()

    podcasts = PodcastEpisode.search(from_date, to_date, tags, geos)

    st.session_state.pc_podcast_list = podcasts
    return podcasts


def set_podcast_audio(episode_id: str):
    st.session_state.pc_podcast_listen = episode_id


@st.cache_resource(ttl="1 day", show_spinner=False)
def get_podcast_tags() -> list[str]:
    get_request = requests.get(
        url=f"{API_ENDPOINT}/podcasts/tags",
    )
    get_request.raise_for_status()
    return get_request.json()


@st.cache_resource(ttl="1 day", show_spinner=False)
def get_podcast_geos() -> list[str]:
    get_request = requests.get(
        url=f"{API_ENDPOINT}/podcasts/geos",
    )
    get_request.raise_for_status()
    return get_request.json()


@st.cache_resource(show_spinner=False, validate=lambda x: x is not None)
def get_podcast_audio(episode_id: str, _create_if_missing: bool = True) -> bytes | None:
    get_request = requests.get(
        url=f"{API_ENDPOINT}/podcasts/{episode_id}/audio",
        params={"create_if_missing": _create_if_missing},
    )
    get_request.raise_for_status()

    if get_request.status_code == 204:
        return None

    audio_bytes = BytesIO(get_request.content)
    return audio_bytes
