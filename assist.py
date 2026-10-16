"""Helpers for the Auto Thumbnail Maker UI (no image processing here).

- build_bg_prompt(): ready-to-paste prompt for ChatGPT / Gemini so the user can
  generate a cinematic, text-free background that leaves room for our title + character.
- quality_notes(): warns when uploaded images are too small / not cut-outs, which is the
  most common reason a thumbnail looks blurry or amateur.
"""
import io

from PIL import Image

MOODS = {
    "Epic sunset": "warm golden-orange sunset sky, glowing sun rays, orange and teal color grading",
    "Neon purple": "purple and electric-blue neon glow, magical glowing particles, dark moody background",
    "Danger red": "dark ominous sky, red and black palette, fire and floating embers, intense dramatic atmosphere",
    "Fresh adventure": "bright blue sky, lush green landscape, soft clouds, cheerful vibrant colors",
    "Underwater": "deep blue and cyan underwater scene, god rays from above, bubbles, glowing sea life",
    "Nether lava": "glowing orange lava, dark rocky cave, smoke and hot embers, strong orange rim light",
}

_BIG_HEADLINE = ("Keep the {empty} half of the image calmer and darker (a big title goes there). "
                 "Put the main landmark or action toward the {busy} side; a character will be added there.")
_SMALL_LABEL = ("Keep the top-left area calm (a short label goes there). Put the main landmark or action "
                "across the middle, and keep the {busy} side lower area open for a large character.")
_VERSUS = ("Symmetrical composition with a clear, open center. Left and right halves have matching "
           "lighting; characters will be added on the left and the right.")


def build_bg_prompt(idea, mood="Epic sunset", game="Minecraft", layout="Small label", side="Right"):
    """Return an English prompt to paste into ChatGPT / Gemini image generation."""
    idea = " ".join((idea or "").split()) or "an epic dramatic scene"
    game = " ".join((game or "").split())
    mood_text = MOODS.get(mood, MOODS["Epic sunset"])
    busy = "right" if side.lower() == "right" else "left"
    empty = "left" if busy == "right" else "right"

    if layout == "Versus":
        comp = _VERSUS
    elif layout == "Big headline":
        comp = _BIG_HEADLINE.format(empty=empty, busy=busy)
    else:
        comp = _SMALL_LABEL.format(busy=busy)

    game_part = f" in {game} style" if game else ""
    return (
        f"Create a cinematic YouTube thumbnail BACKGROUND image, 16:9 landscape (1920x1080). "
        f"Scene: {idea}{game_part}. "
        f"Mood and colors: {mood_text}. "
        f"Composition: {comp} "
        f"Style: ultra-detailed digital art, dramatic volumetric lighting, glowing highlights, "
        f"rich saturated colors, strong contrast, sharp focus, slight depth of field. "
        f"IMPORTANT: no text, no letters, no numbers, no logos, no watermark, no user interface, "
        f"and no people or characters in the empty area."
    )


def _read(file_like):
    if file_like is None:
        return None
    getvalue = getattr(file_like, "getvalue", None)
    if callable(getvalue):
        return getvalue()
    data = file_like.read()
    try:
        file_like.seek(0)
    except Exception:
        pass
    return data


def quality_notes(bg_file=None, fg_file=None):
    """Return a list of short warnings about the uploaded images (empty list = all good)."""
    notes = []
    try:
        data = _read(bg_file)
        if data:
            w, h = Image.open(io.BytesIO(data)).size
            if w < 1280 or h < 720:
                notes.append(f"Background chhota hai ({w}x{h}). Kam se kam 1280x720, behtar 1920x1080 — "
                             "warna thumbnail blurry dikhega.")
    except Exception:
        pass
    try:
        data = _read(fg_file)
        if data:
            img = Image.open(io.BytesIO(data)).convert("RGBA")
            alpha = img.getchannel("A")
            if alpha.getextrema()[0] >= 250:
                notes.append("Character transparent PNG nahi hai, isliye photo card jaisa dikhega. "
                             "remove.bg ya Canva 'Background Remover' se cutout banao — tab asli pro look aata hai.")
            else:
                bbox = alpha.point(lambda v: 255 if v > 16 else 0).getbbox()
                ch = (bbox[3] - bbox[1]) if bbox else img.height
                if ch < 600:
                    notes.append(f"Character chhota hai (sirf {ch}px ooncha). 800px+ ooncha photo use karo, "
                                 "warna bada karne par blurry dikhega.")
    except Exception:
        pass
    return notes
