"""Maqolalardan rasm olishni GitHub serverida sinash (vaqtinchalik)."""
from pathlib import Path

from PIL import Image

from bot import photos

PAGES = [
    "https://www.cbsnews.com/news/tom-cruise-takes-on-alien-invasion-in-edge-of-tomorrow/",
    "https://www.etonline.com/movies/146851_tom_cruise_emily_blunt_detail_edge_of_tomorrow_production",
    "https://www.cheatsheet.com/entertainment/tom-cruise-worked-out-6-months-1-movie-costume.html",
    "https://3dvf.com/en/edge-of-tomorrow-s-toughest-scene-tested-tom-cruise-and-emily-blunt/",
    "https://www.falstaff.com/en/news/this-las-vegas-hotel-room-costs-100000-per-night",
    "https://www.foxnews.com/travel/palms-casino-debuts-worlds-most-expensive-hotel-room-featuring-formaldehyde-suspended-sharks-24-hour-butler-service",
    "https://blooloop.com/museum/news/damien-hirst-art-hotel-empathy-suite-las-vegas/",
    "https://sg.asiatatler.com/life/most-expensive-hotel-rooms-suites-in-the-world",
]
out = Path("tests/photo-test")
out.mkdir(parents=True, exist_ok=True)
used = set()
for i, page in enumerate(PAGES, 1):
    try:
        print(i, page, "->", photos._page_images(page)[:2])
    except Exception as e:
        print(i, page, "-> ERR", repr(e)[:120])
    path = photos.from_pages([page], out / "raw", used)
    if path:
        img = Image.open(path)
        print("   OK", img.size)
        img.thumbnail((540, 540))
        img.save(out / f"{i:02d}.jpg")
    else:
        print("   TOPILMADI")
