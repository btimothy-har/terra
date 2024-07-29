import streamlit as st
from ai import AVAILABLE_MODELS
from ai import MAX_TOKEN_VALUES
from ai import get_client
from googleauth import auth_flow
from langchain_core.messages import ChatMessage
from session import SessionHistory
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

st.set_page_config(
    page_title="Terra Chat",
    page_icon=":coffee:",
    layout="centered",
    initial_sidebar_state="auto",
    #menu_items=None
    )

if "auth_code" not in st.session_state:
    st.session_state["auth_code"] = None

if "user_info" not in st.session_state:
    st.session_state["user_info"] = None

if "ai_model" not in st.session_state:
    st.session_state.ai_model = AVAILABLE_MODELS[0]

if "ai_temp" not in st.session_state:
    st.session_state.ai_temp = 0.2

if "ai_max_tokens" not in st.session_state:
    st.session_state.ai_max_tokens = 4096

if "ai_client" not in st.session_state:
    reload_model(False)

if "message_history" not in st.session_state:
    st.session_state.message_history = SessionHistory()
    st.session_state.message_history.append(
        ChatMessage(content="Hello, how may I help you?", role="assistant")
        )

with st.sidebar:
    ai_model_select = st.selectbox(
        label="Chat Model",
        options=AVAILABLE_MODELS,
        key="ai_model",
        on_change=reload_model
        )
    ai_temp_select = st.slider(
        label="Temperature",
        min_value=0.0,
        max_value=1.0,
        step=0.05,
        key="ai_temp",
        on_change=reload_model
        )
    ai_max_tokens_select = st.select_slider(
        label="Max Tokens",
        options=MAX_TOKEN_VALUES,
        key="ai_max_tokens",
        on_change=reload_model
        )

if __name__ == "__main__":
    if st.session_state.user_info and st.session_state.auth_code:
        st.chat_input(
            placeholder="Type a message...",
            key="user_message",
        )

        clean_render = get_clean_render()

        with clean_render:
            for message in st.session_state.message_history:
                with st.chat_message(message.role):
                    st.write(message.content)

            if getattr(st.session_state, "user_message", None):
                with st.chat_message("user"):
                    message = ChatMessage(content=st.session_state.user_message, role="user")
                    st.session_state.message_history.append(message)
                    st.write(message.content)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        response = st.write_stream(
                            st.session_state.ai_client.stream(st.session_state.message_history.message_dict())
                            )
                st.session_state.message_history.append(
                    ChatMessage(content=response, role="assistant")
                    )
    else:
        auth_flow()
