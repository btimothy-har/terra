# ruff: noqa: N999 Streamlit things

import asyncio
from datetime import datetime
from datetime import timezone
from functools import partial
from uuid import uuid4

import config
import streamlit as st
import zoneinfo
from clients.ai import AVAILABLE_MODELS
from conversation import AgentConfig
from conversation import ChatState
from conversation import chat_agent
from dialogs.auth import auth_flow
from dialogs.auth import get_user_info
from dialogs.sel_thread import open_thread
from models import ContextMessage
from models import Session
from models import ThreadMessage
from utils.chat import refresh_user_conversations
from utils.chat import set_active_conversation
from utils.main import dynamic_toast
from utils.main import get_clean_render


def invoke_graph():
    state = ChatState(
        loop_count=0,
        thread_id=st.session_state.current_thread.id,
        agent=AgentConfig(
            model=st.session_state.ai_model, temp=st.session_state.ai_temp
        ),
        conversation=st.session_state.current_thread.message_dict(),
        workspace=[],
        agent_logs=[],
        use_multi_agent=st.session_state.multi_agent,
        completed=False,
        output=None,
    )
    response = asyncio.run(chat_agent.ainvoke(state))
    return response


st.set_page_config(
    page_title="terra Chat",
    page_icon=":coffee:",
    layout="centered",
    initial_sidebar_state="auto",
    # menu_items=None
)

pg = st.navigation(
    pages=[st.Page("pages/podcasts.py", title="Podcasts", icon=":coffee:")]
)

pg.run()

if not st.session_state.get("session", None):
    cookie = st.context.cookies.get(config.SESSION_COOKIE)
    session = Session.resume(cookie) if cookie else None

    if session:
        st.session_state.session = session
    else:
        st.session_state.session = Session.create(cookie if cookie else str(uuid4()))

    st.session_state.session.set_cookie(
        config.SESSION_COOKIE, st.session_state.session.id
    )

if not st.session_state.get("user", None):
    if st.session_state.session.credentials:
        st.session_state.user = get_user_info(
            st.session_state.session.id, st.session_state.session.credentials
        )
    else:
        auth_flow()

