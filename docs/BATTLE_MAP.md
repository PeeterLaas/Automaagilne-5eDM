# 🗺️ Battle map

A browser battle map that follows the combat tracker live. The agent moves tokens with ordinary
`combat_tracker.py` commands, and the players watch the map in a browser next to the terminal.
It works with every agent, needs no web server, and uses only Python's standard library.

```
play/
├── battle_map.html        # open once in a browser and leave it open (generated)
├── battle_map.js          # current battle, re-read every second (generated)
└── assets/                # your own images, git-ignored
    ├── maps/cave.jpg
    ├── maps/cave.jpg.grid.json   # remembered grid for that map
    └── tokens/goblin.png         # matched to "Goblin", "Goblin1", "Goblin2", …
```

## Quick start

```bash
cd play
python3 ../scripts/battle_map.py open          # opens battle_map.html in your browser
```

Then play as usual. When combat starts, the DM places tokens (`@C3` after a name) and moves them
with `combat_tracker.py move`. Instructions for the DM are already in `play/AGENTS.md`.

You can also try it by hand:

```bash
python3 ../scripts/combat_tracker.py init --party "Ana@C3,Rowan@C4" --party-hp 12 \
        --enemies "Goblin1:7:15:2@H6,Goblin2:7:15:2@I7,Ogre:59:11:-1:large@L9"
python3 ../scripts/combat_tracker.py move Ana E5 Goblin1 G6
python3 ../scripts/combat_tracker.py damage Goblin1 7
```

Without a map image you get a parchment grid (20×15 by default). Each token shows its art or its
initials, an HP bar, condition badges and whose turn it is. Defeated creatures are greyed out
and crossed.

**In the browser:**
- Click a token, then hover over a square to measure the distance in feet.
- *Show coordinates* labels every square.
- *DM view* reveals enemy HP and AC, which players don't see by default.
- *Show grid lines* hides the overlay when the map has its own grid printed on it.

## Map images

1. Put an image in `play/assets/maps/`.
2. Tell the tracker how many squares the map has:
   ```bash
   python3 ../scripts/combat_tracker.py map --image assets/maps/cave.jpg --grid 30x21
   ```
3. If the overlay doesn't line up with the printed grid, click **Calibrate grid…** in the browser.
   Set the column and row counts, then use **Pick corners**: click the top-left corner of the first
   square, then the bottom-right corner of the last one. Copy the command shown and run it. The grid
   is saved next to the image, so `--map assets/maps/cave.jpg` remembers it next time.

Tip: count squares along one edge and divide the image width by that count. If the result matches
the square size in pixels, the grid probably covers the whole image and needs no inset.

## Tokens

Token art is matched by name. For "Goblin2" the map looks for `assets/tokens/goblin2.png`, then
`goblin.png` (`.png`, `.webp`, `.jpg` and `.gif` all work). For one-off art use
`combat_tracker.py token Ana assets/tokens/elf-ranger.png`. Creatures without art get a coloured
initial: blue for PCs, red for enemies, amber for NPCs.

## Extracting from your own collection

`scripts/extract_assets.py` pulls images out of PDFs, zip/rar map packs and folders. Each run
writes a `_gallery.html` you can browse to pick the keepers.

```bash
# Maps: embedded page images from PDFs, images from zip/rar packs, folders (recursive)
python3 scripts/extract_assets.py maps "~/DnD/Lost Mine of Phandelver Maps.zip" "~/DnD/Dungeon Tiles/"

# Tokens: cut round and rectangular tokens off token sheets (PDF or scanned image)
python3 scripts/extract_assets.py tokens "~/DnD/Monster Tokens/"
```

The token cutter finds tokens on dark or light sheets with gaps between them, such as the classic
*Dungeon* magazine token sheets. Round tokens get a transparent circular crop. The gallery shows
the name printed under each token, so you can rename files to `goblin.png`, `wolf.png` and so on.
Sheets where images touch edge to edge can't be cut automatically; crop those by hand.

Requirements: `poppler-utils` (pdfimages, pdftoppm) for PDFs, `unrar` for .rar, and
[Pillow](https://pypi.org/project/pillow/) for tokens.

## ⚖️ Copyright

`play/assets/` is git-ignored on purpose. Most published maps and tokens are copyrighted:
- Official adventure maps and the *Dungeon* token sheets are licensed for **home game use**
  only. That's fine at your own table, but they must not go into a public repository or onto a
  shared drive.
- Commercial map packs and books are for the people who bought them.

For material you can share, for example with a class, use openly licensed sources:
- [game-icons.net](https://game-icons.net): thousands of monster silhouettes, CC BY 3.0.
- The SRD 5.1 / 5.2 monster stats, CC BY 4.0. They are available as data from
  [5e-bits/5e-database](https://github.com/5e-bits/5e-database).
- Maps you draw or generate yourself, or maps whose creators allow sharing. Check each licence
  and credit the authors.
