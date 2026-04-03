from pathlib import Path

from .config import AppConfig


def runtime_root(config: AppConfig) -> Path:
    config.home_dir.mkdir(parents=True, exist_ok=True)
    return config.home_dir
