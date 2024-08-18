import asyncio
import os
from datetime import datetime
from datetime import timezone
from functools import partial
from uuid import uuid4

import config
import streamlit as st
import zoneinfo
from chat.graph import CHAT_AGENT
from chat.states import AgentConfig
from chat.states import ChatState
from clients.ai import AVAILABLE_MODELS
from dialogs.googleauth import auth_flow
from dialogs.sel_thread import open_thread
from langchain_core.messages import ChatMessage
from models.session import AppSession
from utils import dynamic_toast
from utils import get_clean_render
from utils import refresh_user_conversations
from utils import set_active_conversation


def invoke_graph():
    state = ChatState(
        loop_count=0,
        thread_id=st.session_state.current_thread.thread_id,
        agent=AgentConfig(
            model=st.session_state.ai_model,
            temp=st.session_state.ai_temp,
            max_tokens=st.session_state.ai_max_tokens,
        ),
        conversation=st.session_state.current_thread.message_dict(),
        workspace=[],
        agent_logs=[],
        use_multi_agent=st.session_state.multi_agent,
        completed=False,
        output=None,
    )
    response = asyncio.run(CHAT_AGENT.ainvoke(state))
    return response


st.set_page_config(
    page_title="terra Chat",
    page_icon=":coffee:",
    layout="centered",
    initial_sidebar_state="auto",
    # menu_items=None
)

if "ai_temp" not in st.session_state:
    st.session_state.ai_temp = config.DEFAULT_TEMP

if "ai_max_tokens" not in st.session_state:
    st.session_state.ai_max_tokens = config.DEFAULT_MAX_TOKENS

if "ai_model" not in st.session_state:
    st.session_state.ai_model = config.DEFAULT_MODEL

if "multi_agent" not in st.session_state:
    st.session_state.multi_agent = True

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
                use_container_width=True,
            ):
                st.caption(
                    "Settings in this window only affect the primary AI Model, "
                    "and not the background Agents."
                )
                ai_model_select = st.selectbox(
                    label="Model",
                    options=AVAILABLE_MODELS,
                    key="ai_model",
                    on_change=partial(dynamic_toast, "AI Model Changed:", "ai_model"),
                    help=(
                        "Gemini-1.5 models are best used with Multi-Agents, "
                        "while GPT-4o is best used as a standalone model."
                    ),
                )
                ai_temp_select = st.slider(
                    label="Temperature",
                    min_value=0.0,
                    max_value=1.0,
                    step=0.05,
                    key="ai_temp",
                    on_change=partial(
                        dynamic_toast, "AI Temperature Changed:", "ai_temp"
                    ),
                )
                ai_max_tokens_select = st.select_slider(
                    label="Max Tokens",
                    options=config.MAX_TOKEN_VALUES,
                    key="ai_max_tokens",
                    on_change=partial(
                        dynamic_toast, "AI Max Tokens Changed:", "ai_max_tokens"
                    ),
                )
                multi_agent_toggle = st.checkbox(
                    label="Use Multi-Agent",
                    key="multi_agent",
                    on_change=partial(
                        dynamic_toast, "Multi-Agent Toggled:", "multi_agent"
                    ),
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

            if len(st.session_state.current_thread.messages) == 0:
                st.session_state.current_thread.get_messages()

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
                new_user_message = st.session_state.current_thread.append(
                    ChatMessage(content=st.session_state.user_message, role="user")
                )
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
                    status_elem = st.empty()
                    with status_elem.status("Thinking...", expanded=True) as status:
                        response = invoke_graph()
                        time_taken = datetime.now(timezone.utc) - message_time
                        status.update(
                            label=f"Done! Took {time_taken.seconds} seconds.",
                            expanded=False,
                            state="complete",
                        )
                    status_elem.empty()
                    full_response = st.write_stream(response["output"])

            new_asst_message = st.session_state.current_thread.append(
                ChatMessage(content=full_response, role="assistant")
            )

            st.session_state.current_thread.save(st.session_state.session.user.id)
            new_user_message.save(
                thread_id=st.session_state.current_thread.thread_id,
                session_id=st.session_state.session.id,
                user_id=st.session_state.session.user.id,
            )
            new_asst_message.save(
                thread_id=st.session_state.current_thread.thread_id,
                session_id=st.session_state.session.id,
                user_id=st.session_state.session.user.id,
            )
            if response["workspace"]:
                new_asst_message.save_context(
                    thread_id=st.session_state.current_thread.thread_id,
                    context=response["workspace"],
                )
            if st.session_state.current_thread.thread_id not in list(
                st.session_state.conversations.keys()
            ):
                st.session_state.conversations = refresh_user_conversations()
            st.rerun()
    else:
        auth_flow()
