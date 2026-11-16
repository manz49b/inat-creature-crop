"""Crop every photo in input/ so the target's head points up. Results go to output/.

Usage:  python run.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import boxes  # noqa: E402

HERE = Path(__file__).parent
IN, OUT = HERE / "input", HERE / "output"
EXTS = boxes.PHOTO_EXTS


def main():
    IN.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    if not boxes.API_KEY:
        sys.exit("No API key. Copy .env.example to .env and put your key after TYPESAFE_API_KEY=")
    photos = sorted(p for p in IN.iterdir() if p.suffix.lower() in EXTS)
    if not photos:
        sys.exit(f"No photos found. Put photos (JPG/PNG/WEBP or camera RAW) in {IN}")
    done = [p for p in photos if (OUT / f"{p.stem}_crop.jpg").exists()]
    photos = [p for p in photos if p not in done]
    if done:
        print(f"Skipping {len(done)} already in output/ (delete a *_crop.jpg there to redo it)")
    if not photos:
        sys.exit("Nothing new to process.")
    print(f"{len(photos)} photo(s), target: {boxes.PROMPT['target']}")
    ok = 0
    for i, path in enumerate(photos, 1):
        try:
            r = boxes.process(path)
        except Exception as e:
            print(f"[{i}/{len(photos)}] {path.name}: FAILED - {e}")
            continue
        r["crop"].save(OUT / f"{path.stem}_crop.jpg", quality=92)
        r["preview"].save(OUT / f"{path.stem}_boxes.jpg", quality=85)
        warn = "" if r["present"] in (True, "yes", "Yes") else "  (target may not be in photo)"
        print(f"[{i}/{len(photos)}] {path.name}: rotated {r['angle']} deg -> output/{path.stem}_crop.jpg{warn}")
        ok += 1
    print(f"Done: {ok}/{len(photos)} cropped into {OUT}")


if __name__ == "__main__":
    main()
