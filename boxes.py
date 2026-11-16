"""Jev helpers: find each animal in a photo, rotate it to a natural pose, square-crop it."""

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


def prepare(path, send_px=None):
    """Returns (full-res upright image for cropping, small JPEG bytes to send to Jev).

    The API ignores EXIF, so pixels are made upright first. The sent copy is kept small
    (default 800 px) so all the questions fit in Jev's token limit; fewer tokens also costs less.
    """
    full = open_photo(path)
    full.thumbnail((4000, 4000))
    img = full.copy()
    img.thumbnail((send_px or PROMPT.get("send_px", 800),) * 2)
    if min(img.size) < 280:
        s = 280 / min(img.size)
        img = img.resize((round(img.width * s), round(img.height * s)))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return full, buf.getvalue()


ORDINALS = ["largest", "2nd largest", "3rd largest", "4th largest", "5th largest"]
HEAD_UP_ALWAYS = {"moth"}           # always head up, whatever the view
HEAD_UP_FROM_ABOVE = {"butterfly"}  # head up only when seen from above (wings open)


def build_questions(prompt, ref):
    """Count question + one set of per-subject questions per slot, all in a single request."""
    fill = lambda s, n="": s.replace("{photo}", ref).replace("{n}", n)
    qs = {"count": {**prompt["count"], "instructions": fill(prompt["count"]["instructions"])}}
    for i in range(prompt["max_subjects"]):
        for k, q in prompt["per_subject"].items():
            qs[f"{k}_{i + 1}"] = {**q, "instructions": fill(q["instructions"], ORDINALS[i])}
    return qs


def ask_jev(jpeg, prompt=PROMPT):
    if not API_KEY:
        raise RuntimeError("No API key: put TYPESAFE_API_KEY=... in moth_crop/.env")
    ref = str(uuid.uuid4())
    payload = {
        "model": MODEL,
        "state": prompt["state"].replace("{photo}", ref),
        "questions": build_questions(prompt, ref),
        "assets": {ref: {"type": "image", "format": "jpg", "data_base64": base64.b64encode(jpeg).decode()}},
    }
    r = httpx.post(API_URL, json=payload, timeout=120,
                   headers={"Authorization": f"Bearer {API_KEY}", "TypeSafe-Danger-Zone-Images": "true"})
    if r.status_code >= 400:
        hint = " (try a lower send_px or max_subjects in prompt.json)" if "max_tokens" in r.text else ""
        raise RuntimeError(f"Jev returned {r.status_code}: {r.text[:300]}{hint}")
    return r.json()


def to_px(box, img):
    return (box["left"] * img.width, box["top"] * img.height, box["right"] * img.width, box["bottom"] * img.height)


def centre(px):
    return ((px[0] + px[2]) / 2, (px[1] + px[3]) / 2)


def direction(from_px, to_px_):
    """Clockwise degrees from 'up' of the vector from one box centre to another (screen coords)."""
    (ax, ay), (bx, by) = centre(from_px), centre(to_px_)
    dx, dy = bx - ax, by - ay
    if math.hypot(dx, dy) < 1:
        return None
    return math.degrees(math.atan2(dx, -dy))


def wrap(a):
    return (a + 180) % 360 - 180


def pose_angle(kind, view, obj_px, head_px, feet_px, prompt=PROMPT):
    """PIL rotate() angle (counter-clockwise degrees) and a label for the rule used.

    - kinds not in prompt["rotate_kinds"] (birds, mammals...): left as shot, since they're usually level already
    - moth: head points up
    - butterfly seen from above (wings open): head points up
    - other insects, or a butterfly in profile: feet point down if visible, else head to the nearer side
    - head too close to the body centre (tiny or ambiguous subject): left unchanged
    """
    if kind not in prompt.get("rotate_kinds", ["moth", "butterfly", "other insect or bug"]):
        return 0.0, "not rotated"
    w, h = obj_px[2] - obj_px[0], obj_px[3] - obj_px[1]
    (ox, oy), (hx, hy) = centre(obj_px), centre(head_px)
    if math.hypot(hx - ox, hy - oy) < prompt.get("min_head_offset", 0.2) * max(w, h) / 2:
        return 0.0, "head unclear, not rotated"
    head = direction(obj_px, head_px)
    if kind in HEAD_UP_ALWAYS or (kind in HEAD_UP_FROM_ABOVE and view == "top"):
        return wrap(head), "head up"
    if feet_px is not None:
        feet = direction(obj_px, feet_px)
        if feet is not None:
            return wrap(feet - 180), "feet down"
    # rotating CCW by (head - 90) puts the head at the right; (head + 90) at the left; pick the smaller turn
    right, left = wrap(head - 90), wrap(head + 90)
    return (right, "head right") if abs(right) <= abs(left) else (left, "head left")


