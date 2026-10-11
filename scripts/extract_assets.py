#!/usr/bin/env python3
"""
extract_assets.py — Pull map images and monster tokens out of your own PDFs,
zips and image folders into the battle map's asset folder.

The results are for YOUR table: assets/ is git-ignored. Check the licence of
anything you extract before sharing it with others.

Usage:
    # Maps: images from PDFs (one per page/embedded image), zip/rar map packs, folders
    python3 scripts/extract_assets.py maps "~/DnD/Maps.zip" "~/DnD/Dungeon Tiles/" --dest play/assets/maps

    # Tokens: cut round/rectangular tokens out of token sheets (PDF or image)
    python3 scripts/extract_assets.py tokens "~/DnD/Monster Tokens/" --dest play/assets/tokens

    Then open <dest>/_gallery.html, see which token is which, and rename the files
    to the monster's name (goblin.png, ogre.png …) so the battle map finds them.

Requirements: poppler-utils (pdfimages, pdftoppm) for PDFs, unrar for .rar,
and Pillow for `tokens` (pip install pillow).
"""

import argparse
import html
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from dnd_paths import DATA_DIR

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
MIN_MAP_SIDE = 500  # pixels; smaller images are icons, logos, decorations


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "image"


def _need(tool: str, package: str):
    if not shutil.which(tool):
        sys.exit(f"❌ '{tool}' not found. Install {package} (e.g. sudo apt install {package}).")


def _iter_sources(sources: list[str]):
    for src in sources:
        p = Path(src).expanduser()
        if not p.exists():
            print(f"⚠️  Not found: {p}")
            continue
        if p.is_dir():
            yield from sorted(f for f in p.rglob("*") if f.is_file())
        else:
            yield p


def _image_size(path: Path) -> tuple[int, int] | None:
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception:
        return None


def _unique(dest: Path, stem: str, ext: str) -> Path:
    out = dest / f"{stem}{ext}"
    n = 2
    while out.exists():
        out = dest / f"{stem}-{n}{ext}"
        n += 1
    return out


def _write_gallery(dest: Path, title: str, intro: str, names: list[str], labels: bool):
    figs = "\n".join(
        f'<figure><a href="{html.escape(n)}"><img src="{html.escape(n)}" loading="lazy" alt=""></a>'
        + (f'<img class="lbl" src="_labels/{html.escape(n)}" alt="">' if labels else "")
        + f"<figcaption>{html.escape(n)}</figcaption></figure>"
        for n in names
    )
    (dest / "_gallery.html").write_text(f"""<!doctype html><meta charset="utf-8">
<title>{title}</title>
<style>
 body{{background:#15120f;color:#eadfcc;font:13px system-ui,sans-serif;padding:16px}}
 main{{display:grid;grid-template-columns:repeat(auto-fill,minmax({150 if labels else 240}px,1fr));gap:12px}}
 figure{{margin:0;background:#1f1a15;border:1px solid #3a3128;border-radius:6px;padding:8px;text-align:center;
   overflow-wrap:anywhere}}
 img{{max-width:100%;max-height:{130 if labels else 200}px}} img.lbl{{display:block;margin:4px auto;max-height:40px}}
 code{{color:#e8b64c}}
</style>
<h1>{title}</h1>
<p>{intro}</p>
<main>{figs}</main>
""", encoding="utf-8")


# ── maps ──────────────────────────────────────────────────────────────────────

def _keep_image(path: Path, dest: Path, stem: str, min_side: int) -> Path | None:
    size = _image_size(path)
    if size and min(size) < min_side:
        return None
    out = _unique(dest, stem, path.suffix.lower())
    shutil.copy2(path, out)
    return out


