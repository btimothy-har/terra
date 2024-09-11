FROM python:3.12.4
COPY --from=ghcr.io/astral-sh/uv:0.3.0 /uv /bin/uv

WORKDIR /src

COPY ./requirements.txt .
COPY ./pyproject.toml .
RUN uv pip install --system "psycopg[binary]" \
    && uv pip install --system -r requirements.txt

COPY ./src/api ./api
RUN uv pip install --system -e .

CMD ["uvicorn", "api.main:app", \
    "--reload", \
    "--host", "0.0.0.0", \
    "--port", "8000"]