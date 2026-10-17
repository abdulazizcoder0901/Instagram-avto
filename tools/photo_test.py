"""Rasm manbalarini GitHub serverida alohida sinash (vaqtinchalik)."""
import re
import sys

import requests

from bot import photos

for q in sys.argv[1:]:
    print("=" * 20, q)
    r = requests.get("https://www.bing.com/images/search", headers=photos.BROWSER, timeout=30,
                     params={"q": q, "qft": "+filterui:imagesize-large", "form": "IRFLTR", "first": 1})
    title = re.search(r"<title>(.*?)</title>", r.text, re.S)
    print("BING status", r.status_code, "len", len(r.text), "title", title.group(1)[:80] if title else None,
          "iusc", r.text.count('class="iusc"'))
    try:
        print("BING", list(photos._bing(q))[:4])
    except Exception as e:
        print("BING ERR", e)
    try:
        print("DDG", list(photos._duckduckgo(q))[:4])
    except Exception as e:
        print("DDG ERR", repr(e))
