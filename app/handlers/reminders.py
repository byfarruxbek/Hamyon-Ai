from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from app.models import Reminder
from app.services.finance import get_or_create_user
router=Router()

@router.message(Command("eslatma"))
async def create_reminder(m:Message,session_factory,timezone="Asia/Tashkent"):
    try:
        _,day,hour,*words=m.text.split()
        when=datetime.strptime(f"{day} {hour}","%Y-%m-%d %H:%M")
        message=" ".join(words).strip()
        if not message: raise ValueError()
    except Exception:
        await m.answer("Format: /eslatma YYYY-MM-DD HH:MM eslatma matni\nMisol: /eslatma 2026-12-01 09:00 Kommunal to‘lov");return
    if when<=datetime.now(ZoneInfo(timezone)).replace(tzinfo=None): await m.answer("Eslatma vaqti kelajakda bo‘lishi kerak.");return
    async with session_factory() as db:
        user=await get_or_create_user(db,m.from_user.id)
        row=Reminder(user_id=user.id,message=message[:300],remind_at=when)
        db.add(row);await db.commit();await db.refresh(row)
    await m.answer(f"🔔 Eslatma #{row.id} qo‘shildi: {when:%Y-%m-%d %H:%M} · {escape(message)}")

@router.message(Command("eslatmalar"))
async def list_reminders(m:Message,session_factory):
    async with session_factory() as db:
        user=await get_or_create_user(db,m.from_user.id)
        rows=(await db.scalars(select(Reminder).where(Reminder.user_id==user.id,Reminder.completed.is_(False)).order_by(Reminder.remind_at).limit(20))).all()
    await m.answer("🔔 Eslatmalar:\n"+("\n".join(f"#{r.id} {r.remind_at:%Y-%m-%d %H:%M} · {escape(r.message)}" for r in rows) if rows else "Faol eslatma yo‘q"))

@router.message(Command("ochireslatma"))
async def delete_reminder(m:Message,session_factory):
    try: rid=int(m.text.split(maxsplit=1)[1])
    except Exception: await m.answer("Format: /ochireslatma ID");return
    async with session_factory() as db:
        user=await get_or_create_user(db,m.from_user.id)
        row=await db.scalar(select(Reminder).where(Reminder.id==rid,Reminder.user_id==user.id))
        if row: await db.delete(row);await db.commit()
    await m.answer("Eslatma o‘chirildi." if row else "Eslatma topilmadi.")
