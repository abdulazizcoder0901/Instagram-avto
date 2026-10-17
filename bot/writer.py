"""Claude yordamida Notion mavzusidan carousel ssenariysi va post matnini yozish."""
import json

import anthropic

MODEL = "claude-opus-5-5"

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
- Ishlatilmaydigan maydonlarni bo'sh qator ("") qilib qoldir.

caption: 2–4 qisqa abzats; birinchi qator hook; oxirida izohga chaqiriq va 5–8 ta mos hashtag.
alt_text: carousel mazmunining bir gaplik tavsifi.
music_query: Instagram musiqa kutubxonasidan qidirish uchun 2–4 so'zli inglizcha so'rov (kayfiyat/janr, masalan "calm lofi piano").
music_suggestions: postga mos 5 ta mashhur trek (Instagram'da odatda bor bo'lgan), title va artist bilan.
"""

SLIDE = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": ["cover", "content", "cta"]},
        "kicker": {"type": "string"},
        "title": {"type": "string"},
        "subtitle": {"type": "string"},
        "body": {"type": "string"},
    },
    "required": ["type", "kicker", "title", "subtitle", "body"],
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


def _call(messages):
    client = anthropic.Anthropic()
    for _ in range(4):
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=SYSTEM,
            output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}],
            messages=messages,
        )
        if response.stop_reason == "pause_turn":
            messages = messages + [{"role": "assistant", "content": response.content}]
            continue
        if response.stop_reason == "refusal":
            raise RuntimeError("Claude bu mavzuni yozishni rad etdi")
        if response.stop_reason == "max_tokens":
            raise RuntimeError("Javob juda uzun bo'lib ketdi (max_tokens)")
        text = [b.text for b in response.content if b.type == "text"]
        return _validate(json.loads(text[-1]))
    raise RuntimeError("Claude javobni yakunlamadi")


def _validate(post):
    slides = post["slides"]
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
    return _call([{"role": "user", "content": prompt}])


def revise_post(topic, script, recent, previous, feedback):
    prompt = (
        f"Mavzu: {topic['title']}\n\nNotion'dagi ssenariy:\n{script or '—'}\n\n"
        f"Oxirgi chiqqan mavzular (takrorlama): {'; '.join(recent) or '—'}\n\n"
        f"Oldingi variant (JSON):\n{json.dumps(previous, ensure_ascii=False)}\n\n"
        f"Sahifa egasining izohi:\n{feedback}\n\n"
        "Izohga to'liq amal qilib, postni qayta yoz. Izohda tilga olinmagan yaxshi joylarni saqlab qol."
    )
    return _call([{"role": "user", "content": prompt}])
