"""Find each animal in every photo in input/, rotate it to a natural pose and square-crop it into output/.

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
    print(f"{len(photos)} photo(s) to process")
    ok = 0
    for i, path in enumerate(photos, 1):
        tag = f"[{i}/{len(photos)}] {path.name}"
        try:
            r = boxes.process(path)
        except Exception as e:
            print(f"{tag}: FAILED - {e}")
            continue
        r["preview"].save(OUT / f"{path.stem}_boxes.jpg", quality=85)
        if not r["subjects"]:
            print(f"{tag}: no animal found (see output/{path.stem}_boxes.jpg)")
            continue
        for j, s in enumerate(r["subjects"], 1):
            name = f"{path.stem}_crop.jpg" if j == 1 else f"{path.stem}_crop{j}.jpg"
            s["crop"].save(OUT / name, quality=92)
            turn = f" {s['angle']:+.0f} deg" if s["angle"] else ""
            print(f"{tag}: {s['kind']} ({s['view']} view), {s['rule']}{turn} -> output/{name}")
        ok += 1
    print(f"Done: {ok}/{len(photos)} processed into {OUT}")


if __name__ == "__main__":
    main()
