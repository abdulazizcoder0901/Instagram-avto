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

DIZAYN (sahifaning yagona uslubi)
Har bir slayd 1080x1350. Fonda butun ekran bo'ylab HAQIQIY foto turadi, bot uni oq-qora (kulrang)
qiladi va pastga qorong'i soya beradi. Ustida oq, markazlashtirilgan, toza matn (Inter shrifti):
katta qalin sarlavha, kalit qism kursivda — masalan: Marketingingizni tekshiradigan <span class="em">6 ta savol.</span>
Bot o'zi qo'shadi: fon rasmi va soya, pastda @mr_abdulazz, nuqtali progress va "→" aylana tugmasi —
ularni yozma. Har slayd uchun:
- position: "bottom" (matn pastki qismda — asosiy holat, foto yuqorida ko'rinib turadi),
  "center" (foto qorong'iroq, matn o'rtada — ro'yxat yoki ko'p matn uchun), "top" (matn tepada).
- html: faqat matn bloklari. Klasslar: .kicker (kichik ustki yozuv), .h1 (cover sarlavhasi), .h2, .h3,
  .num (katta raqam), .body (asosiy matn), .small, .em (kursiv ajratish), .soft (xiraroq), .tag (konturli
  yorliq), .glass (shaffof qorong'i panel), .list > .item > <b>1</b> matn (raqamli ro'yxat), .divider, .left.
  Inline style mumkin, lekin <style>, <script>, <img> yozma.
O'qilishi muhim: telefonda oson o'qilsin, minimal va premium. Har slaydda bitta fikr; sarlavha 2–8 so'z,
.body 30 so'zdan oshmasin. Matn pastki 245px ga (tugma va handle joyi) va tepadagi 120px ga kirmasin.

FON RASMLARI — HAQIQIY RASMLAR
Fon — mavzuning O'ZIGA oid haqiqiy rasm bo'lsin: film bo'lsa o'sha filmdan kadr (aktyor, sahna,
kostyum), joy bo'lsa o'sha joy, mahsulot/odam bo'lsa o'sha mahsulot/odam.
Bot rasmni maqolalarning asosiy rasmidan (og:image — ulashilganda chiqadigan katta rasm) oladi:
- photo_pages: WebSearch natijalarida chiqqan, asosiy rasmi aynan shu slayd mavzusini ko'rsatadigan
  1–3 ta maqola/sahifa linki (yangiliklar, kino saytlari, IMDb, Wikipedia, rasmiy sayt, Pinterest pin).
  Faqat qidiruv natijasida haqiqatan ko'rgan linklarni yoz — o'zingdan link to'qima.
  Har slaydga boshqa maqola ber, shunda rasmlar takrorlanmaydi (bot bir xil rasmni qayta qo'ymaydi).
- photo_search: zaxira uchun inglizcha aniq so'rov (bepul fotobazadan, agar maqolalardan rasm chiqmasa).
- photo_ref: sahifa egasi yuborgan rasm shu slayd foni bo'lishi kerak bo'lsa "ref-01.jpg", aks holda "".

SAHIFA EGASINING IZOHLARI VA RASMLARI
- Izohni so'zma-so'z emas, maqsadini tushunib bajar. "Real misollar qo'sh" — aniq haqiqiy holatlar bilan slaydlar.
- Egasi rasm yuborsa, avval Read bilan har birini ko'r:
  * Postga qo'yish uchun (foto, kadr, haqiqiy misol, "shuni qo'y") — o'sha slaydning photo_ref'iga
    "ref-NN.jpg" ni yoz.
  * Reference/namuna ("shunga o'xshash", "shu uslubda", boshqa sahifaning posti) — postga qo'yma;
    undagi hook, tuzilma, matn joylashuvi va ohangni o'rganib, shu uslub doirasida qo'lla.
  * Aniq aytilmagan bo'lsa: mavzuga oid foto — postga qo'y; boshqa sahifaning tayyor posti — reference.

Dizayn to'plami (CSS) — faqat shu klasslardan foydalan:
""" + DESIGN_CSS + """

CHIQISH
slides: 6–9 ta slayd, har biri {position, photo_pages, photo_search, photo_ref, html}. 1-slayd — cover/hook, oxirgisi — izohga undovchi savol va
obuna/saqlashga chaqiriq.
caption: 2–4 qisqa abzats; birinchi qator hook; oxirida izohga chaqiriq va 5–8 ta mos hashtag.
alt_text: carousel mazmunining bir gaplik tavsifi.
music_query: Instagram musiqa kutubxonasidan qidirish uchun 1–3 so'zli inglizcha kayfiyat/janr so'rovi
  ("epic cinematic", "calm piano", "upbeat electronic"). Biznes akkauntda faqat litsenziyali kutubxona
  musiqasi bor, mashhur qo'shiq nomlari topilmaydi — shuning uchun kayfiyat/janr yoz.
music_suggestions: postga mos 5 ta mashhur trek (Instagram'da odatda bor bo'lgan), title va artist bilan.
"""

SLIDE = {
    "type": "object",
    "properties": {
        "position": {"type": "string", "enum": ["bottom", "center", "top"]},
        "photo_pages": {"type": "array", "items": {"type": "string"}},
        "photo_search": {"type": "string"},
        "photo_ref": {"type": "string"},
        "html": {"type": "string"},
    },
    "required": ["position", "photo_pages", "photo_search", "photo_ref", "html"],
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
        # mavjud bo'lmagan ref-rasmlarni olib tashlaymiz
        if slide["photo_ref"] not in image_names:
            slide["photo_ref"] = ""
        slide["html"] = re.sub(r"<(img|script|style)\b[^>]*>", "", slide["html"])
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
