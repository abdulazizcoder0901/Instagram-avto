"""Instagram uchun 1080x1350 (4:5) matnli post rasmi yaratadi.

Ishlatish:
    python3 scripts/make_post_image.py media/2026-10-17/post.png "Sarlavha" "Qisqa matn"
"""
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
BG = (17, 24, 39)
ACCENT = (99, 102, 241)
FG = (243, 244, 246)
MUTED = (156, 163, 175)

FONT_CANDIDATES = {
    "bold": ["/usr/share/fonts/opentype/inter/Inter-Bold.otf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "regular": ["/usr/share/fonts/opentype/inter/Inter-Regular.otf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}


def load_font(weight, size):
    for path in FONT_CANDIDATES[weight]:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def draw_lines(draw, lines, font, y, fill, spacing):
    for line in lines:
        draw.text((100, y), line, font=font, fill=fill)
        y += font.size + spacing
    return y


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    out, title = Path(sys.argv[1]), sys.argv[2]
    body = sys.argv[3] if len(sys.argv) > 3 else ""

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle([100, 220, 220, 236], fill=ACCENT)

    y = draw_lines(draw, textwrap.wrap(title, 18), load_font("bold", 88), 300, FG, 20)
    draw_lines(draw, textwrap.wrap(body, 34), load_font("regular", 46), y + 60, MUTED, 18)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    print(out)


if __name__ == "__main__":
    main()
