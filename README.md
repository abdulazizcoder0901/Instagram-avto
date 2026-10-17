# Instagram-avto

Har kuni @mr_abdulazz uchun carousel post: **Notion → Claude → slaydlar → Telegram'da tasdiqlash → Buffer → Instagram**.

## Har kuni nima bo'ladi

1. **09:40** — GitHub Actions ishga tushadi va Notion'dan bugungi mavzuni oladi: sanasi bugun yoki
   undan oldin bo'lgan, hali "Post" bo'lmagan eng birinchi mavzu. Bir kunga 2 ta mavzu tushsa yoki bir
   kun o'tib ketsa, mavzu yo'qolmaydi: keyingi kuni chiqadi.
2. Claude Notion'dagi ssenariy asosida carousel yozadi (hook, amaliy misollar, faktlarni internetdan
   tekshiradi) va slaydlar (1080×1350) chiziladi. Slaydlar `posts/<sana>/` papkasiga saqlanadi.
3. **10:00** — Telegram bot'ga slaydlar va post matni keladi, ostida 2 ta tugma bo'ladi:
   - **✅ Tasdiqlash** — musiqa tanlash bosqichiga o'tadi;
   - **❌ Yoqmadi** — bot nimani o'zgartirish kerakligini so'raydi. Siz yozasiz, Claude postni qayta
     yozadi va yangi variantni yuboradi. Tugmani bosmasdan to'g'ridan-to'g'ri izoh yozsangiz ham bo'ladi.
4. Musiqa: bot 5 ta variant beradi, siz raqamini bosasiz yoki yozasiz (0 — musiqasiz).
5. Post Buffer'ga yuboriladi va Buffer'dagi bugungi vaqtda chiqadi. Agar bugungi vaqt o'tib ketgan
   bo'lsa, darhol chiqadi. Notion'da mavzu "Post" deb belgilanadi.

Agar soat ~15:10 gacha javob bermasangiz, o'sha kungi post yuborilmaydi. Davom ettirish uchun:
GitHub → **Actions** → **Daily Instagram post** → **Run workflow**. Bot to'xtagan joyidan davom etadi.

### Musiqa haqida

Buffer musiqani Instagram postga avtomatik qo'sha oladi, lekin buning uchun Instagram akkaunt
Buffer'ga **Facebook Login orqali** ulangan bo'lishi kerak (Buffer → Channels → Instagram → Reconnect).
- Shunday ulangan bo'lsa: bot Instagram kutubxonasidan haqiqiy treklarni taklif qiladi, tanlangani
  postga o'zi qo'shiladi.
- Ulanmagan bo'lsa: bot Claude tavsiya qilgan treklarni ko'rsatadi. Musiqa tanlasangiz, post vaqtida
  Buffer telefoningizga eslatma yuboradi va siz Instagram ilovasida musiqani qo'shib post qilasiz.
  0 ni tanlasangiz, post musiqasiz, o'zi avtomatik chiqadi.

## Bir martalik sozlash

GitHub repo → **Settings → Secrets and variables → Actions → New repository secret** bo'limiga
quyidagi 5 ta secret qo'shiladi:

| Secret | Qayerdan olinadi |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram'da [@BotFather](https://t.me/BotFather) → `/newbot` → bergan token. Keyin o'z bot'ingizni ochib **Start** bosing. |
| `TELEGRAM_CHAT_ID` | [@userinfobot](https://t.me/userinfobot) ga istalgan xabar yozing, u `Id` raqamingizni beradi. Bot faqat shu chatga javob beradi. |
| `CLAUDE_CODE_OAUTH_TOKEN` | Kompyuterda Terminal'da `curl -fsSL https://claude.ai/install.sh \| bash`, keyin `claude setup-token` buyrug'ini bering. Brauzerda Claude akkauntingizga kiring, terminal `sk-ant-oat01-...` token beradi. Claude obunangiz hisobidan ishlaydi, qo'shimcha to'lov yo'q. |
| `NOTION_TOKEN` | [notion.so/profile/integrations](https://www.notion.so/profile/integrations) → New integration → Internal → secret'ni nusxalang. Keyin Notion'da **Kontent Plan** sahifasi → `•••` → **Connections** → shu integratsiyani qo'shing. |
| `BUFFER_API_KEY` | [publish.buffer.com/settings/api](https://publish.buffer.com/settings/api) |

Workflow faqat **asosiy (`main`) branch'da** turganida har kuni o'zi ishga tushadi.

## Tuzilma

```
bot/main.py        kunlik jarayon (holat: posts/<sana>/state.json)
bot/writer.py      Claude: post yozish va izoh bo'yicha qayta yozish
bot/notion.py      mavzuni olish, "Post" deb belgilash
bot/telegram.py    Telegram bot
bot/buffer.py      Buffer: jadval, musiqa, post yaratish
scripts/carousel.py  slaydlarni chizish (JSON → JPEG)
posts/<sana>/vN/   har bir variantning slaydlari va matni
```

Slaydlar Buffer'ga `raw.githubusercontent.com/.../<commit-sha>/...` linki orqali beriladi. Repo
public bo'lgani uchun link login so'ramaydi, commit SHA bilan bo'lgani uchun esa hech qachon o'zgarmaydi.

Slaydni qo'lda chizib ko'rish:

```bash
pip install -r requirements.txt
python3 scripts/carousel.py posts/<sana>/v1/post.json
```
