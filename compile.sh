#!/bin/bash

uv pip compile api/requirements.in -q -U -o api/requirements.txt
uv pip compile app/requirements.in -q -U -o app/requirements.txt
uv pip compile jobs/requirements.in -q -U -o jobs/requirements.txt

uv sync

uv pip install -r api/requirements.txt
uv pip install -r app/requirements.txt
uv pip install -r jobs/requirements.txt

echo "Compilation complete." 