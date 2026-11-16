"""Fix too-dark, too-bright or flat crops so the animal is easier to identify. No Jev calls.

Each crop is cut around the animal's box with a small margin, so the animal fills the
middle of the crop. Brightness is measured there (not on the background), and the crop
is only changed if that region is clearly out of range. Colours are kept; only light
levels are stretched and the midtones nudged, with caps so nothing gets overcooked.

Usage:  python adjust.py      (reads output/crops/, writes changed ones to output/crops_adjusted/)
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).parent
CROPS, ADJ = HERE / "output" / "crops", HERE / "output" / "crops_adjusted"

# Thresholds on 0-1 luminance measured over the animal region.
DARK_MEDIAN, BRIGHT_MEDIAN = 0.28, 0.78   # median outside this range -> fix
MIN_RANGE = 0.45                           # 1st-99th percentile spread below this -> flat, fix
TARGET_MEDIAN = 0.45                       # midtones are nudged toward this
GAMMA_LIMITS = (0.55, 1.6)                 # cap on midtone change
CUTOFF = 0.5                               # % of darkest/brightest pixels allowed to clip when stretching


def animal_mask(size, margin=0.12):
    """Central region of a crop, where the animal is."""
    w, h = size
    m = Image.new("L", size, 0)
    m.paste(255, (round(w * margin), round(h * margin), round(w * (1 - margin)), round(h * (1 - margin))))
    return m


def measure(img, mask):
    lum = np.asarray(img.convert("L"), dtype=np.float32)[np.asarray(mask) > 0] / 255
    p1, p50, p99 = np.percentile(lum, [1, 50, 99])
    return float(p1), float(p50), float(p99)


def diagnose(p1, p50, p99):
    issues = []
    if p50 < DARK_MEDIAN:
        issues.append("dark")
    if p50 > BRIGHT_MEDIAN:
        issues.append("bright")
    if p99 - p1 < MIN_RANGE:
        issues.append("flat")
    return issues


def fix(img, mask):
    """Stretch levels (measured on the animal only, colours preserved), then nudge midtones."""
    out = ImageOps.autocontrast(img, cutoff=CUTOFF, mask=mask, preserve_tone=True)
    _, p50, _ = measure(out, mask)
    p50 = min(max(p50, 0.02), 0.98)
    gamma = np.log(TARGET_MEDIAN) / np.log(p50)          # out = in ** gamma puts the median at the target
    gamma = float(np.clip(gamma, *GAMMA_LIMITS))
    p1, _, _ = measure(img, mask)
    if gamma > 1 and p1 < 0.15:
        # Real blacks already exist, so "bright" means a dark animal against a bright sky or wall.
        # Darkening the midtones would bury the animal, so don't.
        gamma = 1.0
    if abs(gamma - 1) > 0.05:
        lut = [round(255 * (i / 255) ** gamma) for i in range(256)]
        out = out.point(lut * len(out.getbands()))
    return out


def adjust(img):
    """Returns (adjusted image or None if fine, issues list, before stats, after stats)."""
    img = img.convert("RGB")
    mask = animal_mask(img.size)
    before = measure(img, mask)
    issues = diagnose(*before)
    if not issues:
        return None, issues, before, None
    out = fix(img, mask)
    return out, issues, before, measure(out, mask)


def main():
    if not CROPS.exists():
        sys.exit(f"No crops found in {CROPS}. Run run.py first.")
    ADJ.mkdir(parents=True, exist_ok=True)
    files = sorted(CROPS.glob("*.jpg"))
    changed = 0
    for f in files:
        out, issues, before, after = adjust(Image.open(f))
        if out is None:
            continue
        out.save(ADJ / f.name, quality=92)
        changed += 1
        fmt = lambda s: f"median {s[1]:.2f}, range {s[2] - s[0]:.2f}"
        print(f"{f.name}: {'+'.join(issues)}  ({fmt(before)} -> {fmt(after)})")
    print(f"Done: adjusted {changed} of {len(files)} crops into {ADJ}")


if __name__ == "__main__":
    main()
