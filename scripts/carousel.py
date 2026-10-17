"""JSON ssenariydan premium-minimal carousel slaydlar (1080x1350 JPEG) yaratadi.

Ishlatish:
    python3 scripts/carousel.py posts/2026-10-18/post.json

JSON tuzilmasi:
    {
      "slides": [
        {"type": "cover", "kicker": "...", "title": "...", "subtitle": "..."},
        {"type": "content", "title": "...", "body": "..."},
        {"type": "image", "title": "...", "body": "...", "image": "rasm.jpg"},
        {"type": "cta", "title": "...", "body": "..."}
      ]
    }

Slaydlar JSON fayl turgan papkaga 01.jpg, 02.jpg, ... nomlari bilan saqlanadi.
"image" slayddagi rasm ham shu papkadan qidiriladi.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H = 1080, 1350
MARGIN = 96
HANDLE = "@mr_abdulazz"

BG = (246, 244, 239)
INK = (20, 20, 22)
MUTED = (110, 108, 104)
ACCENT = (194, 120, 62)
RULE = (222, 218, 210)

FONT_DIR = Path("/usr/share/fonts/opentype/inter")
FALLBACK = {
    "bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "regular": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
}
FONT_FILES = {
    "display": "InterDisplay-Bold.otf",
    "bold": "Inter-SemiBold.otf",
    "regular": "Inter-Regular.otf",
    "medium": "Inter-Medium.otf",
}


def font(weight, size):
    path = FONT_DIR / FONT_FILES[weight]
    if path.exists():
        return ImageFont.truetype(str(path), size)
    fallback = FALLBACK["regular" if weight == "regular" else "bold"]
    return ImageFont.truetype(fallback, size)


def wrap(draw, text, fnt, max_width):
    """Matnni piksel kengligi bo'yicha qatorlarga bo'ladi; \\n ni hurmat qiladi."""
    lines = []
    for paragraph in text.split("\n"):
        words, line = paragraph.split(), ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if draw.textlength(candidate, font=fnt) <= max_width:
                line = candidate
            else:
                if line:
                    lines.append(line)
                line = word
        lines.append(line)
    return lines


def text_block(draw, text, fnt, y, fill, line_gap=1.25, max_width=W - 2 * MARGIN):
    for line in wrap(draw, text, fnt, max_width):
        draw.text((MARGIN, y), line, font=fnt, fill=fill)
        y += int(fnt.size * line_gap)
    return y


def fit_font(draw, text, weight, start, minimum, max_lines, max_width=W - 2 * MARGIN):
    """Sarlavha max_lines qatorga sig'guncha shrift o'lchamini kichraytiradi."""
    size = start
    while size > minimum:
        if len(wrap(draw, text, font(weight, size), max_width)) <= max_lines:
            break
        size -= 4
    return font(weight, size)


def chrome(draw, index, total, show_swipe):
    draw.text((MARGIN, 72), HANDLE, font=font("medium", 30), fill=MUTED)
    counter = f"{index}/{total}"
    cf = font("medium", 30)
    draw.text((W - MARGIN - draw.textlength(counter, font=cf), 72), counter, font=cf, fill=MUTED)
    draw.line([(MARGIN, H - 130), (W - MARGIN, H - 130)], fill=RULE, width=2)
    if show_swipe:
        hint = "Suring  →"
        hf = font("medium", 32)
        draw.text((W - MARGIN - draw.textlength(hint, font=hf), H - 100), hint, font=hf, fill=INK)
    # pastki chap: progress chiziqlari
    seg, gap = 28, 10
    for i in range(total):
        x = MARGIN + i * (seg + gap)
        color = INK if i < index else RULE
        draw.rounded_rectangle([x, H - 84, x + seg, H - 78], radius=3, fill=color)


def draw_cover(draw, s):
    y = 300
    if s.get("kicker"):
        draw.text((MARGIN, y), s["kicker"].upper(), font=font("bold", 34), fill=ACCENT)
        y += 90
    tf = fit_font(draw, s["title"], "display", 112, 68, 5)
    y = text_block(draw, s["title"], tf, y, INK, line_gap=1.08)
    if s.get("subtitle"):
        text_block(draw, s["subtitle"], font("regular", 44), y + 56, MUTED, line_gap=1.35)


def draw_content(draw, s, number):
    y = 250
    draw.text((MARGIN, y), f"{number:02d}", font=font("display", 120), fill=ACCENT)
    y += 190
    tf = fit_font(draw, s["title"], "display", 76, 52, 3)
    y = text_block(draw, s["title"], tf, y, INK, line_gap=1.12)
    if s.get("body"):
        bf = fit_font(draw, s["body"], "regular", 46, 36, 9)
        text_block(draw, s["body"], bf, y + 44, MUTED, line_gap=1.42)


def draw_cta(draw, s):
    y = 380
    draw.rounded_rectangle([MARGIN, y, MARGIN + 120, y + 10], radius=5, fill=ACCENT)
    y += 80
    tf = fit_font(draw, s["title"], "display", 92, 60, 4)
    y = text_block(draw, s["title"], tf, y, INK, line_gap=1.1)
    if s.get("body"):
        text_block(draw, s["body"], font("regular", 44), y + 48, MUTED, line_gap=1.4)


def draw_image(img, draw, s, photo_path):
    """Haqiqiy rasm/misol slaydi: sarlavha, yumaloq burchakli rasm, qisqa izoh."""
    y = 220
    tf = fit_font(draw, s["title"], "display", 64, 44, 2)
    y = text_block(draw, s["title"], tf, y, INK, line_gap=1.12) + 36
    body = s.get("body", "")
    bf = font("regular", 38)
    body_lines = wrap(draw, body, bf, W - 2 * MARGIN)[:3] if body else []
    bottom = H - 170 - (len(body_lines) * int(bf.size * 1.38) + 30 if body_lines else 0)
    box = (W - 2 * MARGIN, bottom - y)
    photo = ImageOps.fit(ImageOps.exif_transpose(Image.open(photo_path)).convert("RGB"), box,
                         Image.LANCZOS)
    mask = Image.new("L", box, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, box[0] - 1, box[1] - 1], radius=28, fill=255)
    img.paste(photo, (MARGIN, y), mask)
    y = bottom + 30
    for line in body_lines:
        draw.text((MARGIN, y), line, font=bf, fill=MUTED)
        y += int(bf.size * 1.38)


def render_slides(slides, out_dir, assets_dir=None):
    """Slaydlarni out_dir ga 01.jpg, 02.jpg, ... qilib saqlaydi va yo'llarini qaytaradi.

    "image" slayd rasmlari assets_dir (berilmasa out_dir) dan olinadi; rasm topilmasa,
    slayd oddiy matnli slayd sifatida chiziladi.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(slides)
    outputs = []
    assets_dir = Path(assets_dir or out_dir)
    content_no = 0
    for i, s in enumerate(slides, start=1):
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)
        if s["type"] == "cover":
            draw_cover(draw, s)
        elif s["type"] == "image" and s.get("image") and (assets_dir / s["image"]).is_file():
            draw_image(img, draw, s, assets_dir / s["image"])
        elif s["type"] in ("content", "image"):
            content_no += 1
            draw_content(draw, s, content_no)
        elif s["type"] == "cta":
            draw_cta(draw, s)
        else:
            raise ValueError(f"Noma'lum slayd turi: {s['type']}")
        chrome(draw, i, total, show_swipe=i < total)
        out = out_dir / f"{i:02d}.jpg"
        img.save(out, "JPEG", quality=95, optimize=True)
        outputs.append(out)
    return outputs


def render(spec_path):
    spec_path = Path(spec_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    for out in render_slides(spec["slides"], spec_path.parent):
        print(out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    render(sys.argv[1])
