"""Notion kontent-plan bilan ishlash: bugungi mavzuni olish va "Post" deb belgilash."""
import os

import requests

API = "https://api.notion.com/v1"
VERSION = "2025-09-03"
DATA_SOURCE_ID = os.environ.get("NOTION_DATA_SOURCE_ID", "13954e42-ad65-811e-be30-000bafe10b9d")

TITLE = "Kontent mavzu"
STATUS = "Content Status"
DATE = "Publish Date"
RUBRIC = "Rubrikalar"
DONE = "Post"


def _headers():
    return {
        "Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
        "Notion-Version": VERSION,
        "Content-Type": "application/json",
    }


def _post(path, body):
    r = requests.post(f"{API}{path}", headers=_headers(), json=body, timeout=30)
    r.raise_for_status()
    return r.json()


def _plain(rich):
    return "".join(part.get("plain_text", "") for part in rich or [])


def _topic(page):
    props = page["properties"]
    date = (props.get(DATE) or {}).get("date") or {}
    return {
        "id": page["id"],
        "url": page["url"],
        "title": _plain(props[TITLE]["title"]).strip(),
        "date": date.get("start"),
        "rubrics": [o["name"] for o in (props.get(RUBRIC) or {}).get("multi_select", [])],
    }


def next_topic(today):
    """Sanasi bugun yoki undan oldin bo'lgan, hali chiqmagan eng birinchi mavzu.

    Shunday qilib bir kunga ikki mavzu tushsa yoki bir kun o'tkazib yuborilsa ham
    hech qaysi mavzu yo'qolmaydi — navbatdagi kunlarda chiqadi.
    """
    body = {
        "filter": {"and": [
            {"property": STATUS, "status": {"does_not_equal": DONE}},
            {"property": DATE, "date": {"on_or_before": today}},
        ]},
        "sorts": [
            {"property": DATE, "direction": "ascending"},
            {"timestamp": "created_time", "direction": "ascending"},
        ],
        "page_size": 1,
    }
    results = _post(f"/data_sources/{DATA_SOURCE_ID}/query", body)["results"]
    return _topic(results[0]) if results else None


def recent_titles(limit=12):
    body = {
        "filter": {"property": STATUS, "status": {"equals": DONE}},
        "sorts": [{"property": DATE, "direction": "descending"}],
        "page_size": limit,
    }
    return [_topic(p)["title"] for p in _post(f"/data_sources/{DATA_SOURCE_ID}/query", body)["results"]]


def page_text(page_id):
    """Sahifa ichidagi ssenariy matnini oddiy matn ko'rinishida qaytaradi."""
    lines, cursor = [], None
    while True:
        params = {"page_size": 100}
        if cursor:
            params["start_cursor"] = cursor
        r = requests.get(f"{API}/blocks/{page_id}/children", headers=_headers(), params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        for block in data["results"]:
            content = block.get(block["type"], {})
            text = _plain(content.get("rich_text"))
            if text:
                lines.append(text)
        if not data.get("has_more"):
            return "\n".join(lines)
        cursor = data["next_cursor"]


def mark_posted(page_id, today):
    r = requests.patch(f"{API}/pages/{page_id}", headers=_headers(), timeout=30, json={
        "properties": {
            STATUS: {"status": {"name": DONE}},
            DATE: {"date": {"start": today}},
        },
    })
    r.raise_for_status()
