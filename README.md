# Hamyon AI — PyCharm uchun

Telegram orqali shaxsiy xarajat, daromad, qarz/to‘lov va hisobotlarni yuritadigan modul bot. **Shaxsiy ma'lumotlar izolyatsiyasi** har bir so‘rovda Telegram foydalanuvchisi ID si bilan DB query filtrlash orqali ta'minlanadi. Haqiqiy tokenlar, qarzlar yoki seed yozuvlar loyihaga kiritilmagan.

## Muammo tahlili va yechimlar

Chat eksportida AI parse va `/savol` API xatolari, `/daromad`ning xarajat formatini ko‘rsatishi, `so'm` kategoriyaga yozilishi, `/pay`ning chalkashligi ko‘rindi. Bu relizda manual tranzaksiya AI dan mustaqil ishlaydi; AI xatosida tushunarli diagnostika/log bor; daromad va xarajat komandalarida alohida handler; valyuta so‘zi kategoriya sanitizatsiyasidan o‘tadi; `/pay` qarzni tugma orqali tanlaydi, to‘liq to‘lashni bir bosishda, qisman to‘lovni `/pay_sum ID SUMMA` bilan bajaradi.

## PyCharm/macOS ishga tushirish

1. ZIPni ochib PyCharm’da `hamyon-ai` papkasini **Open** qiling. Python 3.13 interpreter tanlang (3.15 hozircha pydantic-core build’ini qo‘llamaydi).
2. PyCharm Terminal: `python3 -m venv .venv` va `source .venv/bin/activate`
3. `python -m pip install -e '.[dev]'`
4. `.env.example` nusxasini `.env` deb o‘zgartiring; BotFather tokenini `TELEGRAM_BOT_TOKEN` ga kiriting. AI kerak bo‘lsa OpenRouter’da hisob ochib, bepul API key yarating va `AI_API_KEY` ga kiriting. `AI_BASE_URL` va `AI_MODEL` ni default qiymatda qoldiring (`https://openrouter.ai/api/v1`, `openrouter/free`). Oddiy matn/rasm AI ishlaydi; ovoz transkripsiyasi default o‘chirilgan, chunki u alohida STT modeliga va hisoblanadigan usage’ga bog‘liq bo‘lishi mumkin. Hech qachon kalitni chat yoki gitga yubormang. OpenAI kalitidan foydalanmoqchi bo‘lsangiz, `AI_API_KEY` ni bo‘sh qoldirib `OPENAI_API_KEY` ni to‘ldiring.
5. `python -m app`

Birinchi ishga tushishda SQLite `data/hamyon.db` avtomatik yaratiladi. PyCharm Run Configuration’da working directory loyiha ildizi bo‘lsin.

## Asosiy foydalanish

- `/xarajat 45000 ovqat tushlik` yoki `/daromad 5000000 oylik` — tasdiqlash tugmasidan keyin saqlanadi. `so‘m`, `UZS` yoki `sum` yolg‘iz qolsa `Boshqa` kategoriya bo‘ladi.
- Qarz haqida oddiy gap yozing (masalan, `TBC Osmon kartaga 9-noyabrda 2 mln so‘m to‘lashim kerak`) yoki `/qarz` dan keyin yozing. Bot nom, summa va sanani tahlil qilib, tasdiqlashdan keyin saqlaydi. Shuningdek: `/qarzlar`, `/pay`, `/pay_sum ID SUMMA`, `/qarz_ozgartir`, `/qarz_ochir`
- `/hisobot`, `/limit SUMMA`, `/oxirgi`, `/ochir ID`, `/ozgartir ID SUMMA KATEGORIYA IZOH`. Istalgan savolni oddiy xabar qilib yuboring; `/savol` ixtiyoriy.
- `/eslatma YYYY-MM-DD HH:MM MATN`, `/eslatmalar`, `/ochireslatma ID`
- Tugmalar asosiy menyu, qarz tanlash va tasdiqlashni ko‘rsatadi.

