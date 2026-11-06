import asyncio
import logging
from datetime import date, datetime, timedelta
from html import escape
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import func, select

from app.models import Debt, Transaction, User, UserActivity

log = logging.getLogger(__name__)
INACTIVITY_AFTER = timedelta(days=3)
INACTIVITY_REPEAT = timedelta(days=7)
BUDGET_WARNING_PERCENT = 80
SUPPORT_USERNAME = "Farruxbekaloqabot"


def inactivity_nudge_due(last_seen_at: datetime, last_nudge_at: datetime | None, now: datetime) -> bool:
    if now - last_seen_at < INACTIVITY_AFTER:
        return False
    return last_nudge_at is None or now - last_nudge_at >= INACTIVITY_REPEAT


def nudge_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Hisobot", callback_data="eng:report"),
         InlineKeyboardButton(text="💳 Qarzlar", callback_data="eng:debts")],
        [InlineKeyboardButton(text="💬 Taklif yoki yordam", url=f"https://t.me/{SUPPORT_USERNAME}")],
    ])


async def send_engagement_nudges(bot: Bot, session_factory, timezone: str, nudge_hour: int) -> None:
    local_now = datetime.now(ZoneInfo(timezone))
    if local_now.hour < nudge_hour:
        return
    now_utc = datetime.utcnow()
    today = local_now.date()
    month_start = today.replace(day=1)
    due_until = today + timedelta(days=3)

    async with session_factory() as db:
        # Older installs did not record message activity. Seed those users from
        # the newest saved finance action so the feature also covers existing accounts.
        existing_users = (await db.scalars(select(User))).all()
        for user in existing_users:
            if await db.get(UserActivity, user.id) is not None:
                continue
            recent_transaction = await db.scalar(
                select(Transaction.created_at).where(Transaction.user_id == user.id)
                .order_by(Transaction.created_at.desc()).limit(1)
            )
            recent_debt = await db.scalar(
                select(Debt.created_at).where(Debt.user_id == user.id)
                .order_by(Debt.created_at.desc()).limit(1)
            )
            candidates = [stamp for stamp in (user.created_at, recent_transaction, recent_debt) if stamp]
            db.add(UserActivity(user_id=user.id, last_seen_at=max(candidates)))
        await db.flush()
        users = (await db.execute(
            select(UserActivity, User.telegram_id, User.monthly_limit)
            .join(User, User.id == UserActivity.user_id)
        )).all()

        for activity, telegram_id, monthly_limit in users:
            sections = []
            name = (activity.first_name or "").strip()
            greeting = f"{escape(name)}, " if name else ""

            inactivity_due = inactivity_nudge_due(
                activity.last_seen_at, activity.last_inactivity_nudge_at, now_utc
            )
            if inactivity_due:
                sections.append(
                    f"{greeting}so‘nggi 3 kundan beri Hamyon AI’dan foydalanmadingiz. "
                    "Xarajat yoki daromadni yozib, hisobingizni yangilab qo‘yishingiz mumkin."
                )

            due_rows = []
            if activity.last_due_nudge_on != today:
                due_rows = (await db.scalars(
                    select(Debt).where(
                        Debt.user_id == activity.user_id,
                        Debt.remaining > 0,
                        Debt.due_date.is_not(None),
                        Debt.due_date >= today,
                        Debt.due_date <= due_until,
                    ).order_by(Debt.due_date).limit(5)
                )).all()
                if due_rows:
                    due_text = "\n".join(
                        f"• {escape(debt.title)} — {debt.remaining:,} so‘m, {debt.due_date:%d-%m}"
                        for debt in due_rows
                    )
                    sections.append(f"📅 Yaqin 3 kunda to‘lov muddati keladigan qarzlar:\n{due_text}")

            budget_due = False
            if monthly_limit and activity.last_budget_nudge_on != today:
                spent = int(await db.scalar(
                    select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                        Transaction.user_id == activity.user_id,
                        Transaction.kind == "expense",
                        Transaction.occurred_on >= month_start,
                        Transaction.occurred_on <= today,
                    )
                ) or 0)
                if spent >= monthly_limit * BUDGET_WARNING_PERCENT / 100:
                    budget_due = True
                    percent = round(spent * 100 / monthly_limit)
                    sections.append(
                        f"🎯 Bu oy xarajatlari limitning {percent}%iga yetdi "
                        f"({spent:,} / {monthly_limit:,} so‘m)."
                    )

            if not sections:
                continue
            text = "🔔 <b>Hamyon AI eslatmasi</b>\n\n" + "\n\n".join(sections)
            text += "\n\nHisobot yoki qarzlaringizni tugmalar orqali ko‘ring."
            try:
                await bot.send_message(telegram_id, text, reply_markup=nudge_keyboard())
            except Exception as exc:
                log.warning("Engagement message failed uid=%s error=%s", telegram_id, type(exc).__name__)
                continue
            if inactivity_due:
                activity.last_inactivity_nudge_at = now_utc
            if due_rows:
                activity.last_due_nudge_on = today
            if budget_due:
                activity.last_budget_nudge_on = today
            await db.commit()


async def engagement_loop(bot: Bot, session_factory, timezone="Asia/Tashkent", nudge_hour=19):
    while True:
        try:
            await send_engagement_nudges(bot, session_factory, timezone, nudge_hour)
        except Exception as exc:
            log.warning("Engagement scheduler failed error=%s", type(exc).__name__)
        await asyncio.sleep(3600)
