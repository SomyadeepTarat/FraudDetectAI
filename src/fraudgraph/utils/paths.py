from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def resolve_project_path(relative_path: str | Path) -> Path:
    path = Path(relative_path)

    if path.is_absolute():
        return path

    return get_project_root() / path


def ensure_parent_dir(file_path: str | Path) -> Path:
    resolved_path = resolve_project_path(file_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    return resolved_path


def ensure_dir(directory_path: str | Path) -> Path:
    resolved_path = resolve_project_path(directory_path)
    resolved_path.mkdir(parents=True, exist_ok=True)
    return resolved_path