## BotFather profil materiallari

`assets/BOTFATHER_PROFILE_UZ.md` ichida BotFather uchun About, Description va `/setcommands` matnlari bor. `assets/hamyon-ai-logo.png` ni bot rasmi, `assets/hamyon-ai-description.png` ni profil tavsif rasmi sifatida yuklang. `assets/hamyon-ai-welcome.gif` `/start` bilan yuboriladigan qisqa animatsiya. Maxfiylik siyosati sahifasi `assets/privacy-policy-uz.html` ichida; BotFather’ga kiritishdan oldin uni HTTPS manzilga joylashtirib, bot egasining aloqa ma’lumotini to‘ldiring.

Ovozli xabarni matnga aylantirish uchun `.env` dagi `AI_TRANSCRIBE_MODEL` ga mavjud transkripsiya modelini kiriting. Bu qiymat bo‘sh bo‘lsa, bot ovozni matnga aylantirmaydi; matn va rasm tahlili alohida ishlaydi.

## Postgres / Docker

`.env` dagi `POSTGRES_PASSWORD` qiymatini o‘zgartiring, so‘ng `docker compose up --build -d`. Compose bot uchun Postgres ulanishini avtomatik sozlaydi. `docker-compose.yml` Postgres va botni ko‘taradi. SQLite lokal ishlab chiqish uchun; production’da Postgres tavsiya etiladi.

## Migratsiya

Versiyalangan migratsiyalar Alembic’da. Joriy kod ilk startda schema’ni yaratadi (yangi local install uchun qulay). Mavjud production DB’ni keyingi relizlarda o‘zgartirishda `alembic revision --autogenerate -m '...'`, so‘ng `alembic upgrade head` ishlating. Migratsiya konfiguratsiyasi uchun `DATABASE_URL` ni Alembicga ulash zarur.

## Test va sifat

`pytest -q` — valyuta kategoriyasi, income kind, qisman/full payment limit logic. `ruff check app tests` (ruff optional). OpenRouter’da bepul model 20 so‘rov/daqiqada va 50 so‘rov/kunda bilan cheklanishi mumkin; limit tugasa keyingi kunni kuting. So‘rov matni tanlangan model provayderiga uzatiladi, shuning uchun parol, karta raqami yoki o‘ta maxfiy moliyaviy ma’lumot yubormang.

## Hamyon Mini App, eslatma, media

Inline va reply keyboard interfeyslari botda mavjud. Telegram Mini App uchun domenli HTTPS hosting va WebApp backend autentifikatsiyasi kerak; shuning uchun offline ZIP ichida production Mini App yo‘q. Chek rasmini AI orqali parse qilish mavjud va tasdiqlashdan o‘tadi. Ovoz handleri bor, lekin bepul rejimda AI_TRANSCRIBE_MODEL belgilanmaguncha o‘chiq. Shaxsiy eslatmalar DB’da saqlanadi va sozlangan timezone bo‘yicha scheduler yuboradi. Xarajat limitidan oshgan yozuv tasdiqlansa, bot oshgan miqdorni ko‘rsatadi. Tranzaksiya va qarzlarni tahrirlash/o‘chirish user scope bilan bajariladi. Scheduler bir bot worker bilan ishlaydi. AI yozuvni hech qachon avtomatik saqlamaydi; foydalanuvchi tasdiqlashi shart. Oddiy savollar AI ga bevosita yuboriladi; `/savol` majburiy emas.

## Xavfsizlik va chegaralar

- API xatolarida kalit chiqarilmaydi; server logida exception turi ko‘rsatiladi. Rate limit user ID bo‘yicha (bitta jarayon xotirasida).
- DB querylar user scope bilan cheklangan. To‘lov miqdori qoldiqdan oshmaydi.
- Bot bankdagi hisoblarni ko‘rmaydi; hisobot faqat foydalanuvchi kiritgan ma'lumot.
- Telegram polling uchun bir bot tokeni bilan faqat bitta jarayon ishlating.