if st.session_state.user.authorized:
    if "user_tz" not in st.session_state:
        st.session_state.user_tz = "UTC"

    if "conversations" not in st.session_state:
        st.session_state.conversations = refresh_user_conversations()

    if "current_thread" not in st.session_state:
        thread_cookie = st.context.cookies.get(config.THREAD_COOKIE)
        if thread_cookie:
            st.session_state.current_thread = set_active_conversation(thread_cookie)
        else:
            st.session_state.current_thread = set_active_conversation("new")

    st.session_state.session.set_cookie(
        config.THREAD_COOKIE, st.session_state.current_thread.id
    )

    with st.sidebar:
        buttons_container = st.container()
        st.divider()
        history_container = st.container()

        with buttons_container.popover(
            label="Chat Settings",
            help="Toggle settings for the AI model.",
            use_container_width=True,
        ):
            st.caption(
                "Settings in this window only affect the primary AI Model, "
                "<br />and not the background Agents.",
                unsafe_allow_html=True,
            )
            ai_model_select = st.selectbox(
                label="Model",
                options=AVAILABLE_MODELS,
                index=AVAILABLE_MODELS.index(config.DEFAULT_MODEL),
                key="ai_model",
                on_change=partial(dynamic_toast, "AI Model Changed:", "ai_model"),
                help=("Gemini-1.5 models are recommended for use with Multi-Agents."),
            )
            ai_temp_select = st.slider(
                label="Temperature",
                min_value=0.0,
                max_value=1.0,
                value=config.DEFAULT_TEMP,
                step=0.05,
                key="ai_temp",
                on_change=partial(dynamic_toast, "AI Temperature Changed:", "ai_temp"),
            )
            multi_agent_toggle = st.checkbox(
                label="Use Multi-Agent",
                value=True,
                key="multi_agent",
                on_change=partial(dynamic_toast, "Multi-Agent Toggled:", "multi_agent"),
                help=(
                    "When enabled, leverages multiple background Agents to assist "
                    "in generating responses. Disable for a faster response, using "
                    "only the primary AI model."
                ),
            )

        with buttons_container.popover(
            label="User Settings",
            help="Toggle settings for the user.",
            use_container_width=True,
            disabled=True,
        ):
            tz_select = st.selectbox(
                label="Timezone",
                options=sorted(
                    list(zoneinfo.available_timezones()),
                    key=lambda x: zoneinfo.ZoneInfo(x).utcoffset(
                        datetime.now(timezone.utc)
                    ),
                ),
                key="user_tz",
            )

        with history_container:
            new_col, resume_col = st.columns([50, 50])
            new_col.button(
                label="New Thread",
                key="convselect_new",
                type="secondary",
                on_click=partial(set_active_conversation, "new"),
                use_container_width=True,
            )

            resume_col.button(
                label="Open Thread",
                key="convselect_all",
                type="secondary",
                on_click=partial(open_thread),
                use_container_width=True,
                help=(
                    "Open an existing thread or manage your chat history."
                    if len(st.session_state.conversations) >= 1
                    and isinstance(st.session_state.conversations, dict)
                    else "You don't have any chat history yet."
                ),
                disabled=not (
                    len(st.session_state.conversations) >= 1
                    and isinstance(st.session_state.conversations, dict)
                ),
            )

    st.chat_input(
        placeholder="Type a message...",
        key="user_message",
    )

    clean_render = get_clean_render("chat")
    with clean_render:
        if st.session_state.current_thread.summary:
            st.header(f"{st.session_state.current_thread.summary}")

        for message in st.session_state.current_thread:
            with st.chat_message(message.role):
                st.write(message.content)
                st.caption(
                    message.timestamp.astimezone(
                        zoneinfo.ZoneInfo(st.session_state.user_tz)
                    ).strftime("%a %-d %b %Y %-I:%M %p %Z")
                )

    if getattr(st.session_state, "user_message", None):
        with st.chat_message("user"):
            new_user_message = ThreadMessage(
                content=st.session_state.user_message, role="user"
            )
            st.session_state.current_thread.append(new_user_message)
            st.write(new_user_message.content)
            st.caption(
                new_user_message.timestamp.astimezone(
                    zoneinfo.ZoneInfo(st.session_state.user_tz)
                ).strftime("%a %-d %b %Y %-I:%M %p %Z")
            )

        with st.chat_message("assistant"):
            message_container = st.container()
            timestamp_container = st.container()

            with timestamp_container:
                message_time = datetime.now(timezone.utc)
                st.caption(
                    message_time.astimezone(
                        zoneinfo.ZoneInfo(st.session_state.user_tz)
                    ).strftime("%a %-d %b %Y %-I:%M %p %Z")
                )

            with message_container:
                with st.status("Thinking...", expanded=True) as status:
                    response = invoke_graph()
                    time_taken = datetime.now(timezone.utc) - message_time
                    status.update(
                        label=f"Done! Took {time_taken.seconds} seconds.",
                        expanded=False,
                        state="complete",
                    )
                full_response = st.write_stream(response["output"])

        new_asst_message = ThreadMessage(
            content=full_response,
            role="assistant",
            model=st.session_state.ai_model,
        )
        st.session_state.current_thread.append(new_asst_message)

        st.session_state.current_thread.save()
        new_user_message.save(st.session_state.current_thread.id)
        new_asst_message.save(st.session_state.current_thread.id)

        if response["workspace"]:
            ContextMessage.save(response["workspace"])

        if st.session_state.current_thread.id not in list(
            st.session_state.conversations.keys()
        ):
            st.session_state.conversations = refresh_user_conversations()
        st.rerun()
else:
    st.error("You are not authorized to access _terra_.")
    st.stop()
