# Instagram-avto

Instagram'ga Claude + Buffer orqali avtomatik post chiqarish uchun **media hosting**.

Repo **public** bo'lgani uchun bu yerga yuklangan har bir rasm/video login so'ramaydigan
ochiq HTTPS link orqali ochiladi — Buffer aynan shunday URL talab qiladi.

## Jarayon

```
Claude → rasm/video yaratadi → shu repoga push qiladi → raw URL oladi → Buffer'ga beradi → Instagram
```

## Tuzilma

```
media/YYYY-MM-DD/   # har kunning rasmlari (carousel bo'lsa 1.png, 2.png, ...)
scripts/            # rasm yaratish skriptlari
```

## URL formati

Faylni to'g'ridan-to'g'ri ochadigan link (`github.com/.../blob/...` emas!):

```
https://raw.githubusercontent.com/abdulazizcoder0901/Instagram-avto/<commit-sha>/media/<sana>/<fayl>.png
```

Branch nomi o'rniga **commit SHA** ishlatiladi — shunda link hech qachon o'zgarmaydi va
post Instagram'da chiqquncha ishlaydi.

Tekshirish: linkni brauzerning Incognito oynasida oching — rasm login so'ramasdan ochilsa,
Buffer ham uni ola oladi.

## Instagram talablari

- Format: JPG yoki PNG (video: MP4)
- O'lcham: 1080×1350 (4:5) yoki 1080×1080 (1:1)
- Fayl hajmi: rasm 8 MB gacha
- GitHub'da bitta fayl 100 MB dan oshmasligi kerak

## Rasm yaratish

```bash
python3 scripts/make_post_image.py media/2026-10-17/1.png "Sarlavha" "Qisqa matn"
```
