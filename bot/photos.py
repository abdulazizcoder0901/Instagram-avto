"""Slaydlar uchun bepul, litsenziyasi ochiq fotolar: Openverse, keyin Wikimedia Commons."""
import hashlib
import re
from pathlib import Path

import requests

UA = {"User-Agent": "Instagram-avto/1.0 (https://github.com/abdulazizcoder0901/Instagram-avto)"}
FREE = {"cc0", "pdm", "public domain", "public domain mark"}


def _openverse(query):
    r = requests.get("https://api.openverse.org/v1/images/", headers=UA, timeout=30, params={
        "q": query, "page_size": 10, "license_type": "commercial", "mature": "false"})
    r.raise_for_status()
    for item in r.json().get("results", []):
        if (item.get("width") or 0) >= 700:
            yield {"url": item["url"], "author": item.get("creator") or "",
                   "license": f"{item.get('license', '')} {item.get('license_version', '')}".strip()}


def _commons(query):
    r = requests.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=30, params={
        "action": "query", "format": "json", "generator": "search", "gsrsearch": f"{query} filetype:bitmap",
        "gsrnamespace": 6, "gsrlimit": 10, "prop": "imageinfo",
        "iiprop": "url|size|extmetadata", "iiurlwidth": 1600})
    r.raise_for_status()
    pages = sorted(r.json().get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    for page in pages:
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        if (info.get("width") or 0) >= 700:
            author = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()
            yield {"url": info.get("thumburl") or info["url"], "author": author,
                   "license": meta.get("LicenseShortName", {}).get("value", "")}


def find(query, folder):
    """So'rov bo'yicha rasm topib yuklaydi. (fayl_yo'li, credit) yoki (None, None) qaytaradi."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"photo-{hashlib.md5(query.encode()).hexdigest()[:10]}.jpg"
    meta_path = dest.with_suffix(".txt")
    if dest.exists():
        return dest, meta_path.read_text() if meta_path.exists() else ""
    for source in (_openverse, _commons):
        try:
            for item in source(query):
                img = requests.get(item["url"], headers=UA, timeout=60)
                if img.ok and img.headers.get("content-type", "").startswith("image/"):
                    dest.write_bytes(img.content)
                    lic = item["license"].lower()
                    credit = "" if lic in FREE else f"{item['author'] or 'muallif'} ({item['license']})"
                    meta_path.write_text(credit)
                    return dest, credit
        except requests.RequestException:
            continue
    return None, None
