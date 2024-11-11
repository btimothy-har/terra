from uuid import uuid4

import streamlit as st
from config import SESSION_COOKIE
from dialogs.auth import auth_flow
from dialogs.auth import get_user_info
from models import Session
from models import User
from streamlit.delta_generator import DeltaGenerator


def dynamic_toast(message: str, key: str):
    st.toast(f"{message} `{st.session_state.get(key, "")}`")


def get_clean_render(key: str) -> DeltaGenerator:
    render_slots = st.session_state.render_slots = st.session_state.get(
        "render_slots", dict()
    )

    slot_in_use = render_slots[key] = render_slots.get(key, "a")

    if slot_in_use == "a":
        slot_in_use = st.session_state.render_slots[key] = "b"
    else:
        slot_in_use = st.session_state.render_slots[key] = "a"

    slot = {
        "a": st.empty(),
        "b": st.empty(),
    }[slot_in_use]
    return slot.container()


def set_session_cookie() -> Session:
    if not st.session_state.get("session", None):
        cookie = st.context.cookies.get(SESSION_COOKIE)
        session = Session.resume(cookie) if cookie else None

        if session:
            st.session_state.session = session
        else:
            st.session_state.session = Session.create(
                cookie if cookie else str(uuid4())
            )

        st.session_state.session.set_cookie(SESSION_COOKIE, st.session_state.session.id)
    return st.session_state.session


def set_session_user() -> User:
    if not st.session_state.get("user", None):
        if st.session_state.session.credentials:
            st.session_state.user = get_user_info(
                st.session_state.session.id, st.session_state.session.credentials
            )
        else:
            auth_flow()
    return st.session_state.user
