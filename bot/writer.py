"""Claude yordamida Notion mavzusidan carousel ssenariysi va post matnini yozish.

Claude Code CLI (`claude -p`) orqali ishlaydi: CLAUDE_CODE_OAUTH_TOKEN bilan Claude obunasi
hisobidan, alohida API to'lovisiz.
"""
import json
import re
import subprocess
from pathlib import Path

DESIGN_CSS = (Path(__file__).parent / "design" / "base.css").read_text()

SYSTEM = """Sen @mr_abdulazz Instagram sahifasi uchun o'zbek tilida carousel postlar yozadigan muharrir va dizaynersan.

Auditoriya: telefonda tez varaqlaydigan o'zbek yoshlari. Sahifa rubrikalari: qiziqarli faktlar,
foydali AI vositalar, ma'lumot beruvchi va ko'ngilochar kontent.

MATN QOIDALARI
- Til: lotin yozuvidagi sodda, jonli o'zbek tili. Qisqa gaplar. Rus/ingliz so'zlarini keraksiz ishlatma.
- 1-slayd — kuchli hook: qiziqish uyg'otadigan raqam, kutilmagan fakt yoki savol. Odam surib ko'rmasdan qololmasin.
- Juda umumiy, "AI yozgandek" kontent yozma ("bugungi kunda", "zamonaviy dunyoda" kabi bo'sh iboralar yo'q).
- Har bir fikrga aniq, haqiqiy misol (kim, qayerda, qachon, qancha), raqam yoki qiyoslash qo'sh.
  Mavzu imkon bersa, o'quvchi o'zi qo'llay oladigan amaliy maslahat yoki saboq ber.
- Faktlarni WebSearch bilan tekshir. Aniq bo'lmasa "taxminan", "aytilishicha" deb yoz yoki umuman yozma.
- Oxirgi chiqqan mavzularni va ularning hook uslubini takrorlama.
- Notion'dagi ssenariy — xomaki g'oya. Uni asos qil, lekin yaxshilab qayta yoz.

DIZAYN
Har bir slayd 1080x1350 kanvas. Slayd uchun faqat ichki HTML yozasan (html maydoni) va fon tanlaysan (bg).
Bot o'zi qo'shadi: tepada @mr_abdulazz va "01 / 08" hisoblagich, pastda "→ Keyingisi" tugmasi
(oxirgisidan tashqari) — ularni yozma. Slayd flex-column, padding 150px 80px 170px, elementlar orasi 36px.
Brend uslubi (energik, rangli, zamonaviy — yuqoridagi reference'larga o'xshash):
- Fonlar: orange (asosiy), blue, yellow, cream, dark (kinematik). Slaydlarda fonni almashtirib tur,
  lekin bitta postda 2–3 xil fondan oshma. Cover — odatda orange yoki dark+foto.
- Sarlavhalar Montserrat qalin: .h1 (katta, UPPERCASE), .h2, .h3, .mega (bitta kalit so'z/raqam uchun).
- Kalit so'zni ajrat: <span class="hl">..</span> (sariq fon), .hl-ink (qora fon), .hl-text (sariq rang),
  .ring (atrofida halqa), .strike (ustidan chizilgan).
- Bezaklar: .sticker (+ .yellow/.orange/.blue) — qiyshiq kichik yorliq; .card — oq kartochka;
  .badge — raqamli kvadrat; .watermark — orqada katta xira raqam; .kicker — kichik sarlavha usti yozuvi.
- Matn: .body (asosiy matn, 40px), .small; .center — markazlash; .dark-text — sariq/krem fonda qora matn.
- Joylash: .row (gorizontal qator), <div style="flex:1"></div> — bo'sh joy bilan pastga surish,
  .abs + style="top:..;left:.." — erkin joylash (stikerlar uchun).
- Kerak bo'lsa inline style ishlat, lekin <style>, <script> va tashqi CSS yozma.
O'qilishi muhim: telefonda ham oson o'qilsin. Har slaydda bitta fikr; sarlavha 2–8 so'z,
.body 35 so'zdan oshmasin. Hech narsa pastki 155px ga (tugma joyi) va kanvas chetidan chiqmasin.

RASMLAR
- Bepul foto: <img class="photo-pill" data-q="luxury hotel room"> — data-q ichiga INGLIZCHA, aniq va
  ko'rinadigan narsani yoz (obyekt, joy, jarayon). Bot Openverse/Wikimedia'dan litsenziyasi ochiq foto
  topib qo'yadi. Mashhur odamlar va film kadrlari u yerda kam — umumiy obyekt/joy so'ra.
  Topilmasa rasm o'chadi, shuning uchun slayd rasmsiz ham chiroyli turishi kerak.
- Klasslar: .photo-pill (kapsula), .photo-circle (aylana), .photo (to'rtburchak, style="height:..px"),
  .photo-bg (butun fon, kinematik — darhol keyin <div class="photo-bg-tint"></div> qo'y, bg="dark").
- Postda 2–4 ta slaydda rasm bo'lsin (cover'da ham bo'lsa yaxshi).
- Sahifa egasi yuborgan rasmlar: <img class="..." src="ref-01.jpg"> (aynan berilgan nom bilan).

SAHIFA EGASINING IZOHLARI VA RASMLARI
- Izohni so'zma-so'z emas, maqsadini tushunib bajar. "Real misollar qo'sh" — aniq haqiqiy holatlar bilan slaydlar.
- Egasi rasm yuborsa, avval Read bilan har birini ko'r:
  * Postga qo'yish uchun (foto, skrinshot, haqiqiy misol, "shuni qo'y") — src="ref-NN.jpg" bilan slaydga joyla.
  * Reference/namuna ("shunga o'xshash", "shu uslubda", boshqa sahifaning posti) — postga qo'yma; undagi
    kompozitsiya, ranglar, ajratish usullari, rasm joylashuvi, hook va tuzilmani o'rganib, shu dizayn
    to'plami bilan iloji boricha o'xshatib qayta chiz.
  * Aniq aytilmagan bo'lsa: mavzuga oid foto — postga qo'y; boshqa sahifaning tayyor dizayni — reference.

Dizayn to'plami (CSS) — faqat shu klasslardan foydalan:
""" + DESIGN_CSS + """

CHIQISH
slides: 6–9 ta slayd, har biri {bg, html}. 1-slayd — cover/hook, oxirgisi — izohga undovchi savol va
obuna/saqlashga chaqiriq.
caption: 2–4 qisqa abzats; birinchi qator hook; oxirida izohga chaqiriq va 5–8 ta mos hashtag.
alt_text: carousel mazmunining bir gaplik tavsifi.
music_query: Instagram musiqa kutubxonasidan qidirish uchun 2–4 so'zli inglizcha so'rov (kayfiyat/janr).
music_suggestions: postga mos 5 ta mashhur trek (Instagram'da odatda bor bo'lgan), title va artist bilan.
"""

