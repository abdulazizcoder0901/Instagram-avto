"""Claude yordamida Notion mavzusidan carousel ssenariysi va post matnini yozish.

Claude Code CLI (`claude -p`) orqali ishlaydi: CLAUDE_CODE_OAUTH_TOKEN bilan Claude obunasi
hisobidan, alohida API to'lovisiz.
"""
import json
import subprocess

SYSTEM = """Sen @mr_abdulazz Instagram sahifasi uchun o'zbek tilida carousel postlar yozadigan muharrirsan.

Auditoriya: telefonda tez varaqlaydigan o'zbek yoshlari. Sahifa rubrikalari: qiziqarli faktlar,
foydali AI vositalar, ma'lumot beruvchi va ko'ngilochar kontent.

Qoidalar:
- Til: lotin yozuvidagi sodda, jonli o'zbek tili. Qisqa gaplar. Rus/ingliz so'zlarini keraksiz ishlatma.
- Birinchi slayd — kuchli hook: qiziqish uyg'otadigan raqam, kutilmagan fakt yoki savol. Odam surib ko'rmasdan qololmasin.
- Juda umumiy, "AI yozgandek" kontent yozma ("bugungi kunda", "zamonaviy dunyoda", "muhim ahamiyatga ega" kabi bo'sh iboralar yo'q).
- Har bir fikrga aniq misol, raqam, nom yoki qiyoslash qo'sh. Mavzu imkon bersa, o'quvchi o'zi qo'llay oladigan amaliy maslahat yoki saboq ber.
- Faktlar to'g'ri bo'lsin: raqam, sana, narxlarni web_search bilan tekshir. Aniq bo'lmasa "taxminan", "aytilishicha" deb yoz yoki umuman yozma.
- Oxirgi chiqqan mavzularni va ularning hook uslubini takrorlama — boshqacha burchakdan yondash.
- Notion'dagi ssenariy — xomaki g'oya. Uni asos qil, lekin yaxshilab qayta yoz.

Carousel tuzilmasi (jami 6–8 slayd):
- 1-slayd type="cover": kicker (1–3 so'z, masalan "Bilasizmi?"), title (6–8 so'zgacha), subtitle (bitta qisqa gap).
- O'rtadagi slaydlar type="content": title (3–7 so'z), body (15–40 so'z). Har slaydda bitta fikr.
- Oxirgi slayd type="cta": title — izoh yozishga undaydigan savol yoki chaqiriq, body — obuna/saqlashga chaqiriq.
- type="image" — sahifa egasi yuborgan rasm bilan slayd: image (rasm fayl nomi, aynan berilgan nom),
  title (3–7 so'z, rasmda nima ekani), body (ixtiyoriy, 20 so'zgacha izoh). Faqat egasi yuborgan rasmlar uchun.
- Ishlatilmaydigan maydonlarni bo'sh qator ("") qilib qoldir; image maydoni faqat type="image" da to'ldiriladi.

Sahifa egasining izohlari va rasmlari:
- Izohni so'zma-so'z emas, maqsadini tushunib bajar. Masalan "real misollar qo'sh" — aniq, haqiqiy
  holatlar (kim, qayerda, qachon, qancha) bilan alohida slaydlar qo'sh va ularni web_search bilan tekshir.
- Egasi rasm yuborsa, avval Read bilan har birini ko'r.
  * Rasm postga qo'yish uchun bo'lsa (foto, skrinshot, haqiqiy misol, "shuni qo'y", "slaydlar orasiga") —
    type="image" slayd qilib, mos joyga qo'y va sarlavhada rasmda nima ekanini tushuntir.
  * Rasm namuna/reference bo'lsa ("shunga o'xshash", "shu uslubda", boshqa sahifaning posti) — uni postga
    qo'yma; undagi hook, tuzilma, ohang va misol berish usulini o'rganib, o'z postingga qo'lla.
  * Aniq aytilmagan bo'lsa: mavzuga oid foto/misol bo'lsa — postga qo'y, boshqa sahifaning tayyor posti bo'lsa — reference deb qabul qil.

caption: 2–4 qisqa abzats; birinchi qator hook; oxirida izohga chaqiriq va 5–8 ta mos hashtag.
alt_text: carousel mazmunining bir gaplik tavsifi.
music_query: Instagram musiqa kutubxonasidan qidirish uchun 2–4 so'zli inglizcha so'rov (kayfiyat/janr, masalan "calm lofi piano").
music_suggestions: postga mos 5 ta mashhur trek (Instagram'da odatda bor bo'lgan), title va artist bilan.
"""

SLIDE = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": ["cover", "content", "image", "cta"]},
        "kicker": {"type": "string"},
        "title": {"type": "string"},
        "subtitle": {"type": "string"},
        "body": {"type": "string"},
        "image": {"type": "string"},
    },
    "required": ["type", "kicker", "title", "subtitle", "body", "image"],
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
        if slide["type"] == "image" and slide["image"] not in image_names:
            slide.update(type="content", image="")
    if not 3 <= len(slides) <= 10:
        raise ValueError(f"Slaydlar soni noto'g'ri: {len(slides)}")
    if slides[0]["type"] != "cover" or slides[-1]["type"] != "cta":
        raise ValueError("Birinchi slayd cover, oxirgisi cta bo'lishi kerak")
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
