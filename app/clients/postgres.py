import os

import streamlit as st
from psycopg_pool import ConnectionPool


@st.cache_resource
def get_pg_client() -> ConnectionPool:
    db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/terra"
    return ConnectionPool(db_url)
