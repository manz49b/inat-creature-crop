"""Group crops that show the same creature and rank each group best-first. No Jev calls.

Two crops are treated as the same creature when they were taken close together in time AND their
shape AND colours match. Crops from the same photo are never grouped (they're different
animals). Within a group, crops are ranked by sharpness on the animal, with a small penalty if the
crop needed brightness fixing. The best version of each crop is used: the fixed copy if there is one.

Output (everything is kept, ranked, nothing is deleted):
  output/final/g0001_1_IMG_6058_crop.jpg   <- group 1, best
  output/final/g0001_2_IMG_6059_crop.jpg   <- group 1, 2nd best
  ...

Usage:  python rank.py
"""
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

import adjust

HERE = Path(__file__).parent
IN = HERE / "input"
CROPS, ADJ, FINAL = HERE / "output" / "crops", HERE / "output" / "crops_adjusted", HERE / "output" / "final"

# Grouping settings, cautious by default: better to leave two photos of one moth apart than to merge two moths.
MAX_GAP_SECONDS = 90      # only compare crops taken within this many seconds of each other
MAX_HASH_DISTANCE = 85    # shape fingerprint difference (0-256): at or below this, the shapes match
MIN_COLOUR_MATCH = 0.85   # animal colour similarity (0-1): at or above this, the colours match
COMPARE_LAST = 3          # a crop must look like each of a group's last this-many members to join it
FIX_PENALTY = 0.9         # score multiplier for crops that needed brightness fixing


def source_stem(crop_path):
    return re.sub(r"_crop\d*$", "", crop_path.stem)


def taken_at(stem):
    """Capture time from the original photo's EXIF, else its file time."""
    for f in IN.glob(stem + ".*"):
        try:
            exif = Image.open(f).getexif()
            t = exif.get_ifd(0x8769).get(36867) or exif.get(306)
            if t:
                return datetime.strptime(t, "%Y:%m:%d %H:%M:%S").timestamp()
        except Exception:
            pass
        return f.stat().st_mtime
    return None


def fingerprint(img):
    """Difference hash on the animal region: 256 bits that change little between near-identical shots."""
    m = img.size[0] // 8
    g = np.asarray(img.crop((m, m, img.size[0] - m, img.size[1] - m)).convert("L").resize((17, 16)), dtype=np.int16)
    return (g[:, 1:] > g[:, :-1]).flatten()


def colours(img):
    """Normalised 4x4x4 RGB histogram of the animal itself (robust to pose changes).

    Pixels close to the background colour (the median of the crop's border) are left out, so a
    plain wall or sheet behind several different moths doesn't make them all look alike.
    """
    a = np.asarray(img.resize((64, 64)), dtype=np.int16)
    border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    bg = np.median(border, axis=0)
    fg = np.abs(a - bg).sum(axis=2) > 60
    fg[:6], fg[-6:], fg[:, :6], fg[:, -6:] = False, False, False, False
    px = a[fg] if fg.sum() > 100 else a[8:-8, 8:-8].reshape(-1, 3)
    q = px // 64
    h = np.bincount((q[:, 0] * 16 + q[:, 1] * 4 + q[:, 2]).ravel(), minlength=64).astype(float)
    return h / np.linalg.norm(h)


def sharpness(img):
    """Variance of the Laplacian on the animal region: higher = crisper detail."""
    m = img.size[0] // 6
    g = np.asarray(img.crop((m, m, img.size[0] - m, img.size[1] - m)).convert("L"), dtype=np.float32)
    lap = -4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:]
    return float(lap.var())


def main():
    crops = sorted(CROPS.glob("*.jpg"))
    if not crops:
        sys.exit(f"No crops in {CROPS}. Run run.py first.")
    print(f"Reading {len(crops)} crops...")
    items = []
    for c in crops:
        img = Image.open(c).convert("RGB")
        fixed = ADJ / c.name
        _, issues, _, _ = adjust.adjust(img)
        items.append({
            "crop": c, "src": source_stem(c), "time": taken_at(source_stem(c)),
            "hash": fingerprint(img), "col": colours(img),
            "score": sharpness(img) * (FIX_PENALTY if issues else 1.0),
            "best_file": fixed if fixed.exists() else c,
        })
    items.sort(key=lambda it: (it["time"] or 0, it["crop"].name))

    # Walk through in time order. A crop joins an open group only if it looks like ALL of that group's
    # last few members (not just one), so a long burst of different creatures can't chain together.
    def alike(a, b):
        # Shape AND colour must both match: different moths on the same wall often share one or the other.
        return int(np.count_nonzero(a["hash"] != b["hash"])) <= MAX_HASH_DISTANCE \
            and float(a["col"] @ b["col"]) >= MIN_COLOUR_MATCH

    groups = []
    for it in items:
        best = None
        for g in groups:
            last = g[-1]
            if it["time"] is None or last["time"] is None or it["time"] - last["time"] > MAX_GAP_SECONDS:
                continue
            recent = g[-COMPARE_LAST:]
            if any(m["src"] == it["src"] for m in g) or not all(alike(it, m) for m in recent):
                continue
            sim = np.mean([float(it["col"] @ m["col"]) for m in recent])
            if best is None or sim > best[0]:
                best = (sim, g)
        if best:
            best[1].append(it)
        else:
            groups.append([it])

    if FINAL.exists():
        shutil.rmtree(FINAL)
    FINAL.mkdir(parents=True)
    multi = 0
    for g, members in enumerate(sorted(groups, key=lambda m: m[0]["time"] or 0), 1):
        members.sort(key=lambda it: -it["score"])
        multi += len(members) > 1
        for rank, it in enumerate(members, 1):
            shutil.copy2(it["best_file"], FINAL / f"g{g:04d}_{rank}_{it['crop'].name}")
    print(f"Done: {len(items)} crops -> {len(groups)} creatures ({multi} with more than one photo) in {FINAL}")
    print("Best photo of each creature is the one with _1_ in its name.")


if __name__ == "__main__":
    main()
