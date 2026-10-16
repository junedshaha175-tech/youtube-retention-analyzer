"""Auto Thumbnail Maker for the YouTube Retention Analyzer.

Builds 1280x720 gaming-style YouTube thumbnails with Pillow only (no API key).

Pipeline:  background (blur + color grade + dark text side)
        -> character (cutout, rim outline, glow, spotlight, soft edge blend)
        -> headline (balanced lines, hero word, 3D depth, gradient fill, slight tilt)
        -> finishing (grain + sharpen)

Public API:
    STYLES, make_thumbnail(...), to_png_bytes, to_jpeg_bytes, font_ok, load_image
"""
import io
import math
import os
import random
import re
from itertools import combinations
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

W, H = 1280, 720
MAX_TITLE_CHARS = 70
MAX_JPEG_BYTES = 2_000_000  # YouTube thumbnail size limit is 2 MB

FONT_DIR = Path(__file__).parent / "fonts"
FONT_FILES = {
    "anton": FONT_DIR / "Anton-Regular.ttf",
    "bangers": FONT_DIR / "Bangers-Regular.ttf",
    "poppins": FONT_DIR / "Poppins-Bold.ttf",
}
LATIN_FONT = FONT_FILES["poppins"]

# Anton/Bangers/Poppins have no Devanagari glyphs, so Hindi titles use a system font.
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
        font="anton", bg=("#010a03", "#00401a"), text="#ffffff", accent="#00ff41",
        glow="#00ff41", tint="#00ff41", pattern="rain",
    ),
    "Fire Red": dict(
        font="anton", bg=("#1a0000", "#8f0a0a"), text="#ffffff", accent="#ffd400",
        glow="#ff3b1f", tint="#ff2a00", pattern="rays",
    ),
    "Neon Pop": dict(
        font="bangers", bg=("#0b0618", "#2a0f55"), text="#ffe600", accent="#ffffff",
        glow="#c020ff", tint="#8a2be2", pattern="grid",
    ),
    "Pixel Gold": dict(
        font="anton", bg=("#0f2a14", "#3b2a14"), text="#ffffff", accent="#ffb300",
        glow="#ffb300", tint="#ff9500", pattern="blocks",
    ),
}


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def _hex(c, alpha=255):
    c = c.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), alpha)


def _lighten(c, amt):
    r, g, b, _ = _hex(c)
    return (int(r + (255 - r) * amt), int(g + (255 - g) * amt), int(b + (255 - b) * amt))


def _has_devanagari(text):
    return any("\u0900" <= ch <= "\u097f" for ch in text)


def pick_font_path(text, preferred="anton"):
    """Return (font_path, ok). ok=False means glyphs for `text` may be missing."""
    if _has_devanagari(text):
        for p in DEVANAGARI_FONTS:
            if os.path.exists(p):
                return p, True
        return str(FONT_FILES["poppins"]), False
    path = FONT_FILES.get(preferred, LATIN_FONT)
    if not path.exists():
        path = LATIN_FONT
    return str(path), True


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


def _put(canvas, im, pos):
    """alpha_composite that tolerates negative / out-of-canvas positions."""
    x, y = pos
    cx0, cy0 = max(0, -x), max(0, -y)
    cx1, cy1 = min(im.width, canvas.width - x), min(im.height, canvas.height - y)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    canvas.alpha_composite(im.crop((cx0, cy0, cx1, cy1)), (x + cx0, y + cy0))


def _vgrad(top, bottom, size):
    g = Image.linear_gradient("L").resize(size)
    return ImageOps.colorize(g, black=top, white=bottom).convert("RGBA")


# --------------------------------------------------------------------------
# background
# --------------------------------------------------------------------------
def _gradient(c1, c2):
    return _vgrad(_hex(c1)[:3], _hex(c2)[:3], (W, H))


def _vignette(img, strength=170):
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).ellipse((-W * 0.15, -H * 0.25, W * 1.15, H * 1.25), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(120))
    alpha = ImageOps.invert(mask).point(lambda v: int(v * strength / 255))
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    dark.putalpha(alpha)
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
        for i in range(0, n, 2):
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


def _text_side_shade(text_on_left, strength):
    """Dark gradient on the side where the headline sits."""
    span = W * 0.78
    vals = [int(strength * max(0.0, 1 - x / span) ** 1.2) for x in range(W)]
    if not text_on_left:
        vals = vals[::-1]
    row = Image.new("L", (W, 1))
    row.putdata(vals)
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    shade.putalpha(row.resize((W, H)))
    return shade


