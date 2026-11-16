# inat-creature-crop

Finds the moths, butterflies, other bugs and birds in your photos, turns each one to a natural pose,
and crops each to its own 512 × 512 square. Jev ([TypeSafe](https://docs.typesafe.ai/primitives/box)) does the finding.

How each animal is turned:
- **Moth:** head up.
- **Butterfly, seen from above (wings open):** head up.
- **Other insects, or a butterfly with its wings closed:** feet at the bottom. If its feet aren't visible, its head goes to whichever side (left or right) is closer.
- **Birds and other animals:** cropped but not rotated, since photos of them are usually level already.
- **Tiny or unclear subjects** (Jev can't tell which end is the head): cropped but not rotated.

A photo with several animals gives one crop each (up to 3; change this in `prompt.json`).

Works on Mac and Windows with JPG, PNG, WEBP and camera RAW files (CR2, CR3, NEF, ARW, DNG, RAF, ORF, RW2 and others).

> **Never coded before?** Follow the step-by-step [GETTING_STARTED.md](GETTING_STARTED.md) guide instead.

## 1. One-time setup

You need:
- **Python 3.10 or newer.** Mac: `python3 --version`. Windows: `py --version`. If it's missing, install it from https://www.python.org/downloads/ (on Windows, tick "Add Python to PATH").
- **A Jev API key.** Get one at https://console.typesafe.ai/keys.

Then open a terminal in this folder (Mac: Terminal; Windows: PowerShell) and run:

**Mac**
```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

**Windows**
```
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

### Where to put your API key

Open the new `.env` file in this folder with any text editor and paste your key after the `=`:

```
TYPESAFE_API_KEY=your-key-here
```

Save it. `.env` is never committed to git, so your key stays on your machine.
(Instead of the file, you can also set a `TYPESAFE_API_KEY` environment variable.)

## 2. Running it

1. Put your photos in the `input/` folder.
2. Run:

   **Mac:** `.venv/bin/python run.py`
   **Windows:** `.venv\Scripts\python run.py`

3. Results go to `output/`:
   - `output/final/`: **start here.** Every crop, grouped by creature and ranked best-first: `g0084_1_IMG_6120_crop.jpg` is group 84's best photo, `g0084_2_...` its 2nd best, and so on. Brightness-fixed versions are used where they exist.
   - `output/crops/`: the rotated square crops, ready to upload. `<name>_crop.jpg`, plus `<name>_crop2.jpg` and `_crop3.jpg` if there were more animals.
   - `output/crops_adjusted/`: brightened or contrast-fixed copies of any crops where the animal was too dark, too bright or flat. Only crops that needed fixing appear here, and the originals stay in `crops/`.
   - `output/boxes/`: `<name>_boxes.jpg` previews of what Jev found, for checking (green = whole animal, pink = head, cyan = feet, yellow = head direction).

Running it again only processes **new** photos. Photos that are already done (they have a `<name>_boxes.jpg` in `output/boxes/`) are skipped, so you can move crops out for upload without them being redone.
To redo a photo, delete its `_boxes.jpg` and its crops, then run again.

### Brightness and contrast fixing

This runs automatically on new crops. It doesn't use Jev, so it's free. Each crop is measured in the middle, where the animal is,
rather than on the background. If the animal is too dark, too bright or low-contrast, the light levels are stretched
and the midtones nudged (colours are kept), and the result is saved to `output/crops_adjusted/`.

To run it again on all existing crops (for example after changing the thresholds at the top of `adjust.py`):

**Mac:** `.venv/bin/python adjust.py`
**Windows:** `.venv\Scripts\python adjust.py`

### Grouping and ranking (`output/final/`)

This runs automatically at the end of every run, and costs nothing (no Jev). Two crops count as the same creature
when they were taken within 90 seconds of each other and the animal's shape and colours match. Crops from the same
photo are never grouped together. Within a group, the sharpest crop ranks first. Settings are at the top of `rank.py`.
They're cautious on purpose: you may get the same bird split across a few groups, but different moths on the
same wall shouldn't be merged. `final/` is rebuilt from scratch every time.

To rerun it on its own: **Mac:** `.venv/bin/python rank.py` · **Windows:** `.venv\Scripts\python rank.py`

## Troubleshooting

- **"No API key"**: `.env` is missing, or the key isn't after `TYPESAFE_API_KEY=`.
- **"No photos found"**: put the files directly in `input/`, not in a subfolder.
- **"no animal found"**: check `output/boxes/<name>_boxes.jpg`. Jev may have missed it, or its confidence was below `min_confidence`.
- **"max_tokens_exceeded"**: lower `send_px` or `max_subjects` in `prompt.json`.
- **401 / 403 errors**: the key is wrong or expired. Make a new one in the console.
- **Mac: `python3: command not found`** / **Windows: `py` not recognised**: install Python (see setup).

## Customising

- **`prompt.json` settings:** `max_subjects` (most animals per photo, default 3), `send_px` (size sent to Jev, default 800, and smaller is cheaper), `crop_px` (output size, default 512), `min_confidence` (skip weak detections), `rotate_kinds` (which animals get rotated), `min_head_offset` (how clear the head has to be before it rotates), and the animal types in `kind`.
- **Rotation rules:** see `pose_angle` in `boxes.py`.
- **Cost:** one Jev request per photo, whatever the number of animals. Jev charges per input token, and the image is most of that.
- The logic lives in `boxes.py`. `run_boxes.ipynb` does the same job in Jupyter, with inline previews.
- Notes: Jev boxes are axis-aligned, with 0–1 coordinates. Photos are turned upright using EXIF before they're sent. Crops are cut from the full-resolution photo.
