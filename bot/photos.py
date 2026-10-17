"""Slayd fonlari uchun fotolar.

search_real — haqiqiy rasmlar (film kadrlari, aniq joy/odam/mahsulot): Bing Images, keyin DuckDuckGo.
find — zaxira: litsenziyasi ochiq bepul fotolar (Openverse, Wikimedia Commons).
"""
import hashlib
import html
import io
import json
import re
from pathlib import Path
from urllib.parse import urlparse

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


def _bing(query):
    r = requests.get("https://www.bing.com/images/search", timeout=30, headers=BROWSER, params={
        "q": query, "qft": "+filterui:imagesize-large", "form": "IRFLTR", "first": 1})
    r.raise_for_status()
    for m in re.finditer(r'\bm="(\{[^"]+\})"', r.text):
        try:
            url = json.loads(html.unescape(m.group(1))).get("murl")
        except ValueError:
            continue
        if url:
            yield url


def _duckduckgo(query):
    page = requests.get("https://duckduckgo.com/", timeout=30, headers=BROWSER,
                        params={"q": query, "iax": "images", "ia": "images"})
    token = re.search(r"vqd=['\"]?([\d-]+)", page.text)
    if not token:
        return
    r = requests.get("https://duckduckgo.com/i.js", timeout=30,
                     headers={**BROWSER, "Referer": "https://duckduckgo.com/"},
                     params={"l": "us-en", "o": "json", "q": query, "vqd": token.group(1),
                             "f": ",size:Large,,,", "p": "1"})
    r.raise_for_status()
    for item in r.json().get("results", []):
        if item.get("image"):
            yield item["image"]


def search_real(query, folder, used=None, tries=8):
    """Haqiqiy rasmni qidirib yuklaydi; used — shu postda ishlatilgan linklar (takrorlanmasin)."""
    used = used if used is not None else set()
    for source in (_bing, _duckduckgo):
        try:
            for n, url in enumerate(source(query)):
                if n >= tries:
                    break
                if url in used:
                    continue
                path = download(url, folder)
                if path:
                    used.add(url)
                    return path
        except (requests.RequestException, ValueError):
            continue
    return None
