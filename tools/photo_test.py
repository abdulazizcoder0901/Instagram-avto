"""Rasm qidiruvini GitHub serverida sinash (vaqtinchalik)."""
import sys
from pathlib import Path

from PIL import Image

from bot import photos

out = Path("tests/photo-test")
out.mkdir(parents=True, exist_ok=True)
used = set()
for i, q in enumerate(sys.argv[1:], 1):
    path = photos.search_real(q, out / "raw", used)
    if path:
        img = Image.open(path)
        img.thumbnail((540, 540))
        img.save(out / f"{i:02d}.jpg")
    print(i, q, "->", (sorted(used)[-1] if path else "TOPILMADI"), Image.open(path).size if path else "")
