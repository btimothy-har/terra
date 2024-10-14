FROM python:3.12.4
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