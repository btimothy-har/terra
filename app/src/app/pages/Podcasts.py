from datetime import UTC
from datetime import datetime
from datetime import timedelta
from functools import partial

import streamlit as st
from dialogs.podcast_audio import download_podcast_audio
from utils.main import get_clean_render
from utils.main import set_session_cookie
from utils.main import set_session_user
from utils.podcast import get_podcast_audio
from utils.podcast import get_podcast_geos
from utils.podcast import get_podcast_tags
from utils.podcast import refresh_podcasts
from utils.podcast import set_podcast_audio

st.set_page_config(
    page_title="terra Podcasts",
    page_icon=":coffee:",
    layout="centered",
    initial_sidebar_state="auto",
)

try:
    set_session_cookie()
    set_session_user()
except Exception as e:
    st.error(f"Error starting user session: {e}")

if st.session_state.user.authorized:
    clean_render = get_clean_render("pc_main")

    if "pc_podcast_audio_files" not in st.session_state:
        st.session_state.pc_podcast_audio_files = dict()

    if st.session_state.get("pc_podcast_listen"):
        download_podcast_audio()

    with st.sidebar:
        st.subheader("Filter Podcasts")
        st.date_input(
            label="From",
            value=datetime.now(UTC) - timedelta(days=5),
            max_value=st.session_state.get("pc_podcast_filter_to", datetime.now(UTC)),
            key="pc_podcast_filter_from",
            on_change=partial(refresh_podcasts),
        )
        st.date_input(
            label="To",
            value=datetime.now(UTC),
            max_value=datetime.now(UTC),
            key="pc_podcast_filter_to",
            on_change=partial(refresh_podcasts),
        )
        st.multiselect(
            label="Geographies",
            options=get_podcast_geos(),
            on_change=partial(refresh_podcasts),
            key="pc_podcast_filter_geos",
        )
        st.multiselect(
            label="Tags",
            options=get_podcast_tags(),
            on_change=partial(refresh_podcasts),
            key="pc_podcast_filter_tags",
        )

        if "pc_podcast_list" not in st.session_state:
            st.session_state.pc_podcast_list = refresh_podcasts()

        if "pc_active_podcast" not in st.session_state:
            try:
                st.session_state.pc_active_podcast = st.session_state.pc_podcast_list[0]
            except IndexError:
                st.error("No podcasts found.")
                st.stop()

    st.chat_input(
        placeholder=f"Discussing about {st.session_state.pc_active_podcast.title}",
        key="pc_user_message",
    )

    for podcast in st.session_state.pc_podcast_list:
        expanded = st.session_state.pc_active_podcast.episode_id == podcast.episode_id
        with clean_render.expander(
            f"Ep. {podcast.episode_num}: {podcast.title}",
            expanded=expanded,
        ):
            st.subheader(podcast.title)
            st.caption(
                f"Episode {podcast.episode_num}; "
                f"published on {podcast.date.strftime('%d %B %Y')}"
            )
            st.write(podcast.summary)
            st.caption(f"Geos: {', '.join(podcast.geos)}")
            st.caption(f"Tags: {', '.join(podcast.tags)}")

            _, button_col, _ = st.columns([35, 30, 35])

            if not st.session_state.pc_podcast_audio_files.get(podcast.episode_id):
                st.session_state.pc_podcast_audio_files[podcast.episode_id] = (
                    get_podcast_audio(podcast.episode_id, _create_if_missing=False)
                )

            if st.session_state.pc_podcast_audio_files.get(podcast.episode_id):
                st.audio(
                    st.session_state.pc_podcast_audio_files[podcast.episode_id],
                    format="audio/mp3",
                )
            else:
                button_col.button(
                    "Listen to this episode",
                    key=f"pc_listen_{podcast.episode_id}",
                    on_click=partial(set_podcast_audio, podcast.episode_id),
                    use_container_width=True,
                )
else:
    st.error("You are not authorized to access _terra_.")
    st.stop()
