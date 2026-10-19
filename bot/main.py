"""Kunlik carousel post: Notion → Claude → slaydlar → Telegram'da tasdiqlash → Buffer → Instagram.

GitHub Actions har kuni ishga tushiradi (.github/workflows/daily-post.yml):
    python -m bot.main
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from bot import buffer, notion, writer
from bot.telegram import Telegram
from bot.render import render_post

TZ = ZoneInfo("Asia/Tashkent")
ROOT = Path(__file__).resolve().parent.parent
REPO = os.environ.get("GITHUB_REPOSITORY", "abdulazizcoder0901/Instagram-avto")


def now():
    return datetime.now(TZ)


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def commit(paths, message):
    """Fayllarni commit qilib push qiladi va commit SHA'sini qaytaradi."""
    git("add", *[str(p) for p in paths])
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        return git("rev-parse", "HEAD")
    git("commit", "-m", message)
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    for attempt in range(4):
        try:
            git("pull", "--rebase", "origin", branch)
            git("push", "origin", branch)
            break
        except subprocess.CalledProcessError:
            if attempt == 3:
                raise
            time.sleep(2 ** (attempt + 1))
    return git("rev-parse", "HEAD")


def wait_public(url, tries=20):
    for _ in range(tries):
        if requests.head(url, timeout=20).status_code == 200:
            return
        time.sleep(6)
    raise RuntimeError(f"Rasm internetda ochilmadi: {url}")


class Day:
    """Bir kunlik post holati: posts/<sana>/state.json"""

    def __init__(self, date):
        self.date = date
        self.dir = ROOT / "posts" / date
        self.state_path = self.dir / "state.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {}

    def save(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2))

    @property
    def version(self):
        return self.state.get("version", 0)

    def version_dir(self, v=None):
        return self.dir / f"v{v or self.version}"

    def post(self):
        return json.loads((self.version_dir() / "post.json").read_text())

    def slides(self):
        return sorted(self.version_dir().glob("[0-9][0-9].jpg"))

    @property
    def refs_dir(self):
        # Telegram'dan kelgan rasmlar; git'ga qo'shilmaydi, faqat slaydlarga chizilgani chiqadi
        return self.dir / "refs"

    def refs(self):
        return sorted(self.refs_dir.glob("ref-*.jpg"))

    def add_version(self, post, fix=None):
        """Slaydlarni chizadi. Matn sig'masa yoki rasm ochilmasa, fix(post, muammolar) bilan bir marta tuzatadi."""
        v = self.version + 1
        out = self.version_dir(v)
        _, credits, problems = render_post(post["slides"], out, self.refs_dir)
        if problems and fix:
            report = "\n".join(f"{n}-slayd: {'; '.join(items)}" for n, items in problems.items())
            post = fix(post, report)
            _, credits, problems = render_post(post["slides"], out, self.refs_dir)
        post["caption"] = post["caption"].split("\n\n📷 ")[0]
        if credits:
            post["caption"] += "\n\n📷 " + "; ".join(credits)
        (out / "post.json").write_text(json.dumps(post, ensure_ascii=False, indent=2))
        self.state.update(version=v, stage="review")
        self.save()
        commit([self.dir], f"Post {self.date}: {self.state['topic']['title']} (v{v})")

    def image_urls(self):
        # slaydlar qo'shilgan commit: shu SHA bilan link hech qachon o'zgarmaydi
        sha = git("log", "-1", "--format=%H", "--", str(self.version_dir()))
        return [f"https://raw.githubusercontent.com/{REPO}/{sha}/{p.relative_to(ROOT).as_posix()}"
                for p in self.slides()]


def send_review(tg, day):
    post = day.post()
    tg.send_album(day.slides())
    tg.send(
        f"📌 {day.state['topic']['title']}\n🗓 {day.date} · {day.version}-variant\n\n{post['caption']}",
        buttons=[[("✅ Tasdiqlash", f"approve:{day.version}"), ("❌ Yoqmadi", f"reject:{day.version}")]],
    )


def send_confirm(tg, day):
    day.state["stage"] = "confirm"
    day.save()
    tg.send("❓ Rostdan ham shu variantni tasdiqlaysizmi?\n"
            "Keyin post Instagram'ga o'zi chiqadi.",
            buttons=[[("✅ Ha, tasdiqlayman", f"confirm:{day.version}"), ("↩️ Yo'q", f"back:{day.version}")]])


def _when(due):
    if not due:
        return "hozir"
    due = due.astimezone(TZ)
    word = {0: "bugun", 1: "ertaga"}.get((due.date() - now().date()).days, f"{due:%d.%m}")
    return f"{word} soat {due:%H:%M} da"


def publish(tg, day):
    post = day.post()
    urls = day.image_urls()
    for url in urls:
        wait_public(url)
    due = buffer.publish_time(now(), day.date)
    created = buffer.create_post(urls, post["caption"], post["alt_text"], due)

    notion.mark_posted(day.state["topic"]["id"], day.date)
    day.state.update(stage="done", buffer_post_id=created["id"], due_at=due.isoformat() if due else None)
    day.save()
    commit([day.dir], f"Post {day.date}: Buffer'ga yuborildi")

    tg.send(f"✅ Tayyor! Post {_when(due)} Instagram'ga o'zi chiqadi."
            + ("\n\n🔧 Xato topsangiz, chiqishidan oldin /repair yuboring." if due else ""))


