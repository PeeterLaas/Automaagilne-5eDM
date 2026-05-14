#!/usr/bin/env python3
"""
Dungeon Chat Bridge — Natural-language command parser for the D&D group chat.

The DM calls this script when the player says things like:
  "¿Qué partidas hay?"
  "Guarda esta partida"
  "Carga la de Harry Potter"
  "Nueva partida: El Mundo Perdido"

Usage (called by DM):
    python3 /opt/data/scripts/dungeon_chat.py parse "mensaje del jugador"

Returns a single-line instruction that the DM should echo to the player.
"""

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

DEFAULT_DATA_DIR = Path("/opt/data")

# ── Intent patterns (Spanish + English) ───────────────────────────────────────

INTENTS = [
    ("list", [
        r"qu[eé] partidas?( hay)?",
        r"lista(r)? (las )?partidas?",
        r"partidas? (guardadas|disponibles|existentes)",
        r"show (saved )?campaigns",
        r"list (my )?campaigns",
        r"what campaigns( are there)?",
    ]),
    ("save", [
        r"guarda(r|da)?( esta)?( partida)?",
        r"save( this)?( campaign|game|session)?",
        r"checkpoint",
        r"guardar",
    ]),
    ("status", [
        r"estado( de la partida)?",
        r"status( of (the )?campaign)?",
        r"c[oó]mo vamos",
        r"d[oó]nde estamos",
    ]),
    ("switch", [
        r"carga(r|da)?( la (de )?)?(?P<id>.+)",
        r"load( the )?(?P<id>.+)",
        r"switch( to )?(?P<id>.+)",
        r"cambiar( a)?( la (de )?)?(?P<id>.+)",
    ]),
    ("new", [
        r"nueva partida[;:](?P<title>.+)",
        r"new campaign[;:](?P<title>.+)",
        r"crear partida[;:](?P<title>.+)",
        r"empezar (una )?nueva[;:](?P<title>.+)",
    ]),
    ("chat_history", [
        r"historial( de chat)?",
        r"chat history",
        r"[uú]ltimos mensajes",
        r"qu[eé] dijimos",
    ]),
]


def _detect_intent(text: str) -> tuple[str, dict]:
    text_lower = text.lower().strip()
    for intent, patterns in INTENTS:
        for pat in patterns:
            m = re.search(pat, text_lower)
            if m:
                return intent, m.groupdict()
    return "unknown", {}


def _run_manager(cmd: str) -> str:
    """Run campaign_manager.py and return stdout."""
    try:
        result = subprocess.run(
            ["python3", str(DEFAULT_DATA_DIR / "scripts/campaign_manager.py")] + cmd.split(),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"❌ Error running campaign_manager: {e}"


def _run_resumen() -> str:
    try:
        result = subprocess.run(
            ["python3", str(DEFAULT_DATA_DIR / "scripts/generate_resumen.py")],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout
    except Exception:
        return ""


def _slugify(text: str) -> str:
    text = text.lower().strip()
    for src, dst in [
        ("á", "a"), ("à", "a"), ("ä", "a"),
        ("é", "e"), ("è", "e"), ("ë", "e"),
        ("í", "i"), ("ì", "i"), ("ï", "i"),
        ("ó", "o"), ("ò", "o"), ("ö", "o"),
        ("ú", "u"), ("ù", "u"), ("ü", "u"),
        ("ñ", "n"),
    ]:
        text = text.replace(src, dst)
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text[:60]


def _find_campaign_id(name_hint: str) -> str | None:
    """Fuzzy match a campaign name hint to an existing ID."""
    campaigns_dir = DEFAULT_DATA_DIR / "campaigns_data"
    if not campaigns_dir.exists():
        return None

    hint = _slugify(name_hint)
    candidates = [p.stem for p in campaigns_dir.glob("*.json")]

    # Exact match
    if hint in candidates:
        return hint

    # Substring match
    for c in candidates:
        if hint in c or c in hint:
            return c

    # Word-by-word match
    hint_words = set(hint.split("_"))
    best = None
    best_score = 0
    for c in candidates:
        c_words = set(c.split("_"))
        score = len(hint_words & c_words)
        if score > best_score:
            best_score = score
            best = c

    return best if best_score > 0 else None


def handle_list() -> str:
    out = _run_manager("list")
    if "No saved campaigns" in out:
        return "📭 No hay partidas guardadas."
    # Compact the output for chat
    lines = []
    for line in out.splitlines():
        if line.strip().startswith("["):
            lines.append(line.strip())
        elif line.strip().startswith("📜"):
            lines[-1] += " " + line.strip()
    return "📚 Partidas guardadas:\n" + "\n".join(lines) if lines else out


def handle_save() -> str:
    out = _run_manager("save chat_manual")
    _run_resumen()
    if "Saved:" in out:
        return "✅ Partida guardada con éxito (incluyendo historial de chat)."
    return out


def handle_status() -> str:
    return _run_manager("status")


def handle_switch(name_hint: str) -> str:
    cid = _find_campaign_id(name_hint)
    if not cid:
        return f"❌ No encontré una partida que coincida con '{name_hint}'. Usa 'list' para ver las disponibles."
    out = _run_manager(f"switch {cid}")
    _run_resumen()
    if "Active campaign" in out:
        return f"✅ Partida cargada: [{cid}]. El resumen se ha actualizado."
    return out


def handle_new(title_raw: str) -> str:
    title = title_raw.strip().strip('"').strip("'")
    cid = _slugify(title)
    out = _run_manager(f'new {cid} "{title}"')
    if "New campaign created" in out:
        return f"✅ Nueva partida creada: [{cid}] — {title}. Usa 'switch {cid}' para activarla."
    return out


def handle_chat_history() -> str:
    return _run_manager("chat-history")


def parse_command(text: str) -> str:
    intent, groups = _detect_intent(text)

    if intent == "list":
        return handle_list()
    if intent == "save":
        return handle_save()
    if intent == "status":
        return handle_status()
    if intent == "switch":
        name = groups.get("id", "").strip()
        if not name:
            return "❌ ¿Qué partida quieres cargar? Di algo como 'carga la de Harry Potter'."
        return handle_switch(name)
    if intent == "new":
        title = groups.get("title", "").strip()
        if not title:
            return "❌ ¿Cómo se llama la nueva partida? Di algo como 'nueva partida: El Mundo Perdido'."
        return handle_new(title)
    if intent == "chat_history":
        return handle_chat_history()

    return "🤷 No entendí el comando. Prueba: 'qué partidas hay', 'guarda esta', 'carga <nombre>', 'nueva partida: <título>'."


def main():
    parser = argparse.ArgumentParser(description="Dungeon chat command parser")
    parser.add_argument("action", choices=["parse"])
    parser.add_argument("text", help="Player message to parse")
    args = parser.parse_args()

    result = parse_command(args.text)
    print(result)


if __name__ == "__main__":
    main()
