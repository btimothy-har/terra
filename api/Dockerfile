FROM python:3.12.4

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ffmpeg \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.cargo/bin:${PATH}"

COPY --from=ghcr.io/astral-sh/uv:0.3.0 /uv /bin/uv

WORKDIR /src

COPY ./api/requirements.txt ./api/pyproject.toml ./
RUN uv pip install --system -r requirements.txt

COPY ./api/src/api /src/api
COPY ./shared /src/shared

RUN uv pip install --system -e .

CMD ["uvicorn", "api.main:app", \
    "--reload", \
    "--host", "0.0.0.0", \
    "--port", "8000"]