def check_published(tg, day):
    """Chiqish vaqti o'tgan postni tekshiradi. Instagram qabul qilmagan bo'lsa bir marta qayta yuboradi.
    Natija aniq bo'lsa (chiqdi yoki ikkinchi marta ham xato) True."""
    if day.state.get("stage") != "done" or not day.state.get("buffer_post_id") or day.state.get("checked"):
        return True
    status, link, error = buffer.post_result(day.state["buffer_post_id"])
    if status == "sent":
        tg.send(f"📢 {day.date} posti Instagram'ga chiqdi ✅" + (f"\n{link}" if link else ""))
    elif status == "error" and not day.state.get("retried"):
        post = day.post()
        created = buffer.create_post(day.image_urls(), post["caption"], post["alt_text"])
        day.state.update(buffer_post_id=created["id"], retried=True)
        day.save()
        commit([day.dir], f"Post {day.date}: qayta yuborildi")
        tg.send(f"⚠️ Instagram {day.date} postini qabul qilmadi ({error}). Hozir qayta yubordim.")
        return False
    elif status == "error":
        tg.send(f"❌ {day.date} posti yana chiqmadi: {error}\nBuffer'da postni ochib, «Retry» bosing.")
    else:
        return False
    day.state["checked"] = True
    day.save()
    commit([day.dir], f"Post {day.date}: natija tekshirildi")
    return True


def wait_published(tg, day, minutes=20):
    end = now() + timedelta(minutes=minutes)
    while not check_published(tg, day) and now() < end:
        time.sleep(60)


def repairable(day):
    """Tasdiqlangan post hali chiqmagan bo'lsa, uni /repair bilan qaytarib olish mumkin."""
    if day.state.get("stage") != "done" or not day.state.get("buffer_post_id"):
        return False
    if "due_at" not in day.state:
        status, due = buffer.post_status(day.state["buffer_post_id"])
        day.state["due_at"] = due if status == "scheduled" else None
    due = day.state["due_at"]
    return bool(due) and now() < datetime.fromisoformat(due) - timedelta(minutes=2)


def start_repair(tg, day):
    status, _ = buffer.post_status(day.state["buffer_post_id"])
    if status != "scheduled":
        day.state["due_at"] = None
        tg.send("⚠️ Post allaqachon chiqib bo'lgan, endi uni qaytarib bo'lmaydi.")
        return
    buffer.delete_post(day.state["buffer_post_id"])
    topic = day.state["topic"]
    notion.set_status(topic["id"], topic.get("status") or "Boshlanmagan")
    day.state.update(stage="feedback", buffer_post_id=None, due_at=None)
    day.save()
    commit([day.dir], f"Post {day.date}: tuzatish uchun qaytarildi")
    tg.send("🔧 Post navbatdan olindi, Instagram'ga chiqmaydi.\n\n"
            "✏️ Nimani tuzatay? Yozib yuboring (rasm ham bo'ladi). "
            "Yangi variantni yana tasdiqlaysiz.")


def _is_repair(text):
    return text.split("@")[0].strip().lower() in ("/repair", "repair")


def wait_until(hhmm):
    hh, mm = map(int, hhmm.split(":"))
    target = now().replace(hour=hh, minute=mm, second=0, microsecond=0)
    if now() < target:
        time.sleep((target - now()).total_seconds())