def _maps_from_pdf(pdf: Path, dest: Path, min_side: int) -> list[Path]:
    _need("pdfimages", "poppler-utils")
    found = []
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdfimages", "-all", "-p", str(pdf), f"{tmp}/img"],
                       check=False, capture_output=True)
        for img in sorted(Path(tmp).iterdir()):
            if img.suffix.lower() not in IMAGE_EXTS:
                continue  # skip masks/odd formats (.ccitt, .jb2e, .ppm …)
            page = re.search(r"img-(\d+)-", img.name)
            stem = f"{_slug(pdf.stem)}-p{int(page.group(1)):03d}" if page else _slug(pdf.stem)
            out = _keep_image(img, dest, stem, min_side)
            if out:
                found.append(out)
    return found


def _maps_from_archive(arc: Path, dest: Path, min_side: int) -> list[Path]:
    found = []
    with tempfile.TemporaryDirectory() as tmp:
        if arc.suffix.lower() == ".zip":
            with zipfile.ZipFile(arc) as z:
                z.extractall(tmp)
        else:
            _need("unrar", "unrar")
            subprocess.run(["unrar", "x", "-idq", "-o+", str(arc), tmp + "/"], check=False)
        for f in sorted(Path(tmp).rglob("*")):
            if f.suffix.lower() in IMAGE_EXTS:
                out = _keep_image(f, dest, f"{_slug(arc.stem)}-{_slug(f.stem)}", min_side)
                if out:
                    found.append(out)
            elif f.suffix.lower() == ".pdf":
                found += _maps_from_pdf(f, dest, min_side)
    return found


def cmd_maps(args):
    dest = Path(args.dest).expanduser()
    dest.mkdir(parents=True, exist_ok=True)
    total = 0
    for src in _iter_sources(args.sources):
        ext = src.suffix.lower()
        if ext == ".pdf":
            got = _maps_from_pdf(src, dest, args.min_size)
        elif ext in (".zip", ".rar"):
            got = _maps_from_archive(src, dest, args.min_size)
        elif ext in IMAGE_EXTS:
            got = [o for o in [_keep_image(src, dest, _slug(src.stem), args.min_size)] if o]
        else:
            continue
        if got:
            print(f"🗺️  {src.name}: {len(got)} image(s)")
        total += len(got)
    _write_gallery(dest, "Map gallery",
                   "Delete what you don't need and give the keepers short names (cave.jpg). "
                   "Then: <code>combat_tracker.py map --image assets/maps/cave.jpg --grid 30x21</code>, "
                   "and fine-tune with <b>Calibrate grid</b> in the battle map.",
                   sorted(f.name for f in dest.iterdir() if f.suffix.lower() in IMAGE_EXTS), labels=False)
    print(f"\n✅ {total} map image(s) in {dest}")
    print(f"   Browse them: {dest / '_gallery.html'}")
    print("   Use one with: combat_tracker.py map --image assets/maps/<file> --grid <cols>x<rows>")


# ── tokens ────────────────────────────────────────────────────────────────────

def _load_pillow():
    try:
        from PIL import Image, ImageDraw, ImageFilter
        return Image, ImageDraw, ImageFilter
    except ImportError:
        sys.exit("❌ The 'tokens' command needs Pillow: pip install pillow")


def _pages(src: Path, dpi: int, tmp: Path) -> list[Path]:
    if src.suffix.lower() == ".pdf":
        _need("pdftoppm", "poppler-utils")
        prefix = tmp / _slug(src.stem)
        subprocess.run(["pdftoppm", "-r", str(dpi), "-png", str(src), str(prefix)], check=True)
        return sorted(tmp.glob(f"{prefix.name}*.png"))
    if src.suffix.lower() in IMAGE_EXTS:
        return [src]
    return []


