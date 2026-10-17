"""Musiqa variantlari: Instagram katalogi (Buffer orqali) yoki faqat tinglash uchun iTunes namunalari."""
from pathlib import Path

import requests

from bot import buffer


def options(post, limit=5):
    """(rejim, variantlar). "catalog" — Instagram'ning o'z treklari, postga avtomatik qo'shiladi;
    "preview" — Buffer'da Instagram Facebook orqali ulanmagan: faqat tinglash mumkin."""
    # Biznes akkauntlarda faqat litsenziyali kutubxona musiqasi bor: avval kayfiyat/janr bo'yicha,
    # keyin Claude tavsiya qilgan nomlar bo'yicha qidiramiz
    queries = [post["music_query"]] + [s["title"] for s in post["music_suggestions"]]
    catalog = buffer.music_catalog([q for q in queries if q], limit)
    if catalog:
        return "catalog", catalog
    return "preview", [{"id": None, "title": s["title"], "artist": s["artist"],
                        "preview_url": _itunes_preview(s["title"], s["artist"])}
                       for s in post["music_suggestions"][:limit]]


def _itunes_preview(title, artist):
    try:
        r = requests.get("https://itunes.apple.com/search", timeout=20,
                         params={"term": f"{title} {artist}", "entity": "song", "limit": 1})
        results = r.json().get("results", [])
        return results[0].get("previewUrl") if results else None
    except (requests.RequestException, ValueError):
        return None


def download(url, dest):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    Path(dest).write_bytes(r.content)
    return Path(dest)
