import streamlit as st
from langchain_core.messages import ChatMessage
from models.thread import AppThread as ConversationThread
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


def refresh_user_conversations() -> dict:
    user_threads = ConversationThread.get_all_for_user(st.session_state.session.user.id)

    if user_threads:
        conversations = {
            thread_id: ConversationThread.get_from_id(
                thread_id=thread_id, user_id=st.session_state.session.user.id
            )
            for thread_id in user_threads
        }
        conversations = {k: v for k, v in conversations.items() if v}
        st.session_state.conversations = conversations
    else:
        st.session_state.conversations = conversations = dict()
    return conversations


def set_active_conversation(thread_id: str) -> ConversationThread:
    if thread_id == "new":
        active_thread = st.session_state.current_thread = ConversationThread.create(
            st.session_state.session.id
        )
        st.session_state.current_thread.append(
            ChatMessage(
                content=f"Hello, {st.session_state.session.user.given_name}! How may I help you?",
                role="assistant",
            )
        )
    else:
        active_thread = st.session_state.current_thread = (
            st.session_state.conversations.get(thread_id)
        )
    return active_thread


def delete_conversation(thread_id: str):
    thread = st.session_state.conversations.pop(thread_id)
    if thread:
        is_current = thread.thread_id == st.session_state.current_thread.thread_id
        thread.delete(st.session_state.session.user.id)
        if is_current:
            st.session_state.current_thread = set_active_conversation("new")

        st.session_state.conversations = refresh_user_conversations()