def _components(mask: bytes, w: int, h: int):
    """Connected components (4-neighbour) → list of (x0, y0, x1, y1, pixel_count)."""
    seen = bytearray(w * h)
    out = []
    for start in range(w * h):
        if not mask[start] or seen[start]:
            continue
        seen[start] = 1
        stack = [start]
        x0, y0, x1, y1, n = w, h, 0, 0, 0
        while stack:
            i = stack.pop()
            y, x = divmod(i, w)
            n += 1
            x0, x1, y0, y1 = min(x0, x), max(x1, x), min(y0, y), max(y1, y)
            for j in (i - 1 if x else -1, i + 1 if x < w - 1 else -1, i - w, i + w):
                if 0 <= j < w * h and mask[j] and not seen[j]:
                    seen[j] = 1
                    stack.append(j)
        out.append((x0, y0, x1 + 1, y1 + 1, n))
    return out


def _split(mask: bytes, w: int, box, min_part: int):
    """Split a box at an empty band of rows/columns that leaves a token-sized piece on both
    sides (neighbouring tokens can touch the same blob after closing dotted borders)."""
    x0, y0, x1, y1 = box
    for axis in ("y", "x"):
        if axis == "y":
            prof = [sum(mask[y * w + x0: y * w + x1]) for y in range(y0, y1)]
        else:
            prof = [sum(mask[y * w + x] for y in range(y0, y1)) for x in range(x0, x1)]
        gaps = [i for i, v in enumerate(prof) if v == 0 and min_part <= i < len(prof) - min_part]
        if gaps:
            cut = gaps[len(gaps) // 2]
            if axis == "y":
                parts = [(x0, y0, x1, y0 + cut), (x0, y0 + cut + 1, x1, y1)]
            else:
                parts = [(x0, y0, x0 + cut, y1), (x0 + cut + 1, y0, x1, y1)]
            return [b for part in parts for b in _split(mask, w, _shrink(mask, w, part), min_part)]
    return [box]


def _shrink(mask: bytes, w: int, box):
    """Tighten a box to the foreground pixels inside it."""
    x0, y0, x1, y1 = box
    rows = [y for y in range(y0, y1) if any(mask[y * w + x0: y * w + x1])]
    cols = [x for x in range(x0, x1) if any(mask[y * w + x] for y in range(y0, y1))]
    if not rows or not cols:
        return (x0, y0, x0, y0)
    return (cols[0], rows[0], cols[-1] + 1, rows[-1] + 1)


def _find_tokens(page, Image, ImageFilter):
    """Bounding boxes (in page pixels) of tokens on a dark or light background."""
    work_w = 700
    scale = work_w / page.width
    small = page.convert("L").resize((work_w, max(1, round(page.height * scale))))
    w, h = small.size
    hist = small.histogram()
    acc, median = 0, 0
    for median, count in enumerate(hist):
        acc += count
        if acc >= w * h / 2:
            break
    dark_bg = median < 110
    fg = small.point((lambda v: 255 if v > median + 40 else 0) if dark_bg
                     else (lambda v: 255 if v < median - 40 else 0))
    fg = fg.filter(ImageFilter.MaxFilter(3))  # close dotted borders
    mask = bytes(1 if v else 0 for v in fg.tobytes())

    boxes = []
    for x0, y0, x1, y1, _ in _components(mask, w, h):
        if x1 - x0 < w * 0.04 or y1 - y0 < w * 0.04:
            continue
        for bx0, by0, bx1, by1 in _split(mask, w, (x0, y0, x1, y1), round(w * 0.04)):
            bw, bh = bx1 - bx0, by1 - by0
            if bw < w * 0.05 or bh < w * 0.05:            # labels, specks
                continue
            if not 0.4 <= bw / bh <= 2.5:                 # paragraphs, header lines
                continue
            filled = sum(sum(mask[y * w + bx0: y * w + bx1]) for y in range(by0, by1))
            if filled / (bw * bh) < 0.45:                 # sparse = text block
                continue
            if bx0 <= 1 or by0 <= 1 or bx1 >= w - 1 or by1 >= h - 1:  # page border / scan margin
                continue
            if bw > w * 0.6 or bh > h * 0.6:
                continue
            boxes.append(tuple(round(v / scale) for v in (bx0, by0, bx1, by1)))
    boxes.sort(key=lambda b: (round(b[1] / (page.width * 0.05)), b[0]))  # reading order
    return boxes


def cmd_tokens(args):
    Image, ImageDraw, ImageFilter = _load_pillow()
    dest = Path(args.dest).expanduser()
    labels_dir = dest / "_labels"
    labels_dir.mkdir(parents=True, exist_ok=True)
    gallery = []

    with tempfile.TemporaryDirectory() as tmpdir:
        for src in _iter_sources(args.sources):
            pages = _pages(src, args.dpi, Path(tmpdir))
            for page_no, page_path in enumerate(pages, 1):
                page = Image.open(page_path).convert("RGB")
                boxes = _find_tokens(page, Image, ImageFilter)
                stem_base = _slug(src.stem) + (f"-p{page_no}" if len(pages) > 1 else "")
                for i, (x0, y0, x1, y1) in enumerate(boxes, 1):
                    tok = page.crop((x0, y0, x1, y1))
                    bw, bh = tok.size
                    round_tok = 0.85 <= bw / bh <= 1.18
                    if round_tok:
                        side = min(bw, bh)
                        tok = tok.crop(((bw - side) // 2, (bh - side) // 2,
                                        (bw - side) // 2 + side, (bh - side) // 2 + side)).convert("RGBA")
                        alpha = Image.new("L", tok.size, 0)
                        ImageDraw.Draw(alpha).ellipse((0, 0, side - 1, side - 1), fill=255)
                        tok.putalpha(alpha)
                    if max(tok.size) > args.max_size:
                        f = args.max_size / max(tok.size)
                        tok = tok.resize((round(tok.width * f), round(tok.height * f)), Image.LANCZOS)
                    name = f"{stem_base}-{i:02d}.png"
                    tok.save(dest / name)
                    # The printed name usually sits just below the token.
                    label = page.crop((max(0, x0 - bw // 4), y1,
                                       min(page.width, x1 + bw // 4), min(page.height, y1 + bh // 3)))
                    label.save(labels_dir / name)
                    gallery.append((name, src.name))
                print(f"🧩 {src.name}{f' p{page_no}' if len(pages) > 1 else ''}: {len(boxes)} token(s)")

    _write_gallery(dest, "Token gallery",
                   "Rename each file to the monster's name (e.g. <code>goblin.png</code>): the battle map "
                   "matches tokens to combatants by name (\"Goblin2\" uses goblin2.png, else goblin.png). "
                   "Delete the ones you don't need. The strip under each token is the label printed on the sheet.",
                   [n for n, _ in gallery], labels=True)
    print(f"\n✅ {len(gallery)} token(s) in {dest}")
    print(f"   Open {dest / '_gallery.html'} to see and rename them.")


def main():
    parser = argparse.ArgumentParser(description="Extract maps and tokens from your own files")
    sub = parser.add_subparsers(dest="command", required=True)

    m = sub.add_parser("maps", help="Extract map images from PDFs, zip/rar packs and folders")
    m.add_argument("sources", nargs="+")
    m.add_argument("--dest", default=str(DATA_DIR / "assets" / "maps"))
    m.add_argument("--min-size", type=int, default=MIN_MAP_SIDE,
                   help=f"skip images whose shorter side is below this (default {MIN_MAP_SIDE}px)")

    t = sub.add_parser("tokens", help="Cut tokens out of token sheets")
    t.add_argument("sources", nargs="+")
    t.add_argument("--dest", default=str(DATA_DIR / "assets" / "tokens"))
    t.add_argument("--dpi", type=int, default=200, help="PDF render resolution (default 200)")
    t.add_argument("--max-size", type=int, default=256, help="max token size in px (default 256)")

    args = parser.parse_args()
    {"maps": cmd_maps, "tokens": cmd_tokens}[args.command](args)


if __name__ == "__main__":
    main()
