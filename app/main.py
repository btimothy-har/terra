import os
from datetime import datetime
from datetime import timezone
from functools import partial
from uuid import uuid4

import config
import streamlit as st
import zoneinfo
from dialogs.googleauth import auth_flow
from dialogs.sel_thread import open_thread
from langchain_core.messages import ChatMessage
from models.session import AppSession
from utils import get_clean_render
from utils import refresh_user_conversations
from utils import reload_model
from utils import set_active_conversation

st.set_page_config(
    page_title="terra Chat",
    page_icon=":coffee:",
    layout="centered",
    initial_sidebar_state="auto",
    #menu_items=None
    )

if "ai_temp" not in st.session_state:
    st.session_state.ai_temp = config.DEFAULT_TEMP

if "ai_max_tokens" not in st.session_state:
    st.session_state.ai_max_tokens = config.DEFAULT_MAX_TOKENS

if "ai_client" not in st.session_state:
    reload_model()

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
        if "user_tz" not in st.session_state:
            st.session_state.user_tz = "UTC"

        if "current_thread" not in st.session_state:
            st.session_state.current_thread = set_active_conversation("new")

        if "conversations" not in st.session_state:
            st.session_state.conversations = refresh_user_conversations()

        with st.sidebar:
            buttons_container = st.container()
            st.divider()
            history_container = st.container()

            with buttons_container.popover(
                label="Chat Settings",
                help="Toggle settings for the AI model.",
                use_container_width=True
                ):
                ai_temp_select = st.slider(
                    label="Temperature",
                    min_value=0.0,
                    max_value=1.0,
                    step=0.05,
                    key="ai_temp",
                    on_change=partial(reload_model,True)
                    )
                ai_max_tokens_select = st.select_slider(
                    label="Max Tokens",
                    options=config.MAX_TOKEN_VALUES,
                    key="ai_max_tokens",
                    on_change=partial(reload_model,True)
                    )

            with buttons_container.popover(
                label="User Settings",
                help="Toggle settings for the user.",
                use_container_width=True,
                disabled=True
                ):
                tz_select = st.selectbox(
                    label="Timezone",
                    options=sorted(list(zoneinfo.available_timezones()), key=lambda x: zoneinfo.ZoneInfo(x).utcoffset(datetime.now(timezone.utc))),
                    key="user_tz"
                    )

            with history_container:
                new_col, resume_col = st.columns([50, 50])
                new_col.button(
                    label="New Thread",
                    key="convselect_new",
                    type="secondary",
                    on_click=partial(set_active_conversation, "new"),
                    use_container_width=True
                )

                resume_col.button(
                    label="Open Thread",
                    key="convselect_all",
                    type="secondary",
                    on_click=partial(open_thread),
                    use_container_width=True,
                    help=("Open an existing thread or manage your chat history."
                        if len(st.session_state.conversations) >= 1 and isinstance(st.session_state.conversations, dict)
                        else "You don't have any chat history yet."),
                    disabled=not(len(st.session_state.conversations) >= 1
                        and isinstance(st.session_state.conversations, dict))
                )

        st.chat_input(
            placeholder="Type a message...",
            key="user_message",
            )

        clean_render = get_clean_render("chat")
        with clean_render:
            if st.session_state.current_thread.summary:
                st.header(f"{st.session_state.current_thread.summary}")

            if len(st.session_state.current_thread.messages) == 0:
                st.session_state.current_thread.get_messages()

            for message in st.session_state.current_thread:
                with st.chat_message(message.role):
                    st.write(message.content)
                    st.caption(message.timestamp.astimezone(
                        zoneinfo.ZoneInfo(st.session_state.user_tz)
                        ).strftime("%a %-d %b %Y %-I:%M %p %Z"))

        if getattr(st.session_state, "user_message", None):
            with st.chat_message("user"):
                new_user_message = st.session_state.current_thread.append(
                    ChatMessage(
                        content=st.session_state.user_message,
                        role="user")
                        )
                st.write(new_user_message.content)
                st.caption(new_user_message.timestamp.astimezone(
                    zoneinfo.ZoneInfo(st.session_state.user_tz)
                    ).strftime("%a %-d %b %Y %-I:%M %p %Z"))

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = st.write_stream(
                        st.session_state.ai_client.stream(st.session_state.current_thread.message_dict())
                        )
                new_asst_message = st.session_state.current_thread.append(
                    ChatMessage(content=response, role="assistant")
                    )
                st.caption(new_asst_message.timestamp.astimezone(
                    zoneinfo.ZoneInfo(st.session_state.user_tz)
                    ).strftime("%a %-d %b %Y %-I:%M %p %Z"))

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
