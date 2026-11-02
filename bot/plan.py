"""Kontent-reja fayli (content_plan.json): Notion o'rniga tayyor mavzular va ularning sanalari.

Fayl bo'lsa, bot mavzularni shu yerdan oladi: sanasi kelgan (yoki o'tib ketgan), hali chiqmagan eng
birinchi mavzu. Rejada post yo'q kunlarda bot faqat fayl va izohlarni qabul qiladi.
"""
import json
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "content_plan.json"


def enabled():
    return PATH.exists()


def _load():
    return json.loads(PATH.read_text())


def _published(root):
    """Allaqachon chiqqan (tasdiqlangan) reja mavzularining id'lari."""
    done = set()
    for state in (Path(root) / "posts").glob("*/state.json"):
        s = json.loads(state.read_text())
        if s.get("stage") == "done" and s.get("topic", {}).get("id"):
            done.add(s["topic"]["id"])
    return done


def topic_for(date, root):
    """Shu kun uchun mavzu: sanasi kelgan, hali chiqmagan eng birinchi reja punkti yoki None."""
    data = _load()
    done = _published(root)
    for item in sorted(data["posts"], key=lambda p: p["date"]):
        if item["date"] <= date and item["id"] not in done:
            return {"id": item["id"], "title": item["title"], "rubrics": item.get("rubrics", []),
                    "source": data.get("source", ""),
                    "script": data.get("rules", "") + "\n\n" + item["script"]}
    return None


def next_date(after):
    """Rejadagi keyingi post sanasi (after'dan keyin) yoki None."""
    if not enabled():
        return None
    dates = sorted(p["date"] for p in _load()["posts"] if p["date"] > after)
    return dates[0] if dates else None
