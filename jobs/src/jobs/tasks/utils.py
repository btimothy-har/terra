from typing import Any


def clean_string(s: Any) -> Any:
    if isinstance(s, str):
        return s.encode("utf-8", errors="ignore").decode("utf-8").replace("\x00", "")
    elif isinstance(s, list):
        return [clean_string(item) for item in s]
    elif isinstance(s, dict):
        return {k: clean_string(v) for k, v in s.items()}
    return s
