"""Find each animal in every photo in input/, rotate it to a natural pose and square-crop it into output/crops/ (debug previews go to output/boxes/).

Usage:  python run.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import adjust  # noqa: E402
import boxes  # noqa: E402

HERE = Path(__file__).parent
IN, OUT = HERE / "input", HERE / "output"
CROPS, BOXES = OUT / "crops", OUT / "boxes"
EXTS = boxes.PHOTO_EXTS


def tidy_old_layout():
    """Older versions wrote everything straight into output/. Move those into crops/ and boxes/."""
    for f in OUT.glob("*.jpg"):
        dest = BOXES if f.stem.endswith("_boxes") else CROPS if "_crop" in f.stem else None
        if dest and not (dest / f.name).exists():
            f.rename(dest / f.name)


def main():
    IN.mkdir(exist_ok=True)
    CROPS.mkdir(parents=True, exist_ok=True)
    BOXES.mkdir(parents=True, exist_ok=True)
    tidy_old_layout()
    if not boxes.API_KEY:
        sys.exit("No API key. Copy .env.example to .env and put your key after TYPESAFE_API_KEY=")
    photos = sorted(p for p in IN.iterdir() if p.suffix.lower() in EXTS)
    if not photos:
        sys.exit(f"No photos found. Put photos (JPG/PNG/WEBP or camera RAW) in {IN}")
    # The boxes preview marks a photo as done, so crops can be moved out for upload without being redone.
    done = [p for p in photos if (BOXES / f"{p.stem}_boxes.jpg").exists() or (CROPS / f"{p.stem}_crop.jpg").exists()]
    photos = [p for p in photos if p not in done]
    if done:
        print(f"Skipping {len(done)} already done (to redo one, delete its file in output/boxes/ and output/crops/)")
    if not photos:
        sys.exit("Nothing new to process.")
    print(f"{len(photos)} photo(s) to process")
    ok = 0
    for i, path in enumerate(photos, 1):
        tag = f"[{i}/{len(photos)}] {path.name}"
        try:
            r = boxes.process(path)
        except Exception as e:
            print(f"{tag}: FAILED - {e}")
            continue
        r["preview"].save(BOXES / f"{path.stem}_boxes.jpg", quality=85)
        if not r["subjects"]:
            print(f"{tag}: no animal found (see output/boxes/{path.stem}_boxes.jpg)")
            continue
        for j, s in enumerate(r["subjects"], 1):
            name = f"{path.stem}_crop.jpg" if j == 1 else f"{path.stem}_crop{j}.jpg"
            s["crop"].save(CROPS / name, quality=92)
            turn = f" {s['angle']:+.0f} deg" if s["angle"] else ""
            fixed, issues, _, _ = adjust.adjust(s["crop"])
            if fixed is not None:
                adjust.ADJ.mkdir(parents=True, exist_ok=True)
                fixed.save(adjust.ADJ / name, quality=92)
                turn += f", {'+'.join(issues)} -> also crops_adjusted/"
            print(f"{tag}: {s['kind']} ({s['view']} view), {s['rule']}{turn} -> output/crops/{name}")
        ok += 1
    print(f"Done: {ok}/{len(photos)} processed. Crops are in {CROPS}")


if __name__ == "__main__":
    main()
