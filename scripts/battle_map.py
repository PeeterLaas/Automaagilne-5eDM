#!/usr/bin/env python3
"""
battle_map.py — Browser battle map for the combat tracker.

Writes two files into the data dir (play/ by default):
    battle_map.html   the page; open it once in a browser and leave it open
    battle_map.js     the current battle, re-read by the page every second

Works from file:// — no web server needed. combat_tracker.py calls render()
after every change, so the map follows the fight automatically.

Usage:
    python3 scripts/battle_map.py render      # (re)write the files
    python3 scripts/battle_map.py open        # render and open in the default browser
    python3 scripts/battle_map.py path        # print the path of battle_map.html

Assets (git-ignored, your own files):
    assets/maps/<anything>.jpg|png|webp     map images
    assets/maps/<image>.grid.json           grid saved by `combat_tracker.py map`
    assets/tokens/<name>.png|jpg|webp       token art, matched by combatant name:
                                            "Goblin2" → goblin2.*, then goblin.*
"""

import argparse
import json
import re
import sys
import webbrowser
from pathlib import Path

from dnd_paths import DATA_DIR

DEFAULT_COLS = 20
DEFAULT_ROWS = 15
SIZES = {"tiny": 1, "small": 1, "medium": 1, "large": 2, "huge": 3, "gargantuan": 4}
IMAGE_EXTS = (".png", ".webp", ".jpg", ".jpeg", ".gif")

CELL_RE = re.compile(r"^([A-Za-z]{1,2})(\d{1,3})$")


# ── Grid coordinates ──────────────────────────────────────────────────────────

def parse_cell(cell: str) -> tuple[int, int]:
    """'C4' → (col=2, row=3), zero-based. Raises ValueError."""
    m = CELL_RE.match(cell.strip())
    if not m:
        raise ValueError(f"'{cell}' is not a grid cell (expected e.g. C4, AA12)")
    col = 0
    for ch in m.group(1).upper():
        col = col * 26 + (ord(ch) - 64)
    row = int(m.group(2))
    if row < 1:
        raise ValueError(f"'{cell}': rows start at 1")
    return col - 1, row - 1


def cell_name(col: int, row: int) -> str:
    letters = ""
    n = col + 1
    while n:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return f"{letters}{row + 1}"


def parse_grid(grid: str) -> tuple[int, int]:
    """'24x18' → (24, 18)."""
    m = re.match(r"^\s*(\d+)\s*[xX×]\s*(\d+)\s*$", grid)
    if not m or int(m.group(1)) < 1 or int(m.group(2)) < 1:
        raise ValueError(f"'{grid}' is not a grid size (expected e.g. 24x18)")
    return int(m.group(1)), int(m.group(2))


# ── Map config ────────────────────────────────────────────────────────────────

def _sidecar(image_path: Path) -> Path:
    return image_path.with_name(image_path.name + ".grid.json")


