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
from scripts.carousel import render_slides

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

    def add_version(self, post):
        v = self.version + 1
        out = self.version_dir(v)
        render_slides(post["slides"], out, assets_dir=self.refs_dir)
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


def send_music_menu(tg, day):
    post = day.post()
    options = buffer.music_options(post["music_query"])
    if options:
        day.state.update(music_mode="catalog", music_options=options)
        note = "Tanlangan musiqa postga avtomatik qo'shiladi."
    else:
        options = [{"id": None, **m} for m in post["music_suggestions"][:5]]
        day.state.update(music_mode="reminder", music_options=options)
        note = ("Buffer'da Instagram musiqa katalogi ulanmagan. Musiqa tanlasangiz, post vaqtida Buffer "
                "telefoningizga eslatma yuboradi: Instagram'da shu musiqani qo'shib, post qilasiz.\n"
                "0 tanlasangiz, post musiqasiz, o'zi avtomatik chiqadi.")
    day.state["stage"] = "music"
    day.save()
    lines = [f"{i}. {o['title']}" + (f" — {o['artist']}" if o["artist"] else "") for i, o in enumerate(options, 1)]
    tg.send("🎵 Musiqani tanlang (tugmani bosing yoki raqamini yozing):\n\n" + "\n".join(lines)
            + f"\n0. Musiqasiz\n\n{note}",
            buttons=[[(str(i), f"music:{i}") for i in range(1, len(options) + 1)], [("0 · Musiqasiz", "music:0")]])


def publish(tg, day, choice):
    post = day.post()
    urls = day.image_urls()
    for url in urls:
        wait_public(url)
    due = buffer.publish_time(now())
    option = day.state["music_options"][choice - 1] if choice else None
    reminder = False
    if option and day.state["music_mode"] == "catalog":
        try:
            created = buffer.create_post(urls, post["caption"], post["alt_text"], due, music=option["id"])
        except RuntimeError as e:
            tg.send(f"⚠️ Musiqani avtomatik qo'shib bo'lmadi ({e}). Eslatma rejimida yuboraman.")
            reminder = True
    elif option:
        reminder = True
    else:
        created = buffer.create_post(urls, post["caption"], post["alt_text"], due)
    if reminder:
        label = option["title"] + (f" — {option['artist']}" if option["artist"] else "")
        created = buffer.create_post(urls, post["caption"], post["alt_text"], due, music=label, reminder=True)

    notion.mark_posted(day.state["topic"]["id"], day.date)
    day.state.update(stage="done", buffer_post_id=created["id"], music_choice=choice)
    day.save()
    commit([day.dir], f"Post {day.date}: Buffer'ga yuborildi")

    when = f"bugun soat {due:%H:%M} da" if due else "hozir"
    if reminder:
        tg.send(f"✅ Buffer'ga qo'yildi. {when.capitalize()} Buffer ilovasi eslatma yuboradi — "
                f"Instagram'da 🎵 «{label}» ni qo'shib post qiling.")
    else:
        tg.send(f"✅ Tayyor! Post {when} Instagram'ga chiqadi."
                + (f"\n🎵 {option['title']}" if option else ""))


def wait_until(hhmm):
    hh, mm = map(int, hhmm.split(":"))
    target = now().replace(hour=hh, minute=mm, second=0, microsecond=0)
    if now() < target:
        time.sleep((target - now()).total_seconds())


def run():
    started = now()
    date = os.environ.get("POST_DATE") or started.strftime("%Y-%m-%d")
    deadline = started + timedelta(minutes=int(os.environ.get("DEADLINE_MINUTES", "330")))
    tg = Telegram()
    day = Day(date)

    if day.state.get("stage") == "done":
        tg.send(f"ℹ️ {date} uchun post allaqachon Buffer'ga yuborilgan.")
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

    if not day.version:
        day.add_version(writer.write_post(topic, script, recent))

    if os.environ.get("SEND_AT"):
        wait_until(os.environ["SEND_AT"])
    tg.skip_pending()
    if day.state.get("stage") == "music":
        send_music_menu(tg, day)
    else:
        day.state["stage"] = "review"
        send_review(tg, day)

    pending = []  # izohsiz kelgan rasmlar: keyingi izoh bilan birga ishlatiladi
    while now() < deadline:
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
            if action == "music" and stage != "music":
                continue
            tg.clear_buttons(msg_id)
            if action == "approve":
                send_music_menu(tg, day)
            elif action == "reject":
                day.state["stage"] = "feedback"
                day.save()
                tg.send("✏️ Nimani o'zgartiray? Yozib yuboring.\n"
                        "Masalan: «hookni kuchliroq qil», «real misollar qo'sh», «3-slaydni qisqartir».\n\n"
                        "📎 Rasm ham yuborishingiz mumkin: postga qo'yish uchun (foto, skrinshot, haqiqiy misol) "
                        "yoki namuna sifatida («shunga o'xshash qil»). Rasm izohiga nima qilishni yozing.")
            elif action == "music":
                publish(tg, day, int(arg))
                return

        texts = [e[1] for e in events if e[0] == "text"]
        photos = [e for e in events if e[0] == "photo"]
        stage = day.state["stage"]
        if stage == "music" and texts and texts[-1].isdigit() and int(texts[-1]) <= len(day.state["music_options"]):
            publish(tg, day, int(texts[-1]))
            return
        if stage not in ("review", "feedback") or not (texts or photos):
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
        day.add_version(revised)
        send_review(tg, day)

    day.save()
    commit([day.dir], f"Post {date}: tasdiqlanmadi")
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