def _rays_layer(cx, cy, color):
    """Soft sunburst rays radiating from (cx, cy) - sits behind the character."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    n = 20
    for i in range(0, n, 2):
        a0, a1 = i * 360 / n, (i + 1) * 360 / n
        pts = [(cx, cy)] + [(cx + 2200 * math.cos(math.radians(a)),
                             cy + 2200 * math.sin(math.radians(a))) for a in (a0, a1)]
        d.polygon(pts, fill=(*_lighten(color, 0.6), 34))
    return layer.filter(ImageFilter.GaussianBlur(5))


def _top_shade(strength=170, height=230):
    col = Image.linear_gradient("L").rotate(180).resize((W, height)).point(lambda v: int(v * strength / 255))
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    black = Image.new("RGBA", (W, height), (0, 0, 0, 255))
    black.putalpha(col)
    shade.paste(black, (0, 0))
    return shade


def _background(style, bg_image, has_fg, text_on_left, blur_bg, rng):
    if bg_image is None:
        img = _gradient(*style["bg"])
        img = _pattern(img, style["pattern"], style["glow"], rng)
        if has_fg:
            img = Image.alpha_composite(img, _text_side_shade(text_on_left, 90))
        return _vignette(img, 150)

    img = ImageOps.fit(bg_image.convert("RGB"), (W, H), Image.LANCZOS)
    if blur_bg:  # depth of field: subject + text pop
        img = img.filter(ImageFilter.GaussianBlur(2.6))
    img = ImageEnhance.Contrast(img).enhance(1.12)
    img = ImageEnhance.Color(img).enhance(1.3)
    img = ImageEnhance.Brightness(img).enhance(0.9)
    img = img.convert("RGBA")

    tint = Image.new("RGBA", (W, H), _hex(style["tint"], 38))  # color grade
    img = Image.alpha_composite(img, tint)
    if has_fg:
        img = Image.alpha_composite(img, _text_side_shade(text_on_left, 185))
    else:
        img = Image.alpha_composite(img, Image.new("RGBA", (W, H), (0, 0, 0, 105)))
    return _vignette(img, 135)


# --------------------------------------------------------------------------
# character (subject)
# --------------------------------------------------------------------------
def _smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _feather_mask(a_np, inner):
    """Soft fade on the inner edge if the cutout was cropped there (hard straight edge)."""
    h, w = a_np.shape
    strip = a_np[:, :4] if inner == "left" else a_np[:, -4:]
    if (strip > 200).mean() < 0.25:
        return np.ones((h, w), dtype=np.float32)
    fw = max(30, min(170, int(w * 0.30)))
    ramp = _smoothstep(np.arange(w, dtype=np.float32) / fw)
    if inner == "right":
        ramp = ramp[::-1]
    return np.tile(ramp, (h, 1)).astype(np.float32)


def _place_cutout(base, fg, style, side, h_ratio=1.05, w_ratio=0.47, rays=True):
    """Paste a transparent-background character. Returns (image, text_zone_x0, x1)."""
    a_full = fg.getchannel("A")
    bbox = a_full.point(lambda v: 255 if v > 16 else 0).getbbox()
    if bbox:
        fg = fg.crop(bbox)

    scale = min(H * h_ratio / fg.height, W * w_ratio / fg.width)
    fg = fg.resize((max(1, int(fg.width * scale)), max(1, int(fg.height * scale))), Image.LANCZOS)

    rgb = fg.convert("RGB")
    rgb = ImageEnhance.Brightness(rgb).enhance(1.07)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.12)
    rgb = ImageEnhance.Color(rgb).enhance(1.2)
    rgb = ImageEnhance.Sharpness(rgb).enhance(1.6)

    a_np = np.asarray(fg.getchannel("A"), dtype=np.float32) / 255.0
    inner = "left" if side == "right" else "right"
    fmask = _feather_mask(a_np, inner)
    a_faded = Image.fromarray((a_np * fmask * 255).astype(np.uint8), "L")

    pad = 70
    w, h = fg.size
    a_pad = Image.new("L", (w + 2 * pad, h + 2 * pad), 0)
    a_pad.paste(a_faded, (pad, pad))
    f_pad = Image.new("L", a_pad.size, 255)
    f_pad.paste(Image.fromarray((fmask * 255).astype(np.uint8), "L"), (pad, pad))

    binary = a_pad.point(lambda v: 255 if v > 40 else 0)
    dil = binary.filter(ImageFilter.GaussianBlur(7)).point(lambda v: 255 if v > 25 else 0)
    dil = dil.filter(ImageFilter.GaussianBlur(1.2))
    dil = ImageChops.multiply(dil, f_pad)

    glow_mask = dil.filter(ImageFilter.GaussianBlur(26)).point(lambda v: min(255, int(v * 1.6)))
    shadow_mask = dil.filter(ImageFilter.GaussianBlur(16)).point(lambda v: int(v * 0.75))

    pos_x = (W - w + 4) if side == "right" else -4
    pos_y = H - h + 8
    ox, oy = pos_x - pad, pos_y - pad
    sz = a_pad.size

    # spotlight behind the character
    spot = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cx = pos_x + w // 2
    ImageDraw.Draw(spot).ellipse((cx - w * 0.95, H * 0.02, cx + w * 0.95, H * 1.02),
                                 fill=_hex(style["glow"], 135))
    base = Image.alpha_composite(base, spot.filter(ImageFilter.GaussianBlur(85)))
    if rays:
        base = Image.alpha_composite(base, _rays_layer(cx, H * 0.38, style["glow"]))

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow = Image.new("RGBA", sz, (0, 0, 0, 255))
    shadow.putalpha(shadow_mask)
    _put(layer, shadow, (ox - (14 if side == "right" else -14), oy + 10))
    halo = Image.new("RGBA", sz, _hex(style["glow"]))
    halo.putalpha(glow_mask)
    _put(layer, halo, (ox, oy))
    rim = Image.new("RGBA", sz, (255, 255, 255, 255))
    rim.putalpha(dil)
    _put(layer, rim, (ox, oy))
    subject = rgb.convert("RGBA")
    subject.putalpha(a_faded)
    _put(layer, subject, (pos_x, pos_y))
    base = Image.alpha_composite(base, layer)

    if side == "right":
        return base, 56, pos_x + int(w * 0.08)
    return base, pos_x + int(w * 0.92), W - 56


def _place_photo(base, fg, style, side):
    """Fallback for a normal (opaque) photo: tilted rounded card with glow."""
    box_w, box_h = int(W * 0.36), int(H * 0.80)
    card = ImageOps.fit(fg.convert("RGB"), (box_w, box_h), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", card.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *card.size), radius=26, fill=255)
    card.putalpha(mask)
    framed = Image.new("RGBA", (box_w + 28, box_h + 28), (0, 0, 0, 0))
    ImageDraw.Draw(framed).rounded_rectangle((0, 0, *framed.size), radius=32, fill=(255, 255, 255, 255))
    framed.alpha_composite(card, (14, 14))
    angle = 4 if side == "right" else -4
    framed = framed.rotate(angle, expand=True, resample=Image.BICUBIC)

    x = (W - framed.width - 36) if side == "right" else 36
    y = (H - framed.height) // 2
    gp = 60  # padded so the blurred glow isn't clipped to a rectangle
    amask = Image.new("L", (framed.width + 2 * gp, framed.height + 2 * gp), 0)
    amask.paste(framed.getchannel("A"), (gp, gp))
    glow = Image.new("RGBA", amask.size, _hex(style["glow"]))
    glow.putalpha(amask.filter(ImageFilter.GaussianBlur(28)).point(lambda v: min(255, int(v * 1.5))))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    _put(layer, glow, (x - gp, y - gp))
    _put(layer, framed, (x, y))
    base = Image.alpha_composite(base, layer)
    if side == "right":
        return base, 56, x - 14
    return base, x + framed.width + 14, W - 56


def _place_foreground(base, fg, style, side, h_ratio=1.05, w_ratio=0.47, rays=True):
    fg = ImageOps.exif_transpose(fg).convert("RGBA")
    if fg.getchannel("A").getextrema()[0] < 250:
        return _place_cutout(base, fg, style, side, h_ratio, w_ratio, rays)
    return _place_photo(base, fg, style, side)


# --------------------------------------------------------------------------
# headline
# --------------------------------------------------------------------------
def _metrics(font, devanagari):
    asc, desc = font.getmetrics()
    if devanagari:
        return int(asc * 0.85), int((asc + desc) * 0.98)
    cap = -font.getbbox("H", anchor="ls")[1]
    return cap, int(cap * 1.2)


def _layout(draw, words, path, max_w, max_h, devanagari, max_lines=3, max_size=260):
    """Largest font size + balanced line breaks that fit the zone."""
    n = len(words)
    for size in range(max_size, 35, -4):
        font = _font(path, size)
        stroke = max(6, int(size * 0.07))
        widths = [draw.textlength(w, font=font) for w in words]
        space = draw.textlength(" ", font=font)
        cap, lh = _metrics(font, devanagari)
        best = None
        for k in range(1, min(max_lines, n) + 1):
            if cap + (k - 1) * lh + 2 * stroke > max_h:
                break
            for cuts in combinations(range(1, n), k - 1):
                bounds = [0, *cuts, n]
                spans = list(zip(bounds, bounds[1:]))
                lw = [sum(widths[a:b]) + space * (b - a - 1) for a, b in spans]
                if max(lw) + 2 * stroke > max_w:
                    continue
                cost = max(lw) + 0.6 * (max(lw) - min(lw)) + 40 * k
                for (a, b) in spans:  # avoid a tiny orphan word alone on a line
                    if b - a == 1 and len(words[a]) <= 2 and n > 2:
                        cost += 400
                if best is None or cost < best[0]:
                    best = (cost, spans, lw)
        if best:
            _, spans, lw = best
            return font, size, stroke, [words[a:b] for a, b in spans], lw, space, cap, lh
    font = _font(path, 36)
    cap, lh = _metrics(font, devanagari)
    space = draw.textlength(" ", font=font)
    lines, cur = [], []
    for w in words:
        trial = cur + [w]
        if cur and sum(draw.textlength(x, font=font) for x in trial) + space * (len(trial) - 1) > max_w:
            lines.append(cur)
            cur = [w]
        else:
            cur = trial
    if cur:
        lines.append(cur)
    lw = [sum(draw.textlength(x, font=font) for x in ln) + space * (len(ln) - 1) for ln in lines]
    return font, 36, 6, lines, lw, space, cap, lh


def _auto_highlight(words):
    for w in words:
        if any(ch.isdigit() for ch in w):
            return {_norm(w)}
    return {_norm(words[-1])} if words else set()


def _draw_title(base, title, style, highlight, zone, align_left, top_reserved,
                zone_y=None, max_lines=3, max_size=260):
    devanagari = _has_devanagari(title)
    path, _ = pick_font_path(title, style["font"])
    words = title.upper().split()
    if not words:
        return base, 0

    x0, x1 = zone
    y0, y1 = zone_y if zone_y else (top_reserved, H - 50)
    probe = ImageDraw.Draw(base)
    font, size, stroke, lines, lws, space, cap, lh = _layout(
        probe, words, path, x1 - x0, y1 - y0, devanagari, max_lines, max_size)

    block_h = cap + (len(lines) - 1) * lh
    top = y0 + (y1 - y0 - block_h) / 2
    hl = {_norm(w) for w in highlight.split()} if highlight.strip() else _auto_highlight(words)
    hl.discard("")

    placed = []  # (x, baseline, word, is_highlight)
    for i, (line, lw) in enumerate(zip(lines, lws)):
        x = x0 + stroke if align_left else x0 + (x1 - x0 - lw) / 2
        by = top + cap + i * lh
        for w in line:
            placed.append((x, by, w, _norm(w) in hl))
            x += probe.textlength(w, font=font) + space

    glow_c, text_c, acc_c = _hex(style["glow"], 210), style["text"], style["accent"]
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for x, by, w, _ in placed:
        gd.text((x, by), w, font=font, fill=glow_c, anchor="ls",
                stroke_width=stroke + 8, stroke_fill=glow_c)
    layer = Image.alpha_composite(layer, glow.filter(ImageFilter.GaussianBlur(24)))

    d = ImageDraw.Draw(layer)
    depth = max(8, int(size * 0.09))
    for off in range(depth, 0, -2):  # 3D extrusion
        for x, by, w, _ in placed:
            d.text((x + off * 0.6, by + off), w, font=font, fill=(0, 0, 0, 255), anchor="ls",
                   stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
    for x, by, w, _ in placed:
        d.text((x, by), w, font=font, fill=(0, 0, 0, 255), anchor="ls",
               stroke_width=stroke, stroke_fill=(0, 0, 0, 255))

    masks = {False: Image.new("L", (W, H), 0), True: Image.new("L", (W, H), 0)}
    mds = {k: ImageDraw.Draw(v) for k, v in masks.items()}
    for x, by, w, is_hl in placed:
        mds[is_hl].text((x, by), w, font=font, fill=255, anchor="ls")
    gy0 = max(0, int(top - 12))
    gy1 = min(H, int(top + block_h + stroke + 12 + size * 0.25))
    for is_hl, color in ((False, text_c), (True, acc_c)):
        grad = _vgrad(_lighten(color, 0.45), _hex(color)[:3], (W, gy1 - gy0))
        layer.paste(grad, (0, gy0), masks[is_hl].crop((0, gy0, W, gy1)))

    cx = (x0 + x1) / 2
    cy = top + block_h / 2
    layer = layer.rotate(2.0 if align_left else 1.2, resample=Image.BICUBIC, center=(cx, cy))
    return Image.alpha_composite(base, layer), int(top)


def _draw_badge(base, text, style):
    path, _ = pick_font_path(text, style["font"])
    font = _font(path, 50)
    probe = ImageDraw.Draw(base)
    text = text.upper()
    tw = probe.textlength(text, font=font)
    cap = -font.getbbox("H", anchor="ls")[1] if not _has_devanagari(text) else 40
    pad_x, pad_y = 26, 14
    bw, bh = int(tw + pad_x * 2), int(cap + pad_y * 2)
    badge = Image.new("RGBA", (bw + 20, bh + 20), (0, 0, 0, 0))
    bd = ImageDraw.Draw(badge)
    bd.rounded_rectangle((10, 10, 10 + bw, 10 + bh), radius=14, fill=_hex(style["accent"]),
                         outline=(0, 0, 0, 255), width=5)
    bd.text((10 + pad_x, 10 + pad_y + cap), text, font=font, fill=(0, 0, 0, 255), anchor="ls")
    badge = badge.rotate(5, resample=Image.BICUBIC, expand=True)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    _put(layer, badge, (40, 34))
    return Image.alpha_composite(base, layer), 34 + badge.height


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------
LAYOUTS = ("Big headline", "Small label", "Versus")


def make_thumbnail(title, style_name="Matrix Green", highlight="", badge="",
                   bg_image=None, fg_image=None, seed=0, border=False,
                   side="right", blur_bg=True, layout="Big headline",
                   fg_image2=None, rays=True):
    """Build one 1280x720 thumbnail and return it as an RGB PIL image.

    layout:
      "Big headline" - huge title on one side, character on the other.
      "Small label"  - short label at the top, character fills the frame (picture does the work).
      "Versus"       - two characters (fg_image + fg_image2) left/right, label across the top.
    """
    style = STYLES[style_name]
    title = " ".join(title.split())[:MAX_TITLE_CHARS]
    rng = random.Random(seed)
    versus = layout == "Versus" and fg_image is not None and fg_image2 is not None
    has_fg = fg_image is not None
    text_on_left = (side == "right") or not has_fg

    base = _background(style, bg_image, has_fg and not versus, text_on_left, blur_bg, rng)

    zone_y, max_lines, max_size = None, 3, 260
    if versus:
        base, _, _ = _place_foreground(base, fg_image, style, "left", 0.88, 0.46, rays)
        base, _, _ = _place_foreground(base, fg_image2, style, "right", 0.88, 0.46, rays)
        base = Image.alpha_composite(base, _top_shade())
        zx0, zx1 = 90, W - 90
        zone_y, max_lines, max_size = (26, 170), 1, 150
        align_left = False
    else:
        if has_fg:
            base, zx0, zx1 = _place_foreground(base, fg_image, style, side, 1.05, 0.47, rays)
        else:
            zx0, zx1 = 80, W - 80
        align_left = has_fg
        if layout == "Small label":
            base = Image.alpha_composite(base, _top_shade(150, 260))
            zone_y, max_lines, max_size = (34, 290), 2, 170

    top_reserved = 56
    if badge.strip() and not versus:
        base, badge_bottom = _draw_badge(base, badge.strip()[:14], style)
        top_reserved = min(badge_bottom + 6, 150)
        if zone_y:
            zone_y = (max(zone_y[0], top_reserved), max(zone_y[1], top_reserved + 200))

    if title.strip():
        base, _ = _draw_title(base, title, style, highlight, (zx0, zx1), align_left,
                              top_reserved, zone_y, max_lines, max_size)

    if border:
        ImageDraw.Draw(base).rectangle((0, 0, W - 1, H - 1), outline=_hex(style["glow"]), width=12)

    out = base.convert("RGB")
    noise = Image.effect_noise((W, H), 38).convert("RGB")  # subtle film grain
    out = Image.blend(out, noise, 0.035)
    out = ImageEnhance.Contrast(out).enhance(1.05)
    return out.filter(ImageFilter.UnsharpMask(radius=1.4, percent=60, threshold=3))


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