def load_map_grid(data_dir: Path, image: str) -> dict | None:
    """Grid previously saved next to a map image, if any."""
    side = _sidecar(data_dir / image)
    try:
        return json.loads(side.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_map_grid(data_dir: Path, map_cfg: dict):
    if not map_cfg.get("image"):
        return
    side = _sidecar(data_dir / map_cfg["image"])
    grid = {k: map_cfg[k] for k in ("cols", "rows", "inset") if k in map_cfg}
    side.write_text(json.dumps(grid, indent=2), encoding="utf-8")


def make_map_config(data_dir: Path, image: str | None, grid: str | None, inset: str | None) -> dict:
    """Build the `map` block of combat_state.json, validating the inputs."""
    cfg: dict = {"image": None, "cols": DEFAULT_COLS, "rows": DEFAULT_ROWS, "inset": [0, 0, 0, 0]}
    if image:
        img = Path(image).expanduser()
        if not img.is_absolute():
            # Accept paths relative to the data dir or to the current directory.
            img = data_dir / img if (data_dir / img).exists() else img.resolve()
        if not img.exists():
            raise ValueError(f"map image not found: {image}")
        try:
            cfg["image"] = img.resolve().relative_to(data_dir.resolve()).as_posix()
        except ValueError:
            raise ValueError(
                f"map image must be inside {data_dir} (put it in assets/maps/), got {img}"
            )
        saved = load_map_grid(data_dir, cfg["image"])
        if saved:
            cfg.update({k: saved[k] for k in ("cols", "rows", "inset") if k in saved})
    if grid:
        cfg["cols"], cfg["rows"] = parse_grid(grid)
    if inset:
        parts = [float(x) for x in inset.split(",")]
        if len(parts) != 4 or not all(0 <= p < 0.5 for p in parts):
            raise ValueError("--inset needs 4 fractions 0–0.5: left,top,right,bottom")
        cfg["inset"] = parts
    return cfg


# ── Tokens ────────────────────────────────────────────────────────────────────

def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def find_token(data_dir: Path, name: str) -> str | None:
    """assets/tokens/<name>.* then the name without trailing numbers."""
    tokens_dir = data_dir / "assets" / "tokens"
    if not tokens_dir.is_dir():
        return None
    full = _slug(name)
    base = re.sub(r"_?\d+$", "", full)
    for stem in dict.fromkeys([full, base]):
        if not stem:
            continue
        for ext in IMAGE_EXTS:
            p = tokens_dir / f"{stem}{ext}"
            if p.exists():
                return p.relative_to(data_dir).as_posix()
    return None


# ── Rendering ─────────────────────────────────────────────────────────────────

def build_view(data_dir: Path) -> dict:
    try:
        state = json.loads((data_dir / "combat_state.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}

    map_cfg = {"image": None, "cols": DEFAULT_COLS, "rows": DEFAULT_ROWS, "inset": [0, 0, 0, 0]}
    map_cfg.update(state.get("map") or {})

    combatants = []
    for i, c in enumerate(state.get("combatants", [])):
        pos = None
        if c.get("pos"):
            try:
                col, row = parse_cell(c["pos"])
                pos = {"col": col, "row": row, "cell": c["pos"].upper()}
            except ValueError:
                pass
        combatants.append({
            "name": c["name"],
            "type": c.get("type", "enemy"),
            "initiative": c.get("initiative"),
            "hp": c.get("hp_current"),
            "hp_max": c.get("hp_max"),
            "ac": c.get("ac"),
            "conditions": c.get("conditions", []),
            "status": c.get("status", "alive"),
            "size": SIZES.get(str(c.get("size", "medium")).lower(), 1),
            "pos": pos,
            "token": c.get("token") or find_token(data_dir, c["name"]),
            "current": bool(state.get("active")) and i == state.get("turn_index"),
        })

    return {
        "active": bool(state.get("active")),
        "round": state.get("round"),
        "map": map_cfg,
        "combatants": combatants,
        "log": state.get("log", [])[-8:],
    }


def render(data_dir: Path | None = None) -> Path:
    data_dir = data_dir or DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    view = build_view(data_dir)
    js = data_dir / "battle_map.js"
    tmp = js.with_suffix(".js.tmp")
    tmp.write_text(
        "window.__BATTLE__ = " + json.dumps(view, ensure_ascii=False) + ";\n", encoding="utf-8"
    )
    tmp.replace(js)

    html = data_dir / "battle_map.html"
    template = Path(__file__).resolve().parent.parent / "templates" / "battle_map.html"
    content = template.read_text(encoding="utf-8")
    if not html.exists() or html.read_text(encoding="utf-8") != content:
        html.write_text(content, encoding="utf-8")
    return html


def main():
    parser = argparse.ArgumentParser(description="Browser battle map")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("action", nargs="?", default="render", choices=["render", "open", "path"])
    args = parser.parse_args()

    html = render(args.data_dir)
    if args.action == "path":
        print(html)
    elif args.action == "open":
        webbrowser.open(html.resolve().as_uri())
        print(f"🗺️  Opened {html}")
    else:
        print(f"🗺️  Battle map: {html.resolve().as_uri()}")


if __name__ == "__main__":
    sys.exit(main())
