FROM python:3.12.4
COPY --from=ghcr.io/astral-sh/uv:0.3.0 /uv /bin/uv

WORKDIR /src

COPY ./app/requirements.txt .
RUN uv pip install --system -r requirements.txt

COPY ./app/src/app /src/app
COPY ./shared /src/app/shared

WORKDIR /src/app

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "Home.py", \
    "--server.port=8501", \
    "--server.headless=true", \
    "--server.runOnSave=false", \
    "--browser.gatherUsageStats=false", \
    "--theme.base=dark"]