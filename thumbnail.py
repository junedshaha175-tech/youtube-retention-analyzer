"""Auto Thumbnail Maker for the YouTube Retention Analyzer.

Generates 1280x720 YouTube thumbnails with Pillow only (no API key, no cost).
Public API:
    STYLES                      -> dict of style presets
    make_thumbnail(...)         -> PIL.Image (1280x720, RGB)
    to_png_bytes / to_jpeg_bytes
    font_ok(text)               -> False if the title needs a font we can't find
"""
import io
import math
import os
import random
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

W, H = 1280, 720
MAX_TITLE_CHARS = 70
MAX_JPEG_BYTES = 2_000_000  # YouTube thumbnail size limit is 2 MB

FONT_DIR = Path(__file__).parent / "fonts"
LATIN_FONT = FONT_DIR / "Poppins-Bold.ttf"

# Poppins has no Devanagari glyphs, so Hindi titles need a system font.
DEVANAGARI_FONTS = [
    "C:/Windows/Fonts/nirmalab.ttf",
    "C:/Windows/Fonts/Nirmala.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
    "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
    "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc",
]

STYLES = {
    "Matrix Green": dict(
        bg=("#010a03", "#00401a"), text="#00ff41", accent="#ffffff",
        stroke="#000000", glow="#00ff41", pattern="rain",
    ),
    "Fire Red": dict(
        bg=("#1a0000", "#8f0a0a"), text="#ffffff", accent="#ffd400",
        stroke="#000000", glow="#ff3b1f", pattern="rays",
    ),
    "Neon Yellow": dict(
        bg=("#0b0618", "#2a0f55"), text="#ffe600", accent="#ff2d78",
        stroke="#000000", glow="#ffe600", pattern="grid",
    ),
    "Pixel Blocks": dict(
        bg=("#0f2a14", "#3b2a14"), text="#ffffff", accent="#7cff3a",
        stroke="#000000", glow="#7cff3a", pattern="blocks",
    ),
}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _hex(c, alpha=255):
    c = c.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), alpha)


def _has_devanagari(text):
    return any("\u0900" <= ch <= "\u097f" for ch in text)


def pick_font_path(text):
    """Return (font_path, ok). ok=False means glyphs for `text` may be missing."""
    if _has_devanagari(text):
        for p in DEVANAGARI_FONTS:
            if os.path.exists(p):
                return p, True
        return str(LATIN_FONT), False
    return str(LATIN_FONT), True


def font_ok(text):
    return pick_font_path(text)[1]


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def _norm(word):
    return re.sub(r"[^\w]", "", word, flags=re.UNICODE).casefold()


def load_image(file_like, max_side=2560):
    """Open an uploaded image safely and downscale very large ones."""
    img = Image.open(file_like)
    img = ImageOps.exif_transpose(img)
    img.thumbnail((max_side, max_side))
    return img


# --------------------------------------------------------------------------
# backgrounds
# --------------------------------------------------------------------------
def _gradient(c1, c2):
    g = Image.linear_gradient("L").resize((W, H))
    return ImageOps.colorize(g, black=c1, white=c2).convert("RGBA")


def _vignette(img, strength=170):
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).ellipse((-W * 0.15, -H * 0.25, W * 1.15, H * 1.25), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(120))
    dark = Image.new("RGBA", (W, H), (0, 0, 0, strength))
    inv = ImageOps.invert(mask)
    dark.putalpha(Image.eval(inv, lambda v: int(v * strength / 255)))
    return Image.alpha_composite(img, dark)


