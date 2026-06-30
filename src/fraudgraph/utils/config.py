from pathlib import Path
from typing import Any

import yaml

from fraudgraph.utils.paths import resolve_project_path


def load_yaml_config(config_path: str | Path = "configs/config.yaml") -> dict[str, Any]:
    resolved_path = resolve_project_path(config_path)

    if not resolved_path.exists():
        raise FileNotFoundError(f"Config file not found: {resolved_path}")

    with resolved_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if config is None:
        raise ValueError(f"Config file is empty: {resolved_path}")

    if not isinstance(config, dict):
        raise ValueError(f"Config file must contain a YAML mapping: {resolved_path}")

    return config


def get_nested_config_value(
    config: dict[str, Any],
    keys: list[str],
    default: Any | None = None,
) -> Any:
    current_value: Any = config

    for key in keys:
        if not isinstance(current_value, dict) or key not in current_value:
            return default
        current_value = current_value[key]

    return current_value