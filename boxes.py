"""Jev Box helpers: find an object + its head, rotate so the head points up, square-crop."""

import base64
import io
import json
import math
import os
import uuid
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageOps


HERE = Path(__file__).parent


def _load_env(path):
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"\''))


_load_env(HERE / ".env")
API_URL = os.environ.get("JEV_API_URL", "https://api.typesafe.ai/v1/systemone")
MODEL = os.environ.get("JEV_MODEL", "jev-latest")
API_KEY = os.environ.get("TYPESAFE_API_KEY") or os.environ.get("JEV_API_KEY")
PROMPT = json.loads((HERE / "prompt.json").read_text())


RAW_EXTS = {".cr2", ".cr3", ".nef", ".arw", ".dng", ".raf", ".orf", ".rw2", ".pef", ".srw"}
PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp"} | RAW_EXTS


def open_photo(path):
    """Open a JPG/PNG/WEBP, or decode a camera RAW file, as upright RGB pixels."""
    if Path(path).suffix.lower() in RAW_EXTS:
        import rawpy  # RAW decoding applies the camera's orientation itself
        with rawpy.imread(str(path)) as raw:
            return Image.fromarray(raw.postprocess(use_camera_wb=True))
    return ImageOps.exif_transpose(Image.open(path)).convert("RGB")


def prepare(path):
    """Upright pixels (API ignores EXIF), fit within 280-1568 px. Returns (image, jpeg bytes)."""
    img = open_photo(path)
    img.thumbnail((1568, 1568))
    if min(img.size) < 280:
        s = 280 / min(img.size)
        img = img.resize((round(img.width * s), round(img.height * s)))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return img, buf.getvalue()


def ask_jev(jpeg, prompt=PROMPT):
    ref = str(uuid.uuid4())
    fill = lambda s: s.replace("{target}", prompt["target"]).replace("{photo}", ref)
    payload = {
        "model": MODEL,
        "state": fill(prompt["state"]),
        "questions": {k: {**q, "instructions": fill(q["instructions"])} for k, q in prompt["questions"].items()},
        "assets": {ref: {"type": "image", "format": "jpg", "data_base64": base64.b64encode(jpeg).decode()}},
    }
    if not API_KEY:
        raise RuntimeError("No API key: put TYPESAFE_API_KEY=... in moth_crop/.env")
    r = httpx.post(API_URL, json=payload, timeout=90,
                   headers={"Authorization": f"Bearer {API_KEY}", "TypeSafe-Danger-Zone-Images": "true"})
    r.raise_for_status()
    return r.json()


def to_px(box, img):
    return (box["left"] * img.width, box["top"] * img.height, box["right"] * img.width, box["bottom"] * img.height)


def centre(px):
    return ((px[0] + px[2]) / 2, (px[1] + px[3]) / 2)


def head_up_angle(obj_px, head_px):
    """Degrees (PIL counter-clockwise) that turn the centre->head direction to straight up."""
    (ox, oy), (hx, hy) = centre(obj_px), centre(head_px)
    dx, dy = hx - ox, hy - oy
    if math.hypot(dx, dy) < 1:
        return 0.0
    # Screen y points down. Angle of the head direction, measured clockwise from "up".
    clockwise_from_up = math.degrees(math.atan2(dx, -dy))
    return clockwise_from_up  # rotating CCW by this brings it back to up


def square_crop(img, obj_px, angle, pad=0.08, size=512):
    """Rotate about the object centre so its head is up, then take a square crop around it."""
    cx, cy = centre(obj_px)
    w, h = obj_px[2] - obj_px[0], obj_px[3] - obj_px[1]
    # After rotation the axis-aligned box's extent is unknown; the half-diagonal is a safe bound,
    # but too loose. Use the larger of: rotated box extent.
    a = math.radians(angle)
    rw = abs(w * math.cos(a)) + abs(h * math.sin(a))
    rh = abs(w * math.sin(a)) + abs(h * math.cos(a))
    side = max(rw, rh) * (1 + 2 * pad)
    rotated = img.rotate(angle, resample=Image.BICUBIC, center=(cx, cy), fillcolor=(255, 255, 255))
    half = side / 2
    crop = rotated.crop((round(cx - half), round(cy - half), round(cx + half), round(cy + half)))
    return crop.resize((size, size), Image.LANCZOS)


def preview(img, obj_px, head_px):
    out = img.copy()
    d = ImageDraw.Draw(out)
    lw = max(3, img.width // 200)
    d.rectangle(obj_px, outline="lime", width=lw)
    d.rectangle(head_px, outline="magenta", width=lw)
    d.line([centre(obj_px), centre(head_px)], fill="yellow", width=lw)
    return out


def process(path):
    img, jpeg = prepare(path)
    resp = ask_jev(jpeg)
    ans = resp["answers"]
    obj_px, head_px = to_px(ans["object"]["box"], img), to_px(ans["head"]["box"], img)
    angle = head_up_angle(obj_px, head_px)
    return {
        "photo": Path(path).name,
        "model": resp.get("model"),
        "present": ans.get("present"),
        "object_conf": ans["object"].get("confidence"),
        "head_conf": ans["head"].get("confidence"),
        "angle": round(angle, 1),
        "preview": preview(img, obj_px, head_px),
        "crop": square_crop(img, obj_px, angle),
        "raw": ans,
    }
