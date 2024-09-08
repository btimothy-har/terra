FROM python:3.12.4
COPY --from=ghcr.io/astral-sh/uv:0.3.0 /uv /bin/uv

WORKDIR /app

COPY ./api/requirements.txt .
RUN uv pip install --system "psycopg[binary]" \
    && uv pip install --system -r requirements.txt

COPY ./api/src/api /app/api

EXPOSE 8100

CMD ["uvicorn", "api.main:app", \
    "--reload", \
    "--host", "0.0.0.0", \
    "--port", "8100"]