import json
from pathlib import Path


def load_json(file_path, default=None):
    if default is None:
        default = {}

    try:
        file_path = Path(file_path)
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except json.JSONDecodeError:
        return default
    return default


def save_json(file_path, data):
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)