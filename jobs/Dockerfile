FROM python:3.12.4
COPY --from=ghcr.io/astral-sh/uv:0.3.0 /uv /bin/uv

WORKDIR /src

COPY ./requirements.txt .
COPY ./pyproject.toml .
RUN uv pip install --system -r requirements.txt

COPY ./src/jobs ./jobs
RUN uv pip install --system -e .

ENTRYPOINT ["python", "jobs/main.py"]
CMD []