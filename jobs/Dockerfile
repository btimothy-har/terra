FROM python:3.12.4
COPY --from=ghcr.io/astral-sh/uv:0.3.0 /uv /bin/uv

WORKDIR /src

COPY ./requirements.txt .
RUN uv pip install --system -r requirements.txt

WORKDIR /src/jobs

COPY ./src/jobs .

ENTRYPOINT ["python", "main.py"]