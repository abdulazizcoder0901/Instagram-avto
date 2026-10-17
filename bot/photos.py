"""Slayd fonlari uchun fotolar.

from_pages — haqiqiy rasmlar: Claude topgan maqolalarning asosiy rasmi (og:image).
find — zaxira: litsenziyasi ochiq bepul fotolar (Openverse, Wikimedia Commons).
"""
import hashlib
import html
import io
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from PIL import Image

UA = {"User-Agent": "Instagram-avto/1.0 (https://github.com/abdulazizcoder0901/Instagram-avto)"}
BROWSER = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
           "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"}
MIN_SIDE = 500
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


def download(url, folder):
    """Internetdagi rasmni yuklaydi (kamida 500px bo'lsa). Fayl yo'li yoki None."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"web-{hashlib.md5(url.encode()).hexdigest()[:10]}.jpg"
    if dest.exists():
        return dest
    origin = urlparse(url)
    try:
        r = requests.get(url, timeout=40, headers={**BROWSER, "Referer": f"{origin.scheme}://{origin.netloc}/"})
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content))
        if min(img.size) < MIN_SIDE:
            return None
        img.convert("RGB").save(dest, "JPEG", quality=92)
        return dest
    except Exception:
        return None


def _page_images(url):
    """Maqola sahifasidagi asosiy rasm(lar): og:image, twitter:image, image_src."""
    r = requests.get(url, timeout=30, headers={**BROWSER, "Accept": "text/html,*/*"})
    r.raise_for_status()
    found = []
    for tag in re.findall(r"<(?:meta|link)\b[^>]+>", r.text[:400_000], re.I):
        if re.search(r'(?:property|name|rel)=["\'](?:og:image(?::secure_url)?|twitter:image(?::src)?|image_src)["\']',
                     tag, re.I):
            m = re.search(r'(?:content|href)=["\']([^"\']+)', tag, re.I)
            if m:
                found.append(urljoin(url, html.unescape(m.group(1))))
    return list(dict.fromkeys(found))


def from_pages(pages, folder, used=None):
    """Claude topgan maqolalardan asosiy rasmni yuklaydi; used — shu postda ishlatilganlar."""
    used = used if used is not None else set()
    for page in pages:
        try:
            for url in _page_images(page):
                if url in used:
                    continue
                path = download(url, folder)
                digest = path and hashlib.md5(path.read_bytes()).hexdigest()
                if path and digest not in used:
                    used.update({url, digest})
                    return path
        except (requests.RequestException, ValueError):
            continue
    return None
