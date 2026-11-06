# Hamyon AI

Hamyon AI — Telegram bot orqali shaxsiy daromad, xarajat, qarz va eslatmalarni yuritish vositasi. Bot yozuvni avtomatik saqlamaydi: AI tahlil qilgan ma’lumot avval ko‘rsatiladi, foydalanuvchi tekshirib tasdiqlagandan keyingina bazaga yoziladi.

Har bir yozuv Telegram foydalanuvchisining ichki ID’siga bog‘langan. Bot bank hisobiga ulanmaydi va bankdagi haqiqiy balansni ko‘ra olmaydi; hisobotlar faqat botga kiritilgan yozuvlar asosida tuziladi.

## O‘rnatish va ishga tushirish

Python 3.11–3.14 kerak; Python 3.13 tavsiya etiladi. macOS’da loyiha papkasini PyCharm’da ochib, terminalda quyidagilarni bajaring:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
```

`.env` faylida `TELEGRAM_BOT_TOKEN` o‘rniga BotFather tokenini kiriting. Botni ishga tushirish:

```bash
python -m app
```

PyCharm Run Configuration ishlatilsa, **Working directory** loyiha ildizi bo‘lsin. Birinchi ishga tushishda SQLite bazasi `data/hamyon.db` faylida yaratiladi. `.env` faylini hech qachon GitHub’ga yuklamang; u `.gitignore` ichida chiqarib tashlangan.

## AI sozlamalari

Matnli AI tahlili va chek rasmini o‘qish uchun `.env` da `AI_API_KEY` va ishlatiladigan modelni sozlang. Standart provayder OpenRouter:

```env
AI_BASE_URL=https://openrouter.ai/api/v1
AI_MODEL=openrouter/free
```

Tanlangan model rasm qabul qilishini provayderdan tekshiring. Ovozli xabarni matnga aylantirish uchun `AI_TRANSCRIBE_MODEL` ga provayder qo‘llaydigan transkripsiya modelini kiriting. Bu maydon bo‘sh bo‘lsa, ovozli xabar tahlil qilinmaydi. Rasm va audio modellari uchun kvota yoki alohida to‘lov talab qilinishi mumkin. AI ishlamasa, bot xatoni bildiradi; summani `/xarajat` yoki `/daromad` orqali qo‘lda kiritish mumkin.

OpenAI sozlamasidan foydalanilsa, `AI_API_KEY` ni bo‘sh qoldirib `OPENAI_API_KEY` ni to‘ldiring. Token va API kalitlarini chat, README yoki git repozitoriyga yozmang.

## Daromad va xarajat

Yozuvni menyudagi **➕ Xarajat** yoki **➕ Daromad** tugmasidan, buyruqdan yoki oddiy xabardan boshlash mumkin:

```text
Benzinga 200 ming ketdi
Bugun 500 ming ishlab topdim
Tushlikka 45 ming to‘ladim
```

Buyruqlar:

- `/xarajat 45000 ovqat tushlik` — xarajat kiritish.
- `/daromad 5000000 oylik` — daromad kiritish.
- `/oxirgi` — oxirgi yozuvlarni ko‘rish.
- `/ozgartir ID SUMMA KATEGORIYA IZOH` — yozuvni tahrirlash; yozuv turi saqlanib qoladi.
- `/ochir ID` — yozuvni o‘chirish.
- `/limit 1500000` — oylik xarajat limitini belgilash; `/limit 0` limitni o‘chiradi.

Har bir yangi yozuvdan oldin bot summa, turi, kategoriya, izoh va sanani ko‘rsatadi. Tasdiqlash oynasida summani, kategoriyani yoki izohni o‘zgartirish, yoxud bekor qilish mumkin. AI tahlili muvaffaqiyatsiz yoki noaniq bo‘lsa, yozuv avtomatik saqlanmaydi. Buyruq bilan raqamdan boshlangan sodda yozuvlar AI xizmatisiz ham tahlil qilinishi mumkin; erkin matn, rasm va ovoz uchun sozlangan AI kerak.

## Hisobot

- `/hisobot` — joriy oy daromadi, xarajati, farqi va limit holati.
- `/hisobot kun` — bugungi hisob.
- `/hisobot hafta` — dushanbadan bugungacha bo‘lgan hisob.
- `/hisobot kategoriya` — shu oy xarajatlarini kategoriya bo‘yicha.

Hisobotni menyudagi **📊 Hisobot** tugmasidan ham ochish mumkin. Oddiy xabarda hisobot yoki balans haqida so‘ralsa, bot AI’dan raqamlarni taxmin qildirmaydi; ma’lumotni bazadan hisoblab chiqaradi. Ko‘rsatilgan farq bank balansi emas.

## Qarzlar va to‘lovlar

Qarz haqida oddiy gap yozing, masalan:

```text
TBC Osmon kartaga 9-noyabrda 2 mln so‘m to‘lashim kerak
```

Bot topilgan nom, summa va sanani ko‘rsatadi. Qarz faqat tasdiqdan keyin saqlanadi.

- `/qarzlar` — ochiq qarzlarni ko‘rish.
- `/pay` — qarzni tanlash va to‘lovni belgilash.
- `/pay_sum ID SUMMA` — qisman to‘lov kiritish, masalan `/pay_sum 2 100000`.
- `/qarz_ozgartir ID YYYY-MM-DD SUMMA NOMI` — qarzni tahrirlash.
- `/qarz_ochir ID` — qarz va uning to‘lov tarixini o‘chirish.

To‘lov summasi qarz qoldig‘idan oshirilmaydi. Qarz to‘lovi daromad/xarajat hisobotiga alohida tranzaksiya sifatida qo‘shilmaydi; hisobotda ochiq qarz qoldig‘i ko‘rsatiladi.

## Eslatmalar va yordamchi xabarlar

Shaxsiy eslatmalar:

- `/eslatma YYYY-MM-DD HH:MM MATN` — eslatma qo‘shish.
- `/eslatmalar` — eslatmalar ro‘yxati.
- `/ochireslatma ID` — eslatmani o‘chirish.

Bot, shuningdek, oxirgi faollikdan uch kun o‘tgach eslatma yuborishi mumkin; takroriy faollik eslatmasi haftasiga ko‘pi bilan bir marta yuboriladi. To‘lov muddati yaqin qarzlar va limitning 80 foiziga yetgan xarajatlar haqida kunlik ogohlantirish beriladi. Xabarlar `TIMEZONE` bo‘yicha `ENGAGEMENT_NUDGE_HOUR` vaqtidan keyin tekshiriladi (standart — 19:00, `Asia/Tashkent`). Eski bazalarda dastlabki faollik oxirgi saqlangan daromad/xarajat, qarz yoki akkaunt yaratilgan vaqtdan taxmin qilinadi.

`/savol MATN` yoki oddiy xabar bilan AI yordamchisidan so‘rash mumkin. AI’ga savol bilan birga faqat shu foydalanuvchining joriy oy jami, kategoriya yig‘indisi va ochiq qarz qoldig‘i beriladi. So‘rovlar sozlangan AI provayderiga uzatiladi; maxfiy ma’lumotlarni yubormang. `/start` menyu va boshlang‘ich xabarni ko‘rsatadi, `/help` buyruqlarni chiqaradi.

## Docker va PostgreSQL

`.env` ichida `POSTGRES_PASSWORD` ni o‘zgartirib, loyiha ildizida ishga tushiring:

```bash
docker compose up --build -d
```

Compose PostgreSQL va bot konteynerlarini ishga tushiradi; SQLite lokal ishlab chiqish uchun mo‘ljallangan. SQLite bazasi `data/hamyon.db` da saqlanadi. PostgreSQL ma’lumotlari Docker volume’da saqlanadi. Zaxira nusxalarda moliyaviy ma’lumotlar bo‘ladi — ularni maxfiy saqlang.

## Migratsiya va ishga tushirish tartibi

Bot start vaqtida mavjud bo‘lmagan jadvallarni yaratadi. Alembic migratsiyalari `migrations/versions/` ichida saqlanadi; `alembic.ini` hozir lokal SQLite manziliga yo‘naltirilgan va `.env` dagi `DATABASE_URL` ni avtomatik olmaydi. PostgreSQL bazasiga migratsiya qo‘llashdan oldin Alembic ulanish manzilini moslang. Scheduler eslatma va yordamchi bildirishnomalarni yuboradi, shuning uchun bir xil bot tokeni bilan faqat **bitta** bot jarayonini ishga tushiring.

## Tekshiruv

Virtual muhit yoqilgan holda:

```bash
python -m pytest -q
python -m compileall -q app migrations tests
```

## Chegaralar va xavfsizlik

- Bot bank hisoblarini ko‘rmaydi, pul o‘tkazmaydi va bank bilan avtomatik sinxronlanmaydi.
- Hisobotlar faqat foydalanuvchi kiritgan ma’lumotlarga asoslanadi.
- Ma’lumotlar bazasi so‘rovlari foydalanuvchi ID’si bilan chegaralanadi.
- Karta raqami, PIN, CVV, parol yoki API kalitini botga yubormang.
- Telegram yoki AI xizmati tarmog‘i ishlamasa, bot ma’lumotni avtomatik saqlamaydi; xizmat tiklangach qayta urinib ko‘ring yoki tranzaksiyani qo‘lda kiriting.