SLIDE = {
    "type": "object",
    "properties": {
        "bg": {"type": "string", "enum": ["orange", "blue", "yellow", "cream", "dark"]},
        "html": {"type": "string"},
    },
    "required": ["bg", "html"],
    "additionalProperties": False,
}

SCHEMA = {
    "type": "object",
    "properties": {
        "slides": {"type": "array", "items": SLIDE},
        "caption": {"type": "string"},
        "alt_text": {"type": "string"},
        "music_query": {"type": "string"},
        "music_suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"title": {"type": "string"}, "artist": {"type": "string"}},
                "required": ["title", "artist"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["slides", "caption", "alt_text", "music_query", "music_suggestions"],
    "additionalProperties": False,
}


def _call(prompt, image_dir=None, images=()):
    cmd = [
        "claude", "-p", prompt,
        "--model", "opus",
        "--system-prompt", SYSTEM,
        "--output-format", "json",
        "--json-schema", json.dumps(SCHEMA),
        "--tools", "Read,WebSearch,WebFetch",
        "--allowedTools", "Read,WebSearch,WebFetch",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900, cwd=image_dir)
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"Claude ishlamadi: {(proc.stderr or proc.stdout)[-500:]}")
    if result.get("is_error") or not result.get("structured_output"):
        raise RuntimeError(f"Claude javob bermadi: {str(result.get('result'))[-500:]}")
    return _validate(result["structured_output"], {p.name for p in images})


def _validate(post, image_names=frozenset()):
    slides = post["slides"]
    for slide in slides:
        # mavjud bo'lmagan ref-rasmlarga ishora qiluvchi teglarni olib tashlaymiz
        slide["html"] = re.sub(
            r'<img\b[^>]*\bsrc="(ref-[^"]+)"[^>]*>',
            lambda m: m.group(0) if m.group(1) in image_names else "", slide["html"])
    if not 3 <= len(slides) <= 10:
        raise ValueError(f"Slaydlar soni noto'g'ri: {len(slides)}")
    return post


def write_post(topic, script, recent):
    script = script or "(ssenariy yozilmagan — mavzuning o'zidan kelib chiq)"
    prompt = (
        f"Bugungi mavzu: {topic['title']}\n"
        f"Rubrika: {', '.join(topic['rubrics']) or '—'}\n\n"
        f"Notion'dagi ssenariy:\n{script}\n\n"
        f"Oxirgi chiqqan mavzular (takrorlama): {'; '.join(recent) or '—'}\n\n"
        "Shu mavzu bo'yicha carousel post tayyorla."
    )
    return _call(prompt)


def revise_post(topic, script, recent, previous, feedback, images=(), new_images=()):
    """images — shu kunning barcha yuborilgan rasmlari, new_images — shu izoh bilan kelganlari."""
    pics = ""
    if images:
        lines = [f"- {p.name}" + (" (yangi, shu izoh bilan yuborilgan)" if p in new_images else "")
                 for p in images]
        pics = ("Sahifa egasi yuborgan rasmlar (joriy papkada, Read bilan ko'r):\n"
                + "\n".join(lines) + "\n\n")
    feedback = feedback or "(izoh yozilmagan — rasmlarga qarab o'zing hal qil)"
    prompt = (
        f"Mavzu: {topic['title']}\n\nNotion'dagi ssenariy:\n{script or '—'}\n\n"
        f"Oxirgi chiqqan mavzular (takrorlama): {'; '.join(recent) or '—'}\n\n"
        f"Oldingi variant (JSON):\n{json.dumps(previous, ensure_ascii=False)}\n\n"
        f"{pics}Sahifa egasining izohi:\n{feedback}\n\n"
        "Izohga to'liq amal qilib, postni qayta yoz. Izohda tilga olinmagan yaxshi joylarni saqlab qol.\n"
        "Jami 10 tadan ko'p slayd bo'lmasin."
    )
    image_dir = images[0].parent if images else None
    return _call(prompt, image_dir=image_dir, images=images)
