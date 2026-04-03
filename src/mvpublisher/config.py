from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    app_name: str
    home_dir: Path

    @classmethod
    def from_env(cls) -> "AppConfig":
        env_home = os.environ.get("MVPUBLISHER_HOME")
        if env_home:
            root = Path(env_home).resolve()
        else:
            root = (Path.cwd() / "runtime").resolve()
        return cls(app_name="mvpublisher", home_dir=root)
