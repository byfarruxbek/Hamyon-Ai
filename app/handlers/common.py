import logging
from pathlib import Path
from aiogram import Router,F
from aiogram.filters import CommandStart,Command
from aiogram.types import Message,CallbackQuery,FSInputFile
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.services.finance import get_or_create_user
from app.keyboards import main_menu
log=logging.getLogger(__name__);router=Router()
WELCOME_ANIMATION=Path(__file__).resolve().parents[2]/"assets"/"hamyon-ai-welcome.gif"

@router.message(CommandStart())
async def start(m:Message,session_factory:async_sessionmaker):
    async with session_factory() as db:
        user=await get_or_create_user(db,m.from_user.id);await db.commit()
    welcome="💼 <b>Hamyon AI</b>ga xush kelibsiz!\n\nXarajat yoki daromadni oddiy matn, ovozli xabar yoki chek rasmi orqali yuboring. Bot tahlil qiladi va siz tekshirib tasdiqlaganingizdan keyin saqlaydi.\n\nMisol: <code>Benzinga 200 ming ketdi</code>\n/savol — AI’dan so‘rash · /help — yordam"
    if WELCOME_ANIMATION.is_file():
        await m.answer_animation(FSInputFile(WELCOME_ANIMATION),caption=welcome,reply_markup=main_menu())
    else:
        await m.answer(welcome,reply_markup=main_menu())

@router.message(Command("id"))
async def get_id(m:Message): await m.answer(f"Telegram ID: <code>{m.from_user.id}</code>")

@router.message(Command("help"))
async def help_cmd(m:Message):
    await m.answer("""<b>Buyruqlar</b>
/xarajat 45000 ovqat tushlik — chiqim
/daromad 5000000 oylik — kirim
/qarz YYYY-MM-DD SUMMA NOMI — qarz qo‘shish
/pay — qarzni tugma bilan tanlash va to‘lash
/qarz_ozgartir ID YYYY-MM-DD SUMMA NOMI
/qarz_ochir ID — qarz va tarixini o‘chirish
/ozgartir ID SUMMA KATEGORIYA IZOH
/qarzlar — ochiq qarzlar
/hisobot — shu oy
/savol matn — AI tahlili
/limit SUMMA — oylik xarajat chegarasi
/eslatma YYYY-MM-DD HH:MM MATN — eslatma qo‘shish
/eslatmalar, /ochireslatma ID
/oxirgi va /ochir ID — tranzaksiya ko‘rish/o‘chirish

So‘m/UZS valyuta so‘zi kategoriya hisoblanmaydi. Shaxsiy bank ma’lumotlarini yubormang.""")

@router.message(F.text=="⚙️ Sozlamalar")
async def settings(m:Message): await m.answer("Limitni /limit 1500000 buyrug‘i bilan belgilang. Eslatma va timezone sozlamalari keyingi reliz uchun ochiq interfeysda.")
