# Instagram-avto

Har kuni @mr_abdulazz uchun carousel post: **Notion → Claude → slaydlar → Telegram'da tasdiqlash → Buffer → Instagram**.

## Har kuni nima bo'ladi

Bot GitHub Actions'da **uzluksiz** ishlaydi: har bir ish ~5.5 soat davom etadi va oxirida keyingisini
o'zi ishga tushiradi (GitHub jadvali soatlab kechikishi mumkin, shuning uchun unga tayanmaymiz;
6 soatlik jadval faqat zaxira — zanjir uzilsa tiklaydi). Repo public bo'lgani uchun bepul.

1. **21:30** — bot Notion'dan **ertangi** mavzuni oladi: sanasi ertaga yoki undan oldin bo'lgan,
   hali "Post" bo'lmagan eng birinchi mavzu. Mavzu chiqmay qolsa, yo'qolmaydi: keyingi kuni chiqadi.
2. Claude Notion'dagi ssenariy bo'yicha carousel yozadi (ssenariy bo'lmasa — o'zi), faktlarni
   internetdan tekshiradi. Har bir slayd keyingisiga surishga majburlaydi. Uslub: fonda mavzuga oid
   **haqiqiy foto** (oq-qora), markazda oq matn, kalit qism kursivda. Bot slaydlarni 1080×1350
   rasmga aylantiradi va `posts/<sana>/` papkasiga saqlaydi.
3. **22:00** — Telegram bot'ga slaydlar va post matni keladi:
   - **✅ Tasdiqlash** — bot "Rostdan ham?" deb bir marta so'raydi, "Ha" bosilsa post chiqishga qo'yiladi;
   - **❌ Yoqmadi** — bot nimani o'zgartirish kerakligini so'raydi, Claude qayta yozadi. Tugmasiz
     to'g'ridan-to'g'ri izoh yozsangiz ham bo'ladi.
   - **Rasm yuborish** — postga qo'yish ("shuni slaydlar orasiga qo'y") yoki namuna sifatida
     ("shunga o'xshash dizaynda qil"). Albom ham bo'ladi.
4. Post Buffer orqali **soat 18:30** da o'zi chiqadi (`PUBLISH_AT`). Notion'da mavzu "Post" bo'ladi.
   Tasdiqlanmagan bo'lsa, bot **09:00** va **14:00** da eslatadi.
5. **/repair** — tasdiqlagandan keyin xato topsangiz, 18:30 gacha bot'ga `/repair` yuboring: post
   navbatdan olinadi, bot nimani tuzatishni so'raydi va yangi variantni yana tasdiqlaysiz.
6. 18:30 dan keyin bot postni tekshiradi: chiqqan bo'lsa linkini yuboradi, Instagram qabul qilmagan
   bo'lsa bir marta o'zi qayta yuboradi.
7. 21:30 gacha tasdiqlanmagan post chiqmaydi, mavzusi ertangi kunga o'tadi.

Qo'lda ishga tushirish (masalan, boshqa sanani tayyorlash): GitHub → **Actions** → **Daily Instagram
post** → **Run workflow** (`post_date` bilan).

### Musiqa haqida

Instagram avtomatik (API orqali) chiqqan carousel'ga musiqa qo'yishga ruxsat bermaydi: Buffer trekni
qabul qiladi, lekin Instagram uni tashlab yuboradi. Shuning uchun bot musiqa tanlashni so'ramaydi,
carousel musiqasiz chiqadi. Buffer musiqani avtomatik faqat Reels'ga qo'sha oladi.

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
bot/main.py          kunlik jarayon (holat: posts/<sana>/state.json)
bot/writer.py        Claude: post va slayd HTML'ini yozish, izoh/rasm bo'yicha qayta yozish
bot/design/base.css  dizayn uslubi (foto fon, kulrang tus, oq matn, pastki qism)
bot/render.py        HTML → JPEG (Chromium), matn sig'maganini tekshirish
bot/photos.py        fotolar: maqolalardagi asosiy rasm (og:image), zaxira — Openverse/Wikimedia
bot/notion.py        mavzuni olish, "Post" deb belgilash
bot/telegram.py      Telegram bot
bot/buffer.py        Buffer: jadval, post yaratish
posts/<sana>/vN/     har bir variantning slaydlari va matni
```

Slaydlar Buffer'ga `raw.githubusercontent.com/.../<commit-sha>/...` linki orqali beriladi. Repo
public bo'lgani uchun link login so'ramaydi, commit SHA bilan bo'lgani uchun esa hech qachon o'zgarmaydi.