def square_crop(img, obj_px, angle, pad=0.08, size=512):
    """Rotate about the object centre, then take a square crop around it."""
    cx, cy = centre(obj_px)
    w, h = obj_px[2] - obj_px[0], obj_px[3] - obj_px[1]
    a = math.radians(angle)
    rw = abs(w * math.cos(a)) + abs(h * math.sin(a))
    rh = abs(w * math.sin(a)) + abs(h * math.cos(a))
    side = max(rw, rh) * (1 + 2 * pad)
    rotated = img.rotate(angle, resample=Image.BICUBIC, center=(cx, cy), fillcolor=(255, 255, 255))
    half = side / 2
    crop = rotated.crop((round(cx - half), round(cy - half), round(cx + half), round(cy + half)))
    return crop.resize((size, size), Image.LANCZOS)


def preview(img, subjects):
    out = img.copy()
    d = ImageDraw.Draw(out)
    lw = max(3, img.width // 300)
    for i, s in enumerate(subjects, 1):
        d.rectangle(s["obj_px"], outline="lime", width=lw)
        d.rectangle(s["head_px"], outline="magenta", width=lw)
        d.line([centre(s["obj_px"]), centre(s["head_px"])], fill="yellow", width=lw)
        if s["feet_px"]:
            d.rectangle(s["feet_px"], outline="cyan", width=lw)
        d.text((s["obj_px"][0] + lw * 2, s["obj_px"][1] + lw * 2), f"{i} {s['kind']}", fill="lime")
    return out


def _small(im, px=1600):
    im.thumbnail((px, px))
    return im


def _choice(ans, key):
    return (ans.get(key) or {}).get("choice")


def process(path, prompt=PROMPT):
    """Returns {photo, count, subjects:[{kind, view, rule, angle, crop, ...}], preview, raw}."""
    img, jpeg = prepare(path)
    resp = ask_jev(jpeg, prompt)
    ans = resp["answers"]
    count_label = _choice(ans, "count") or "1"
    n = {"0": 0, "1": 1, "2": 2}.get(count_label, prompt["max_subjects"])
    n = min(n, prompt["max_subjects"])

    subjects = []
    for i in range(1, n + 1):
        obj = ans.get(f"object_{i}") or {}
        if not obj.get("box") or (obj.get("confidence") or 0) < prompt["min_confidence"]:
            continue
        kind, view = _choice(ans, f"kind_{i}"), _choice(ans, f"view_{i}")
        obj_px = to_px(obj["box"], img)
        head_px = to_px(ans[f"head_{i}"]["box"], img)
        feet_ok = (ans.get(f"feet_visible_{i}") or {}).get("noul", 0) >= 0.5
        feet_px = to_px(ans[f"feet_{i}"]["box"], img) if feet_ok and ans.get(f"feet_{i}") else None
        angle, rule = pose_angle(kind, view, obj_px, head_px, feet_px, prompt)
        subjects.append({
            "kind": kind, "view": view, "rule": rule, "angle": round(angle, 1),
            "confidence": obj.get("confidence"),
            "obj_px": obj_px, "head_px": head_px, "feet_px": feet_px,
            "crop": square_crop(img, obj_px, angle, size=prompt.get("crop_px", 512)),
        })
    return {"photo": Path(path).name, "model": resp.get("model"), "count": count_label,
            "subjects": subjects, "preview": _small(preview(img, subjects)), "raw": ans}
