FROM python:3.12.4
COPY --from=ghcr.io/astral-sh/uv:0.3.0 /uv /bin/uv

WORKDIR /src

COPY ./requirements.txt .
RUN uv pip install --system -r requirements.txt

WORKDIR /src/app

COPY ./src/app .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "main.py", \
    "--server.port=8501", \
    "--server.headless=true", \
    "--server.runOnSave=true", \
    "--server.baseUrlPath=/chat", \
    "--browser.gatherUsageStats=false", \
    "--theme.base=dark"]