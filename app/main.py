import os
from functools import partial
from uuid import uuid4

import config
import streamlit as st
from clients.ai import AVAILABLE_MODELS
from clients.ai import get_client
from googleauth import auth_flow
from langchain_core.messages import ChatMessage
from models.session import AppSession
from models.thread import AppThread as ConversationThread
from streamlit.delta_generator import DeltaGenerator


def reload_model(toast=True):
    st.session_state.ai_client = get_client(
        st.session_state.ai_model,
        st.session_state.ai_temp,
        st.session_state.ai_max_tokens
        )
    if toast:
        st.toast("Language Model Reloaded.")

def get_clean_render() -> DeltaGenerator:
    slot_in_use = st.session_state.slot_in_use = st.session_state.get("slot_in_use", "a")
    if slot_in_use == "a":
        slot_in_use = st.session_state.slot_in_use = "b"
    else:
        slot_in_use = st.session_state.slot_in_use = "a"

    slot = {
        "a": st.empty(),
        "b": st.empty(),
    }[slot_in_use]
    return slot.container()

def refresh_user_conversations() -> dict:
    user_threads = ConversationThread.get_all_for_user(st.session_state.session.user.id)

    if user_threads:
        st.session_state.conversations = conversations = {
            thread_id: ConversationThread.get_from_id(
                thread_id=thread_id,
                user_id=st.session_state.session.user.id
                )
            for thread_id in user_threads
            }
    else:
        st.session_state.conversations = conversations = dict()
    return conversations

def set_active_conversation(thread_id:str) -> ConversationThread:
    if thread_id == "new":
        active_thread = st.session_state.current_thread = ConversationThread.create(st.session_state.session.id)
        st.session_state.current_thread.append(
            ChatMessage(
                content=f"Hello, {st.session_state.session.user.given_name}! How may I help you?",
                role="assistant"
                )
            )
    else:
        active_thread = st.session_state.current_thread = st.session_state.conversations.get(thread_id)
    return active_thread

def delete_active_conversation():
    st.session_state.current_thread.delete(st.session_state.session.user.id)
    st.session_state.current_thread = set_active_conversation("new")
    st.session_state.conversations = refresh_user_conversations()

st.set_page_config(
    page_title="terra Chat",
    page_icon=":coffee:",
    layout="centered",
    initial_sidebar_state="auto",
    #menu_items=None
    )

if "ai_model" not in st.session_state:
    st.session_state.ai_model = config.DEFAULT_MODEL

if "ai_temp" not in st.session_state:
    st.session_state.ai_temp = config.DEFAULT_TEMP

if "ai_max_tokens" not in st.session_state:
    st.session_state.ai_max_tokens = config.DEFAULT_MAX_TOKENS

if "ai_client" not in st.session_state:
    reload_model(False)

if not st.session_state.get("session", None):
    cookie = st.context.cookies.get(os.environ.get("COOKIE_NAME"))
    session = AppSession.resume(cookie) if cookie else None

    if session:
        st.session_state.session = session
    else:
        st.session_state.session = AppSession.create(cookie if cookie else str(uuid4()))
        st.session_state.session.set_cookie()

if __name__ == "__main__":
    if st.session_state.session.authorized:
        if "current_thread" not in st.session_state:
            st.session_state.current_thread = set_active_conversation("new")

        if "conversations" not in st.session_state:
            st.session_state.conversations = refresh_user_conversations()

        with st.sidebar:
            title_container = st.container()
            buttons_container = st.container()
            del_button, set_button = buttons_container.columns([60, 40])

            st.divider()

            history_container = st.container()

            with set_button.popover(
                label="Settings",
                help="Toggle settings for the AI model.",
                use_container_width=False
                ):
                ai_model_select = st.selectbox(
                    label="Chat Model",
                    options=AVAILABLE_MODELS,
                    key="ai_model",
                    on_change=partial(reload_model, toast=True)
                    )
                ai_temp_select = st.slider(
                    label="Temperature",
                    min_value=0.0,
                    max_value=1.0,
                    step=0.05,
                    key="ai_temp",
                    on_change=partial(reload_model, toast=True)
                    )
                ai_max_tokens_select = st.select_slider(
                    label="Max Tokens",
                    options=config.MAX_TOKEN_VALUES,
                    key="ai_max_tokens",
                    on_change=partial(reload_model, toast=True)
                    )

            if st.session_state.current_thread.summary:
                title_container.header(f"{st.session_state.current_thread.summary}")

                del_button.button(
                    label="Delete Thread",
                    key=f"convdelete_{st.session_state.current_thread.thread_id}",
                    on_click=partial(delete_active_conversation),
                    use_container_width=True,
                    )
            else:
                title_container.header("terra Chat")
                del_button.caption("Start a new conversation or resume one from your chat history.")

            with history_container:
                title_col, new_col = st.columns([70, 30])
                title_col.header("Conversations")
                new_col.button(
                        label="New",
                        key="convselect_new",
                        type="secondary",
                        on_click=partial(set_active_conversation, "new"),
                        use_container_width=True
                    )

                if len(st.session_state.conversations) >= 1 and isinstance(st.session_state.conversations, dict):
                    conv_data = list(st.session_state.conversations.values())
                    conv_data.sort(key=lambda x: x.last_used, reverse=True)

                    date_group = None
                    for thread in conv_data:
                        if not date_group or date_group != thread.last_used.strftime("%B %Y"):
                            date_group = thread.last_used.strftime("%B %Y")
                            st.caption(date_group)

                        st.button(
                            label=thread.summary if len(thread.summary) <= 30 else f"{thread.summary[:30]}...",
                            key=f"convselect_{thread.thread_id}",
                            type="secondary",
                            on_click=partial(set_active_conversation, thread.thread_id),
                            disabled=True \
                                if thread.thread_id == st.session_state.current_thread.thread_id \
                                else False,
                            use_container_width=True
                        )

        st.chat_input(
            placeholder="Type a message...",
            key="user_message",
            )

        clean_render = get_clean_render()

        with clean_render:
            if len(st.session_state.current_thread.messages) == 0:
                st.session_state.current_thread.get_messages()

            for message in st.session_state.current_thread:
                with st.chat_message(message.role):
                    st.write(message.content)
                    st.caption(message.timestamp.strftime("%a %-d %b %Y %-I:%M:%S %p %Z"))

        if getattr(st.session_state, "user_message", None):
            with st.chat_message("user"):
                new_user_message = st.session_state.current_thread.append(
                    ChatMessage(
                        content=st.session_state.user_message,
                        role="user")
                        )
                st.write(new_user_message.content)
                st.caption(new_user_message.timestamp.strftime("%a %-d %b %Y %-I:%M %p %Z"))

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = st.write_stream(
                        st.session_state.ai_client.stream(st.session_state.current_thread.message_dict())
                        )
                new_asst_message = st.session_state.current_thread.append(
                    ChatMessage(content=response, role="assistant")
                    )
                st.caption(new_asst_message.timestamp.strftime("%a %-d %b %Y %-I:%M %p %Z"))

            st.session_state.current_thread.save(st.session_state.session.user.id)
            new_user_message.save(
                thread_id=st.session_state.current_thread.thread_id,
                session_id=st.session_state.session.id,
                user_id=st.session_state.session.user.id
                )
            new_asst_message.save(
                thread_id=st.session_state.current_thread.thread_id,
                session_id=st.session_state.session.id,
                user_id=st.session_state.session.user.id
                )
            if st.session_state.current_thread.thread_id not in list(st.session_state.conversations.keys()):
                st.session_state.conversations = refresh_user_conversations()
            st.rerun()
    else:
        auth_flow()
