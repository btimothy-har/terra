eval "uv pip compile app/requirements.in -o app/requirements.txt"
eval "uv pip compile api/requirements.in -o api/requirements.txt"

eval "uv sync"

eval "uv pip install -r app/requirements.txt -r api/requirements.txt"

echo "Compilation complete"