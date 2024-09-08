import os

import streamlit as st
from cryptography.fernet import Fernet


@st.cache_resource
def get_encryption_client() -> Fernet:
    return Fernet(os.getenv("ENCRYPTION_KEY"))
