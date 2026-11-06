from html import escape

from aiogram import Router
from aiogram.types import CallbackQuery
from sqlalchemy import select

from app.handlers.ai import send_monthly_report
from app.models import Debt
from app.services.finance import get_or_create_user

router = Router()


@router.callback_query(lambda c: c.data == "eng:report")
async def engagement_report(c: CallbackQuery, session_factory):
    await send_monthly_report(c.message, session_factory, user_id=c.from_user.id)
    await c.answer()


@router.callback_query(lambda c: c.data == "eng:debts")
async def engagement_debts(c: CallbackQuery, session_factory):
    async with session_factory() as db:
        user = await get_or_create_user(db, c.from_user.id)
        debts = (await db.scalars(
            select(Debt).where(Debt.user_id == user.id, Debt.remaining > 0)
            .order_by(Debt.due_date).limit(20)
        )).all()
    if debts:
        body = "💳 <b>Ochiq qarzlar</b>\n" + "\n".join(
            f"• {escape(debt.title)} — {debt.remaining:,} so‘m" +
            (f" · {debt.due_date:%d-%m-%Y}" if debt.due_date else "")
            for debt in debts
        )
    else:
        body = "💳 Ochiq qarzingiz yo‘q."
    await c.message.answer(body)
    await c.answer()
