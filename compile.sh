#!/bin/bash

uv pip compile api/requirements.in -o api/requirements.txt
uv pip compile app/requirements.in -o app/requirements.txt
uv pip compile jobs/requirements.in -o jobs/requirements.txt

uv sync

uv pip install -r api/requirements.txt
uv pip install -r app/requirements.txt
uv pip install -r jobs/requirements.txt

echo "Compilation complete." 