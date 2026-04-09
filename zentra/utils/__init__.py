import os
from pathlib import Path

from zentra.config import BASE_FOLDER


def resolve_file_path(data: dict):
    filename = data.get("filename", "").strip() or "generated_output.txt"
    folder   = data.get("folder",   "").strip()
    base_dir = Path(BASE_FOLDER) / folder if folder else Path(BASE_FOLDER)
    return base_dir, base_dir / filename


def resolve_any_path(filename: str) -> Path:
    p = Path(filename)
    if p.is_absolute() and p.exists():
        return p
    rel = Path.cwd() / p
    if rel.exists():
        return rel
    base = Path(BASE_FOLDER) / p
    if base.exists():
        return base
    return base


def ensure_dir(path: Path):
    try:
        path.mkdir(parents=True, exist_ok=True)
        return None
    except OSError as exc:
        return f"Could not create directory `{path}`: {exc}"


def write_file(file_path: Path, content: str):
    try:
        with open(file_path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return None
    except OSError as exc:
        return f"Could not write `{file_path}`: {exc}"
