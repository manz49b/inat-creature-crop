# Getting started (no coding experience needed)

This tool takes your wildlife photos (moths, butterflies, bugs, birds) and makes a neat square crop of each
creature, ready to upload to iNaturalist. A moth gets turned so its head points up. If there are a few
creatures in one photo, each gets its own crop, up to 3.

It takes about 15 minutes to set up the first time. After that, it's one command.

---

## What is Jev?

Jev is an AI made by a company called TypeSafe. It can look at a photo and answer questions about it,
like "where is the moth?" and "where is its head?". This tool sends each photo to Jev, Jev draws boxes
around what it finds, and the tool uses those boxes to turn and crop the picture.

To use Jev you need an **API key**. It's like a password that lets the tool use Jev on your account.

### How much does it cost?

Hardly anything. Jev charges by how much it reads, and a photo costs a tiny fraction of a cent.
New accounts get **$5 of free credit**, which should cover many thousands of photos, so you most likely
won't pay anything to try it.

---

## Step 1: Install Python (one time)

Python is the free program this tool runs on.

- Go to **https://www.python.org/downloads/** and click the big yellow **Download Python** button.
- Open the file you downloaded and click through the installer.
  - **On Windows:** on the first screen, **tick the box "Add Python to PATH"** before clicking Install. This is important.

## Step 2: Download this tool (one time)

1. Go to **https://github.com/manz49b/inat-creature-crop**
2. Click the green **Code** button, then **Download ZIP**.
3. Find the ZIP in your Downloads folder and unzip it (double-click on Mac; right-click, then **Extract All** on Windows).
4. Move the unzipped folder somewhere easy, like your Documents folder.

## Step 3: Get your Jev API key (one time)

1. Go to **https://console.typesafe.ai/keys** and sign up or log in.
2. Create a new key and **copy** it. It's a long string of letters and numbers.
3. Keep it private, the way you would a password.

## Step 4: Open a terminal in the folder

The terminal is a window where you type commands. Don't worry: you'll only copy and paste.

- **Mac:** open the **Terminal** app (press Cmd + Space and type "Terminal"). Type `cd ` (with a space
  after it), drag the tool's folder into the Terminal window, then press **Enter**.
- **Windows:** open the tool's folder in File Explorer, click the address bar at the top, type
  `powershell` and press **Enter**.

## Step 5: Set it up (one time)

Copy and paste these lines into the terminal, pressing **Enter** after each one. Each can take a minute.

**Mac**
```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
open -e .env
```

**Windows**
```
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
notepad .env
```

The last line opens a small text file. Find this line:

```
TYPESAFE_API_KEY=
```

Paste your key straight after the `=`, with no spaces, then **save** and close the file.

## Step 6: Crop your photos (every time)

1. Put your photos in the **input** folder inside the tool's folder. Normal photos (JPG) and camera RAW files both work.
2. In the terminal, paste this and press **Enter**:

   **Mac:** `.venv/bin/python run.py`
   **Windows:** `.venv\Scripts\python run.py`

3. Open **output**, then **crops**. Those are your finished photos, ready to upload.
   If a photo was too dark or too bright, a fixed copy is also saved in **crops_adjusted**. Use whichever looks better.
   (The **boxes** folder next to it shows what Jev spotted. It's only for checking, so you can ignore it.)

Next time, you only need Step 4 (open the terminal in the folder) and Step 6.
Photos that are already done are skipped, so you can move your crops out to upload them and they won't be redone. To redo a photo, delete its picture in output/boxes (and any old crops of it).

---

## If something goes wrong

- **"python3" / "py" is not recognised:** Python isn't installed, or on Windows the "Add Python to PATH" box wasn't ticked. Reinstall it and tick the box.
- **"No API key":** the key isn't saved in the `.env` file. Repeat the end of Step 5.
- **"401" or "403":** the key is wrong. Copy it again from the TypeSafe website.
- **"No photos found":** put the photos directly in the input folder, not in a folder inside it.
- **A crop looks wrong:** look at the matching picture in output/boxes to see what Jev spotted.
