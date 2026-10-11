# Playing with any coding agent

The Dungeon Master is just **instructions + Python scripts**. Any agent that can read an
`AGENTS.md`-style context file and run shell commands can be the DM. The game table is the
[`play/`](../play) folder:

```
play/
├── AGENTS.md              # DM instructions (read by Pi, Codex, opencode, ...)
├── CLAUDE.md              # → imports AGENTS.md for Claude Code
├── .gemini/settings.json  # → tells Gemini CLI to read AGENTS.md
├── .pi/prompts/           # Pi slash commands: /play, /new-campaign, /save, /recap
└── campaigns/             # your saves (created on first game, git-ignored)
```

Start your agent **inside `play/`**, not at the repo root. That way the DM instructions apply only
at the table, and the agent works normally everywhere else in the repo.

Requirements: **Python 3.10+** (standard library only) and the agent of your choice.

Saves go to `play/` by default. Set `DND_DATA_DIR=/some/path` to keep them elsewhere. The old
Hermes/Docker layout (`/opt/data`) is still detected automatically.

---

## Pi (recommended for free and local models)

[Pi](https://pi.dev) is a minimal open-source coding agent that works with many providers.

```bash
curl -fsSL https://pi.dev/install.sh | sh      # or: npm install -g @earendil-works/pi-coding-agent
cd play
pi                                             # first run: accept "trust project" so /play etc. load
```

Inside Pi, type `/play` to start or resume a game, or `/new-campaign The Sunken Crown` to start a
new one. You can also just talk to it. `/save` writes a checkpoint and `/recap` summarises the story.
`/model` switches models at any time.

### Option A — OpenRouter free models (no credit card)

1. Create an account at <https://openrouter.ai> and generate an API key.
2. `export OPENROUTER_API_KEY=sk-or-...` (or run `/login` inside Pi).
3. List free models that Pi knows about:
   ```bash
   pi --list-models ":free"
   ```
4. Start with a free model and let **Ctrl+P** cycle through the others:
   ```bash
   pi --model "openrouter/nvidia/nemotron-3-super-120b-a12b:free" --models "openrouter/*:free"
   ```

What to know about the free tier:

- **50 requests per day** per account (1000/day after a one-time $10 top-up), max 20 per minute.
  **Every tool call is a request.** A turn with a dice roll costs 2 requests, and a combat round
  can cost 4–5. `AGENTS.md` tells the DM to save requests, but plan for roughly 15–25 player turns
  per day.
- Free models are often **rate-limited upstream** (`429 ... temporarily rate-limited upstream`).
  If that happens, press Ctrl+P to switch to another `:free` model and keep playing. The
  campaign lives in files, so nothing is lost.
- The DM needs **tool calling** to roll dice, and models in Pi's list support it. Bigger models
  narrate noticeably better. Tested working: `nvidia/nemotron-3-super-120b-a12b:free`.
- The free model line-up changes often. Check the list again if a model disappears.

### Option B — Google Gemini API key (free tier)

Get a key at <https://aistudio.google.com>, `export GEMINI_API_KEY=...`, then pick a Gemini model
with `/model`. The free tier has its own daily limits, so it works well as a backup when OpenRouter
runs out.

### Option C — Local models with Ollama (offline, no limits)

1. Install [Ollama](https://ollama.com) and pull a model **that supports tool calling**:
   ```bash
   ollama pull qwen3:8b        # ~5 GB, runs on most laptops with 16 GB RAM
   # better narration if you have the hardware: qwen3:14b, gpt-oss:20b
   ```
2. **Raise the context window.** Ollama's default context is too small for an agent's system
   prompt plus tools, and the model will "forget" its instructions:
   ```bash
   OLLAMA_CONTEXT_LENGTH=16384 ollama serve
   ```
3. Register Ollama with Pi by copying [`docs/pi-models.ollama.json`](pi-models.ollama.json) to
   `~/.pi/agent/models.json`. If you already have that file, merge the `ollama` entry into it.
   Keep `contextWindow` equal to `OLLAMA_CONTEXT_LENGTH` so Pi compacts the conversation before
   Ollama silently truncates it.
4. Play:
   ```bash
   cd play
   pi --model "ollama/qwen3:8b"
   ```

Small local models follow the rules less reliably than large cloud models. They may forget to roll
or to save. If that happens, remind the DM (*"roll for it"*, *"save the game"*). A good classroom
exercise is to compare how models of different sizes handle the same `AGENTS.md`.

---

## Claude Code

```bash
cd play
claude
```

`play/CLAUDE.md` imports `AGENTS.md`. Then just say *"let's play"*.

## Gemini CLI

```bash
cd play
gemini
```

`play/.gemini/settings.json` points Gemini CLI at `AGENTS.md`.

## Codex, opencode, Cursor, and other agents

Most agents read `AGENTS.md` natively. Start them in `play/`.

## Hermes / Docker (original setup)

The Hermes Profile Distribution and the Docker setup in the main README still work unchanged.
They use `SOUL.md`, `templates/`, and `/opt/data`.
