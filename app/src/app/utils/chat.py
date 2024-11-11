import streamlit as st
from models import ConversationThread
from models import ThreadMessage


def refresh_user_conversations() -> dict:
    user_threads = ConversationThread.get_all_for_user()

    if user_threads:
        conversations = {
            thread_id: ConversationThread.get_from_id(thread_id=thread_id)
            for thread_id in user_threads
        }
        conversations = {k: v for k, v in conversations.items() if v}
        st.session_state.conversations = conversations
    else:
        st.session_state.conversations = conversations = dict()
    return conversations


def set_active_conversation(thread_id: str) -> ConversationThread:
    if thread_id == "new":
        active_thread = st.session_state.current_thread = ConversationThread.create()
        st.session_state.current_thread.append(
            ThreadMessage(
                role="assistant",
                content=(
                    f"Hello, {st.session_state.user.given_name}! " "How may I help you?"
                ),
            )
        )
    else:
        active_thread = st.session_state.current_thread = (
            st.session_state.conversations.get(thread_id)
        )
        if not active_thread:
            return set_active_conversation("new")

        if len(active_thread.messages) == 0:
            active_thread.get_messages()

    return active_thread


def delete_conversation(thread_id: str):
    thread = st.session_state.conversations.pop(thread_id)
    if thread:
        is_current = thread.id == st.session_state.current_thread.id
        thread.delete()
        if is_current:
            st.session_state.current_thread = set_active_conversation("new")

        st.session_state.conversations = refresh_user_conversations()
