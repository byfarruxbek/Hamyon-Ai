import re
from aiogram import Router
from aiogram.types import Message
from app.domain import AMOUNT_PATTERN, infer_transaction_kind
from app.handlers.transactions import stage
from app.handlers.debts import stage_debt
from app.handlers.ai import answer_question

router = Router()


def looks_like_financial_entry(text: str) -> bool:
    if not AMOUNT_PATTERN.search(text):
        return False
    clues=("so‘m", "so'm", "som", "uzs", "ming", "million", "pul", "non", "mastava", "ovqat", "tushlik", "daromad", "xarajat", "ishlab", "topdim", "yedim", "ichdim", "sotib", "oldim", "sotdim", "video", "maosh", "oylik", "qarz")
    lowered=text.casefold()
    return any(clue in lowered for clue in clues)


def looks_like_debt(text: str) -> bool:
    lowered=text.casefold()
    cues=("qarz", "kredit", "kartaga", "to‘lashim", "to'lashim", "tolashim", "solishim", "to‘lash kerak", "tolash kerak")
    return bool(AMOUNT_PATTERN.search(text) and any(cue in lowered for cue in cues))


@router.message()
async def unknown_message(message: Message, ai, session_factory):
    text=message.text or ""
    if not text:
        await message.answer("Xabarni matn ko‘rinishida yuboring yoki /start orqali menyuni oching.")
        return
    if not text.startswith("/") and looks_like_debt(text):
        await stage_debt(message,text,session_factory,ai)
        return
    kind=infer_transaction_kind(text)
    if not text.startswith("/") and looks_like_financial_entry(text) and kind:
        await stage(message,kind,text,ai)
        return
    if not text.startswith("/") and looks_like_financial_entry(text):
        await stage(message,None,text,ai)
        return
    if not text.startswith("/"):
        await answer_question(message,text,session_factory,ai)
        return
    await message.answer("Buyruqni topolmadim. Menyuni ko‘rish uchun /start ni bosing yoki savolingizni oddiy xabar qilib yozing.")
