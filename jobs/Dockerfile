FROM python:3.12.4

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
ENV PATH="/root/.cargo/bin:${PATH}"

COPY --from=ghcr.io/astral-sh/uv:0.3.0 /uv /bin/uv

WORKDIR /src

COPY ./requirements.txt ./pyproject.toml ./
RUN uv pip install --system -r requirements.txt

COPY ./src/jobs /src/jobs
RUN uv pip install --system -e .

ENTRYPOINT ["python", "jobs/main.py"]