def _pattern(img, name, color, rng):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r, g, b, _ = _hex(color)

    if name == "rain":
        f = _font(str(LATIN_FONT), 26)
        for x in range(10, W, 30):
            y = rng.randint(-300, H)
            for i in range(rng.randint(6, 18)):
                a = max(10, 130 - i * 9)
                d.text((x, y + i * 28), rng.choice("01"), font=f, fill=(r, g, b, a))
    elif name == "rays":
        cx, cy = W * 0.78, H * 0.5
        n = 22
        for i in range(n):
            if i % 2:
                continue
            a0 = i * 360 / n + rng.uniform(-3, 3)
            a1 = a0 + 360 / n
            pts = [(cx, cy)]
            for ang in (a0, a1):
                pts.append((cx + 2000 * math.cos(math.radians(ang)),
                            cy + 2000 * math.sin(math.radians(ang))))
            d.polygon(pts, fill=(r, g, b, 38))
    elif name == "grid":
        for x in range(0, W, 64):
            d.line([(x, 0), (x, H)], fill=(r, g, b, 40), width=2)
        for y in range(0, H, 64):
            d.line([(0, y), (W, y)], fill=(r, g, b, 40), width=2)
    elif name == "blocks":
        s = 48
        for x in range(0, W, s):
            for y in range(0, H, s):
                v = rng.randint(0, 90)
                d.rectangle((x, y, x + s - 2, y + s - 2), fill=(v, v + 20, v // 2, 120))
    return Image.alpha_composite(img, layer)


def _background(style, bg_image, has_fg, rng):
    if bg_image is None:
        img = _gradient(*style["bg"])
        img = _pattern(img, style["pattern"], style["glow"], rng)
        return _vignette(img, 150)

    img = ImageOps.fit(bg_image.convert("RGB"), (W, H), Image.LANCZOS).convert("RGBA")
    img = ImageEnhance.Contrast(img).enhance(1.12)
    img = ImageEnhance.Color(img).enhance(1.25)

    # darken the text side so the title stays readable on any screenshot
    span = W * 0.72
    row = Image.new("L", (W, 1))
    row.putdata([int(200 * max(0.0, 1 - x / span)) if has_fg else 110 for x in range(W)])
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    shade.putalpha(row.resize((W, H)))
    img = Image.alpha_composite(img, shade)
    return _vignette(img, 120)


# --------------------------------------------------------------------------
# text
# --------------------------------------------------------------------------
def _measure(draw, words, font):
    space = draw.textlength(" ", font=font)
    return sum(draw.textlength(w, font=font) for w in words) + space * max(0, len(words) - 1)


def _wrap(draw, words, font, max_w):
    lines, cur = [], []
    for w in words:
        trial = cur + [w]
        if cur and _measure(draw, trial, font) > max_w:
            lines.append(cur)
            cur = [w]
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def _fit(draw, words, path, max_w, max_h, max_lines=3):
    for size in range(230, 35, -4):
        font = _font(path, size)
        if any(draw.textlength(w, font=font) > max_w for w in words):
            continue
        lines = _wrap(draw, words, font, max_w)
        asc, desc = font.getmetrics()
        lh = int((asc + desc) * 0.98)
        if len(lines) <= max_lines and lh * len(lines) <= max_h:
            return font, lines, lh
    font = _font(path, 36)
    return font, _wrap(draw, words, font, max_w), int(sum(font.getmetrics()) * 0.98)


def _auto_highlight(words):
    for w in words:
        if any(ch.isdigit() for ch in w):
            return {_norm(w)}
    return {_norm(words[-1])} if words else set()


def _draw_title(base, title, style, highlight, align_left, top_reserved):
    path, _ = pick_font_path(title)
    words = title.upper().split()
    if not words:
        return base

    if align_left:
        x0, x1 = 64, int(W * 0.60)
    else:
        x0, x1 = 80, W - 80
    y0, y1 = top_reserved, H - 60

    probe = ImageDraw.Draw(base)
    font, lines, lh = _fit(probe, words, path, x1 - x0, y1 - y0)
    block_h = lh * len(lines)
    y = y0 + (y1 - y0 - block_h) / 2

    hl = {_norm(w) for w in highlight.split()} if highlight.strip() else _auto_highlight(words)
    hl.discard("")
    space = probe.textlength(" ", font=font)
    stroke = max(6, int(font.size * 0.075))

    placed = []  # (x, y, word, is_highlight)
    for line in lines:
        lw = _measure(probe, line, font)
        x = x0 if align_left else x0 + (x1 - x0 - lw) / 2
        for w in line:
            placed.append((x, y, w, _norm(w) in hl))
            x += probe.textlength(w, font=font) + space
        y += lh

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd, gd = ImageDraw.Draw(shadow), ImageDraw.Draw(glow)
    for x, yy, w, _ in placed:
        sd.text((x + 8, yy + 10), w, font=font, fill=(0, 0, 0, 230),
                stroke_width=stroke, stroke_fill=(0, 0, 0, 230))
        gd.text((x, yy), w, font=font, fill=_hex(style["glow"], 200),
                stroke_width=stroke + 6, stroke_fill=_hex(style["glow"], 200))
    shadow = shadow.filter(ImageFilter.GaussianBlur(7))
    glow = glow.filter(ImageFilter.GaussianBlur(22))

    base = Image.alpha_composite(base, glow)
    base = Image.alpha_composite(base, shadow)
    d = ImageDraw.Draw(base)
    for x, yy, w, is_hl in placed:
        fill = _hex(style["accent"] if is_hl else style["text"])
        d.text((x, yy), w, font=font, fill=fill,
               stroke_width=stroke, stroke_fill=_hex(style["stroke"]))
    return base


def _draw_badge(base, text, style):
    path, _ = pick_font_path(text)
    font = _font(path, 46)
    d = ImageDraw.Draw(base)
    text = text.upper()
    tw = d.textlength(text, font=font)
    pad_x, pad_y = 26, 12
    box = (48, 44, 48 + tw + pad_x * 2, 44 + 46 + pad_y * 2 + 8)
    d.rounded_rectangle(box, radius=14, fill=_hex(style["accent"]),
                        outline=_hex(style["stroke"]), width=5)
    d.text((box[0] + pad_x, box[1] + pad_y - 2), text, font=font, fill=_hex("#000000"))
    return base, int(box[3])


# --------------------------------------------------------------------------
# foreground image (face / character)
# --------------------------------------------------------------------------
def _place_foreground(base, fg, style):
    fg = ImageOps.exif_transpose(fg).convert("RGBA")
    alpha = fg.getchannel("A")
    has_cutout = alpha.getextrema()[0] < 250

    if has_cutout:
        bbox = alpha.getbbox()
        if bbox:
            fg = fg.crop(bbox)
        scale = min(H * 0.96 / fg.height, W * 0.46 / fg.width)
        fg = fg.resize((max(1, int(fg.width * scale)), max(1, int(fg.height * scale))), Image.LANCZOS)
        pos = (W - fg.width - 30, H - fg.height + 6)

        edge = fg.getchannel("A").filter(ImageFilter.MaxFilter(13))
        outline = Image.new("RGBA", fg.size, _hex("#ffffff"))
        outline.putalpha(edge)
        halo = Image.new("RGBA", fg.size, _hex(style["glow"]))
        halo.putalpha(edge.filter(ImageFilter.GaussianBlur(14)))

        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        layer.alpha_composite(halo, (pos[0], max(0, pos[1])))
        layer.alpha_composite(outline, (pos[0], max(0, pos[1])))
        layer.alpha_composite(fg, (pos[0], max(0, pos[1])))
        return Image.alpha_composite(base, layer)

    # normal photo -> framed card with a slight tilt
    box_w, box_h = int(W * 0.38), int(H * 0.78)
    card = ImageOps.fit(fg.convert("RGB"), (box_w, box_h), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", card.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *card.size), radius=28, fill=255)
    card.putalpha(mask)
    framed = Image.new("RGBA", (box_w + 24, box_h + 24), (0, 0, 0, 0))
    ImageDraw.Draw(framed).rounded_rectangle((0, 0, *framed.size), radius=34, fill=_hex(style["glow"]))
    framed.alpha_composite(card, (12, 12))
    framed = framed.rotate(4, expand=True, resample=Image.BICUBIC)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer.alpha_composite(framed, (W - framed.width - 40, (H - framed.height) // 2))
    return Image.alpha_composite(base, layer)


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------
def make_thumbnail(title, style_name="Matrix Green", highlight="", badge="",
                   bg_image=None, fg_image=None, seed=0, border=True):
    """Build one 1280x720 thumbnail and return it as an RGB PIL image."""
    style = STYLES[style_name]
    title = " ".join(title.split())[:MAX_TITLE_CHARS]
    rng = random.Random(seed)

    base = _background(style, bg_image, fg_image is not None, rng)
    if fg_image is not None:
        base = _place_foreground(base, fg_image, style)

    top_reserved = 60
    if badge.strip():
        base, badge_bottom = _draw_badge(base, badge.strip()[:14], style)
        top_reserved = badge_bottom + 20

    base = _draw_title(base, title, style, highlight, fg_image is not None, top_reserved)

    if border:
        ImageDraw.Draw(base).rectangle((0, 0, W - 1, H - 1), outline=_hex(style["glow"]), width=14)

    return base.convert("RGB")


def to_png_bytes(img):
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def to_jpeg_bytes(img, max_bytes=MAX_JPEG_BYTES):
    """JPEG under YouTube's 2 MB limit."""
    for q in (95, 90, 85, 80, 70, 60):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q, optimize=True)
        if buf.tell() <= max_bytes:
            break
    return buf.getvalue()
