import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import select
from app.models import Reminder, User
log=logging.getLogger(__name__)

async def reminder_loop(bot,session_factory,timezone="Asia/Tashkent"):
    """Deliver due reminders. Run exactly one bot worker to avoid duplicate sends."""
    while True:
        try:
            async with session_factory() as db:
                now=datetime.now(ZoneInfo(timezone)).replace(tzinfo=None)
                due=(await db.execute(select(Reminder,User.telegram_id).join(User,Reminder.user_id==User.id).where(Reminder.completed.is_(False),Reminder.remind_at<=now).limit(100))).all()
                for reminder,telegram_id in due:
                    try:
                        await bot.send_message(telegram_id,"🔔 Eslatma\\n"+reminder.message)
                        reminder.completed=True
                    except Exception as exc:
                        # Mark as completed to avoid endless retries to blocked chats; diagnostic excludes secrets.
                        log.warning("Reminder delivery failed id=%s error=%s",reminder.id,type(exc).__name__)
                        reminder.completed=True
                if due: await db.commit()
        except Exception as exc:
            log.exception("Reminder scheduler iteration failed: %s",type(exc).__name__)
        await asyncio.sleep(30)
