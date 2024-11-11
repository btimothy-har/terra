import streamlit as st
from utils.podcast import get_podcast_audio


@st.dialog("Downloading...", width="small")
def download_podcast_audio():
    with st.spinner(
        "Downloading podcast audio... please wait. Do not close this window."
    ):
        st.session_state.pc_podcast_audio_files[st.session_state.pc_podcast_listen] = (
            get_podcast_audio(
                st.session_state.pc_podcast_listen, _create_if_missing=True
            )
        )
    st.session_state.pc_podcast_listen = None
    st.rerun()