def run():
    started = now()
    # kechqurun (18:00 dan keyin) ertangi post tayyorlanadi, ertalab — bugungisi
    default = started + timedelta(days=1) if started.hour >= 18 else started
    date = os.environ.get("POST_DATE") or default.strftime("%Y-%m-%d")
    deadline = started + timedelta(minutes=int(os.environ.get("DEADLINE_MINUTES", "330")))
    tg = Telegram()
    day = Day(date)
    try:
        tg.set_commands([("repair", "Tasdiqlangan postni tuzatish")])
    except Exception:
        pass

    today = Day(started.strftime("%Y-%m-%d"))
    if today.date != date and not repairable(today):
        wait_published(tg, today)  # kechqurun: bugungi post chiqdimi?

    if day.state.get("stage") == "done" and not repairable(day):
        if os.environ.get("GITHUB_EVENT_NAME") != "schedule" and day.state.get("checked"):
            tg.send(f"ℹ️ {date} uchun post allaqachon Buffer'ga yuborilgan.")
        wait_published(tg, day)
        return

    if "topic" not in day.state:
        topic = notion.next_topic(date)
        if not topic:
            tg.send(f"ℹ️ {date}: Notion'da chiqmagan mavzu qolmadi. Yangi mavzu qo'shing.")
            return
        day.state["topic"] = topic
    topic = day.state["topic"]
    script = notion.page_text(topic["id"])
    recent = notion.recent_titles()

    def fixer(post, report):
        return writer.revise_post(topic, script, recent, post,
                                  "Texnik muammo, faqat shuni tuzat (mazmunni o'zgartirma):\n" + report,
                                  images=day.refs())

    if not day.version:
        day.add_version(writer.write_post(topic, script, recent), fix=fixer)

    if os.environ.get("SEND_AT"):
        wait_until(os.environ["SEND_AT"])
    if day.state.get("stage") != "done":
        # tasdiqlangan post kutilayotganda tunda yuborilgan /repair yo'qolmasin
        tg.skip_pending()
        if day.state.get("stage") == "confirm":
            send_confirm(tg, day)
        else:
            day.state["stage"] = "review"
            send_review(tg, day)

    pending = []  # izohsiz kelgan rasmlar: keyingi izoh bilan birga ishlatiladi
    while now() < deadline:
        if day.state["stage"] == "done" and not repairable(day):
            wait_published(tg, day)
            return
        events = tg.events()
        # albom bo'lib yuborilgan rasmlar bir necha qismda keladi — hammasini yig'ib olamiz
        while any(e[0] == "photo" for e in events[-1:] or []):
            more = tg.events(poll_seconds=3)
            if not more:
                break
            events += more

        for event in [e for e in events if e[0] == "button"]:
            stage = day.state["stage"]
            _, data, cb_id, msg_id = event
            action, _, arg = data.partition(":")
            tg.answer(cb_id)
            if action in ("approve", "reject") and (stage != "review" or int(arg) != day.version):
                continue
            if action in ("confirm", "back") and (stage != "confirm" or int(arg) != day.version):
                continue
            tg.clear_buttons(msg_id)
            if action == "approve":
                send_confirm(tg, day)
            elif action == "confirm":
                publish(tg, day)
            elif action == "back":
                day.state["stage"] = "review"
                day.save()
                tg.send("Yaxshi. O'zgartirish kerak bo'lsa, izoh yozing yoki rasm yuboring.",
                        buttons=[[("✅ Tasdiqlash", f"approve:{day.version}"), ("❌ Yoqmadi", f"reject:{day.version}")]])
            elif action == "reject":
                day.state["stage"] = "feedback"
                day.save()
                tg.send("✏️ Nimani o'zgartiray? Yozib yuboring.\n"
                        "Masalan: «hookni kuchliroq qil», «real misollar qo'sh», «3-slaydni qisqartir».\n\n"
                        "📎 Rasm ham yuborishingiz mumkin: postga qo'yish uchun (foto, skrinshot, haqiqiy misol) "
                        "yoki namuna sifatida («shunga o'xshash qil»). Rasm izohiga nima qilishni yozing.")

        texts = [e[1] for e in events if e[0] == "text"]
        photos = [e for e in events if e[0] == "photo"]
        if any(_is_repair(t) for t in texts):
            texts = [t for t in texts if not _is_repair(t)]
            if day.state["stage"] == "done":
                start_repair(tg, day)
                continue
            tg.send("ℹ️ Post hali tasdiqlanmagan — o'zgartirish kerak bo'lsa, shunchaki izoh yozing.")
        stage = day.state["stage"]
        if stage == "done" and (texts or photos):
            tg.send("✅ Post tasdiqlangan. Tuzatish kerak bo'lsa, /repair yuboring.")
            continue
        if stage not in ("review", "feedback", "confirm") or not (texts or photos):
            continue

        first = len(day.refs()) + 1
        new = [tg.download(e[1], day.refs_dir / f"ref-{first + i:02d}.jpg") for i, e in enumerate(photos)]
        feedback = "\n".join([e[2] for e in photos if e[2]] + texts)
        if not feedback:
            pending += new
            tg.send(f"📎 {len(new)} ta rasm qabul qilindi. Endi ular bilan nima qilishni yozing.\n"
                    "Masalan: «shu rasmlarni slaydlar orasiga qo'y» yoki «shu postlarga o'xshash uslubda yoz».")
            continue
        new, pending = pending + new, []
        tg.send("⏳ Izohingiz bo'yicha qayta yozyapman, 2–4 daqiqa..."
                + (f"\n📎 {len(new)} ta rasm ham hisobga olinadi." if new else ""))
        revised = writer.revise_post(topic, script, recent, day.post(), feedback,
                                     images=day.refs(), new_images=new)
        day.add_version(revised, fix=fixer)
        send_review(tg, day)

    day.save()
    if day.state["stage"] == "done":
        return
    commit([day.dir], f"Post {date}: tasdiqlanmadi")
    if date > now().strftime("%Y-%m-%d"):
        tg.send(f"⏰ {date} uchun post hali tasdiqlanmadi. Ertalab soat 08:00 da bot uni qayta yuboradi.")
        return
    tg.send("⏰ Bugungi post tasdiqlanmadi, Buffer'ga yuborilmadi.\n"
            "Davom ettirish uchun GitHub → Actions → «Daily Instagram post» → Run workflow.")


def main():
    try:
        run()
    except Exception as e:
        try:
            Telegram().send(f"⚠️ Bot xatolik bilan to'xtadi: {type(e).__name__}: {e}")
        finally:
            raise


if __name__ == "__main__":
    sys.exit(main())
