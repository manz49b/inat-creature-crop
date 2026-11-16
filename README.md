# moth_crop

Turns photos of moths so the head points up, then crops each one to a 512 × 512 square.
Jev ([TypeSafe](https://docs.typesafe.ai/primitives/box)) finds the moth and its head in each photo.

Works on Mac and Windows with JPG, PNG, WEBP and camera RAW files (CR2, CR3, NEF, ARW, DNG, RAF, ORF, RW2 and others).

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
   - `<name>_crop.jpg`: the rotated square crop
   - `<name>_boxes.jpg`: what Jev found (green = whole moth, pink = head, yellow = rotation line)

Running it again only processes **new** photos. Any photo that already has a `<name>_crop.jpg` in `output/` is skipped.
To redo a photo, delete its crop from `output/` and run again.

## Troubleshooting

- **"No API key"**: `.env` is missing, or the key isn't after `TYPESAFE_API_KEY=`.
- **"No photos found"**: put the files directly in `input/`, not in a subfolder.
- **"(target may not be in photo)"**: Jev didn't confirm there was a moth, so check `<name>_boxes.jpg`.
- **401 / 403 errors**: the key is wrong or expired. Make a new one in the console.
- **Mac: `python3: command not found`** / **Windows: `py` not recognised**: install Python (see setup).

## Customising

- **Something other than moths?** Change `target` in `prompt.json`, e.g. `"the beetle"`.
- The logic lives in `boxes.py`. `run_boxes.ipynb` does the same job in Jupyter, with inline previews.
- Notes: Jev boxes are axis-aligned, with 0–1 coordinates. Photos are turned upright using EXIF and resized to 280–1568 px before they're sent.
