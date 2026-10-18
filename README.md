# Instagram-avto

Har kuni @mr_abdulazz uchun carousel post: **Notion → Claude → slaydlar → Telegram'da tasdiqlash → Buffer → Instagram**.

## Har kuni nima bo'ladi

1. **21:35** — GitHub Actions ishga tushadi va Notion'dan **ertangi** mavzuni oladi: sanasi ertaga yoki
   undan oldin bo'lgan, hali "Post" bo'lmagan eng birinchi mavzu. Bir kunga 2 ta mavzu tushsa yoki bir
   kun o'tib ketsa, mavzu yo'qolmaydi: keyingi kuni chiqadi.
2. Claude Notion'dagi ssenariy asosida carousel yozadi (hook, amaliy misollar, faktlarni internetdan
   tekshiradi). Uslub: fonda mavzuga oid **haqiqiy foto** (oq-qora), markazda oq matn, kalit qism
   kursivda. Fotolar Claude topgan maqolalarning asosiy rasmidan olinadi (film kadri, joy, odam);
   topilmasa — bepul fotobazadan (Openverse/Wikimedia). Bot slaydlarni Chromium'da 1080×1350
   rasmga aylantiradi va `posts/<sana>/` papkasiga saqlaydi.
3. **22:00** — Telegram bot'ga slaydlar va post matni keladi, ostida 2 ta tugma bo'ladi:
   - **✅ Tasdiqlash** — bot "Rostdan ham?" deb bir marta so'raydi, "Ha" bosilsa post chiqishga qo'yiladi;
   - **❌ Yoqmadi** — bot nimani o'zgartirish kerakligini so'raydi. Siz yozasiz, Claude postni qayta
     yozadi va yangi variantni yuboradi. Tugmani bosmasdan to'g'ridan-to'g'ri izoh yozsangiz ham bo'ladi.
   - **Rasm yuborish** — foto/skrinshotni postga qo'ydirish ("shuni slaydlar orasiga qo'y") yoki
     boshqa postni namuna qilib berish ("shunga o'xshash dizaynda qil"). Albom ham bo'ladi.
4. Post Buffer'ga **avtomatik** chiqishga qo'yiladi va ertasi kuni Buffer'dagi vaqtda o'zi chiqadi.
   Qo'lda hech narsa qilish shart emas. Notion'da mavzu "Post" bo'ladi.
5. **/repair** — tasdiqlagandan keyin xato topsangiz, post chiqishidan oldin bot'ga `/repair` yuboring.
   Post navbatdan olinadi, bot nimani tuzatishni so'raydi, yangi variantni yuboradi — uni yana tasdiqlaysiz.
   Post chiqib bo'lgach /repair ishlamaydi.

Kechasi javob bermasangiz, **08:00** da bot postni qayta yuboradi (13:30 gacha kutadi). Undan keyin
davom ettirish uchun: GitHub → **Actions** → **Daily Instagram post** → **Run workflow**. Bot to'xtagan
joyidan davom etadi. Bot har kuni ~03:05–08:00 orasida ishlamaydi: shu vaqtda yuborilgan xabarlarni
08:00 da o'qiydi.

### Musiqa haqida

Instagram avtomatik (API orqali) chiqqan carousel'ga musiqa qo'yishga ruxsat bermaydi: Buffer trekni
qabul qiladi, lekin Instagram uni tashlab yuboradi. Shuning uchun bot musiqa tanlashni so'ramaydi,
carousel musiqasiz chiqadi.

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

