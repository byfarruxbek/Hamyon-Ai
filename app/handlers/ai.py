import logging
import re
from html import escape
from datetime import date
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select
from app.models import Transaction
from app.services.finance import get_or_create_user,monthly_totals,list_debts
from app.services.ai import AIUnavailable
router=Router();log=logging.getLogger(__name__)

REPORT_TERMS=("hisobot", "balans", "moliyaviy hisob", "shu oy", "oylik hisob", "kirim va xarajat", "daromad va xarajat")

def is_report_request(question:str)->bool:
    text=question.casefold()
    return any(term in text for term in REPORT_TERMS)

def telegram_safe_answer(answer:str)->str:
    """Escape model text for HTML mode and render common Markdown markers."""
    safe=escape((answer or "").strip())
    safe=re.sub(r"\*\*(.+?)\*\*",r"<b>\1</b>",safe,flags=re.S)
    safe=re.sub(r"__(.+?)__",r"<b>\1</b>",safe,flags=re.S)
    safe=re.sub(r"`([^`]+)`",r"<code>\1</code>",safe)
    safe=re.sub(r"(?m)^\s*[-*]\s+", "• ", safe)
    safe=re.sub(r"(?m)^#{1,3}\s*(.+)$",r"<b>\1</b>",safe)
    return safe

async def send_monthly_report(m:Message,session_factory,user_id=None):
    today=date.today();start=today.replace(day=1)
    async with session_factory() as db:
        user=await get_or_create_user(db,user_id or m.from_user.id)
        totals=await monthly_totals(db,user.id,today.year,today.month)
        rows=(await db.execute(select(Transaction.category,func.sum(Transaction.amount)).where(
            Transaction.user_id==user.id,Transaction.kind=="expense",Transaction.occurred_on.between(start,today)
        ).group_by(Transaction.category).order_by(func.sum(Transaction.amount).desc()).limit(8))).all()
        debts=await list_debts(db,user.id)
    month_name=("yanvar","fevral","mart","aprel","may","iyun","iyul","avgust","sentabr","oktyabr","noyabr","dekabr")[today.month-1]
    balance=totals["income"]-totals["expense"]
    category_lines="\n".join(f"• {escape(name)} — {int(amount):,} so‘m" for name,amount in rows) or "• Hozircha xarajat yo‘q"
    debt_total=sum(debt.remaining for debt in debts)
    text=(f"📊 <b>{today.year}-yil {month_name.capitalize()} hisoboti</b>\n\n"
          f"📥 Daromad: <b>{totals['income']:,} so‘m</b>\n"
          f"📤 Xarajat: <b>{totals['expense']:,} so‘m</b>\n"
          f"💰 Farq: <b>{balance:+,} so‘m</b>\n\n"
          f"<b>Xarajat kategoriyalari</b>\n{category_lines}\n\n"
          f"💳 Ochiq qarz qoldig‘i: <b>{debt_total:,} so‘m</b>\n\n"
          "Hisobot botga kiritilgan yozuvlarga asoslangan.")
    await m.answer(text)

async def answer_question(m:Message,question:str,session_factory,ai):
    if not question: await m.answer("Savolni yozing. Masalan: /savol Shu oy xarajatlarim qanday?");return
    if is_report_request(question):
        await send_monthly_report(m,session_factory)
        return
    async with session_factory() as db:
        u=await get_or_create_user(db,m.from_user.id);await db.commit();totals=await monthly_totals(db,u.id,date.today().year,date.today().month);debts=await list_debts(db,u.id)
        today=date.today();start=today.replace(day=1)
        cats=(await db.execute(select(Transaction.category,func.sum(Transaction.amount)).where(Transaction.user_id==u.id,Transaction.kind=="expense",Transaction.occurred_on.between(start,today)).group_by(Transaction.category))).all()
    context={"month":date.today().strftime("%Y-%m"),**totals,"open_debt_uzs":sum(d.remaining for d in debts),"expense_categories":[{"name":n,"amount":int(a)} for n,a in cats]}
    try:
        await m.bot.send_chat_action(m.chat.id,"typing")
        answer=await ai.ask(question,context)
    except AIUnavailable as e:
        log.info("AI answer unavailable uid=%s reason=%s",m.from_user.id,e);await m.answer("AI javobi olinmadi. AI_API_KEY, model nomi va internet ulanishini tekshiring. Oylik raqamlarni /hisobot orqali ko‘rishingiz mumkin.");return
    await m.answer(telegram_safe_answer(answer))

@router.message(Command("savol"))
async def ask(m:Message,session_factory,ai):
    await answer_question(m,m.text.partition(" ")[2].strip(),session_factory,ai)


@router.message(lambda m: m.text=="🤖 AI yordamchi")
async def ai_menu(m:Message): await m.answer("Savolingizni oddiy xabar qilib yuboring. Moliya yozuvlarini ham matnda kiritsangiz bo‘ladi.")
