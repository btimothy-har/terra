from functools import partial

import streamlit as st
from utils import delete_conversation
from utils import get_clean_render
from utils import set_active_conversation


@st.dialog("Open Thread", width="small")
def open_thread():
    conv_data = [i for i in list(st.session_state.conversations.values()) if i]
    if len(conv_data) == 0:
        st.rerun()

    conv_data.sort(key=lambda x: x.last_used, reverse=True)

    date_group = None
    select_thread = False
    delete_thread = False

    clean_render = get_clean_render("thread_list")
    with clean_render:
        for thread in conv_data:
            if not date_group or date_group != thread.last_used.strftime("%B %Y"):
                date_group = thread.last_used.strftime("%B %Y")
                st.caption(date_group)

            is_current_thread = thread.id == st.session_state.current_thread.id

            with st.expander(thread.summary, expanded=is_current_thread):
                _, col_resume, col_delete = st.columns([50, 25, 25])

                select_thread = col_resume.button(
                    label="Open",
                    key=f"convselect_{thread.id}",
                    type="secondary",
                    on_click=partial(set_active_conversation, thread.id),
                    disabled=is_current_thread,
                    use_container_width=True,
                )

                delete_thread = col_delete.button(
                    label="Delete",
                    key=f"convdelete_{thread.id}",
                    on_click=partial(delete_conversation, thread.id),
                    use_container_width=True,
                )
                if select_thread:
                    st.rerun()
                if delete_thread:
                    st.rerun(scope="fragment")
