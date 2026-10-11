"""
dnd_paths.py — Where the game data lives, independent of the agent running it.

Resolution order:
  1. $DND_DATA_DIR                (explicit override)
  2. /opt/data                    (Hermes / Docker container layout)
  3. <repo>/play                  (local play with Pi, Claude Code, Gemini CLI, ...)
"""

import os
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPTS_DIR.parent


def resolve_data_dir() -> Path:
    env = os.environ.get("DND_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()
    container = Path("/opt/data")
    if container.is_dir():
        return container
    return REPO_DIR / "play"


DATA_DIR = resolve_data_dir()
