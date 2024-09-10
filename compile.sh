eval "uv pip compile app/requirements.in api/requirements.in jobs/requirements.in -o requirements.txt"

eval "uv pip compile app/requirements.in -o app/requirements.txt"
eval "uv pip compile api/requirements.in -o api/requirements.txt"
eval "uv pip compile jobs/requirements.in -o jobs/requirements.txt"

eval "uv sync"

eval "uv pip install -r requirements.txt"

echo "Compilation complete."