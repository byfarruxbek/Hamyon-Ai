import re
import secrets
import logging
from datetime import date
from html import escape
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message,CallbackQuery
from sqlalchemy import select
from app.models import Debt,DebtPayment
from app.domain import AMOUNT_PATTERN,CURRENCY_WORDS
from app.services.finance import get_or_create_user,list_debts,pay_debt
from app.keyboards import debt_keyboard,payment_keyboard,debt_confirmation_keyboard
from app.services.ai import AIUnavailable
router=Router()
log=logging.getLogger(__name__)
PENDING_DEBTS={}
MONTHS={"yanvar":1,"fevral":2,"mart":3,"aprel":4,"may":5,"iyun":6,"iyul":7,"avgust":8,"sentabr":9,"sentyabr":9,"oktyabr":10,"noyabr":11,"dekabr":12}



def parse_debt_locally(text: str):
    source=re.sub(r"^/qarz(?:@\w+)?\s*", "", text.strip(), flags=re.I)
    today=date.today()
    due=None;date_span=None
    iso=re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b",source)
    if iso:
        due=date(int(iso.group(1)),int(iso.group(2)),int(iso.group(3)));date_span=iso.span()
    else:
        months="|".join(MONTHS)
        natural=re.search(rf"(?:(?P<year>20\d{{2}})(?:-yil)?\s*)?(?P<day>\d{{1,2}})[ -](?P<month>{months})(?P<suffix>da|dan|gacha)?\b",source,re.I)
        if natural:
            year=int(natural.group("year") or today.year);month=MONTHS[natural.group("month").casefold()]
            day=int(natural.group("day"));due=date(year,month,day)
            if not natural.group("year") and due<today: due=date(year+1,month,day)
            date_span=natural.span()
    matches=list(AMOUNT_PATTERN.finditer(source))
    amount_match=None
    for candidate in matches:
        after=source[candidate.end():candidate.end()+12]
        if candidate.group("unit") or CURRENCY_WORDS.match(after.strip()):
            amount_match=candidate
    if amount_match is None and matches: amount_match=matches[-1]
    if amount_match is None: raise ValueError("Qarz summasi topilmadi")
    value=int(re.sub(r"[\s.,]", "", amount_match.group("number")))
    unit=(amount_match.group("unit") or "").casefold()
    if unit.startswith("ming"): value*=1000
    elif unit.startswith("million") or unit.startswith("mln"): value*=1_000_000
    if value<=0 or value>10**12: raise ValueError("Qarz summasi noto‘g‘ri")
    spans=[amount_match.span()]
    if date_span: spans.append(date_span)
    title=source
    for start,end in sorted(spans,reverse=True): title=title[:start]+" "+title[end:]
    title=CURRENCY_WORDS.sub("",title)
    title=re.sub(r"\b(?:ming|million|mln|kerak|solishim|solish|to‘lashim|to'lashim|to‘lash|to'lash|to‘lay|tolay)\b", " ",title,flags=re.I)
    title=re.sub(r"(?<=\w)(?:siga|ga|ka|da|dan|ni|ning)\b", "",title,flags=re.I)
    title=re.sub(r"\s+"," ",title).strip(" .,-:")
    title=re.sub(r"^(?:men|qarz|kredit)\s+", "",title,flags=re.I).strip()
    if not title: title="Qarz to‘lovi"
    return {"title":title[:120],"amount":value,"due_date":due}


async def stage_debt(message:Message,text:str,session_factory,ai):
    try:
        parsed=parse_debt_locally(text)
    except Exception as exc:
        log.info("Local debt parse did not finish uid=%s reason=%s",message.from_user.id,type(exc).__name__)
        parsed=None
    try:
        ai_data=await ai.parse_debt(text,date.today())
        if ai_data.get("amount"): parsed_amount=int(ai_data["amount"])
        else: parsed_amount=None
        ai_title=str(ai_data.get("title") or "").strip()
        ai_date=date.fromisoformat(ai_data["due_date"]) if ai_data.get("due_date") else None
        if parsed is None:
            parsed={"title":ai_title,"amount":parsed_amount,"due_date":ai_date}
        else:
            if ai_title and len(ai_title)<120 and not any(x in ai_title.casefold() for x in ("kerak","solishim","to‘lashim","to'lashim")):
                parsed["title"]=ai_title
            if parsed_amount: parsed["amount"]=parsed_amount
            if ai_date: parsed["due_date"]=ai_date
    except AIUnavailable as exc:
        log.info("AI debt parse unavailable uid=%s reason=%s",message.from_user.id,exc)
    except Exception as exc:
        log.warning("Debt parse response invalid uid=%s reason=%s",message.from_user.id,type(exc).__name__)
    if not parsed or not parsed.get("amount"):
        await message.answer("Qarzni tushunmadim. Masalan: <code>TBC Osmon kartaga 9-noyabrda 2 mln so‘m to‘lashim kerak</code>. Qarz summasi va muddati aniqlanmasa, /qarz YYYY-MM-DD SUMMA NOMI formatidan foydalaning.")
        return
    token=secrets.token_urlsafe(9);PENDING_DEBTS[token]=(message.from_user.id,parsed)
    due=parsed.get("due_date")
    due_text=due.isoformat() if due else "Muddati ko‘rsatilmagan"
    await message.answer(f"💳 <b>Qarz ma’lumotini tekshiring</b>\nNomi: {escape(parsed['title'])}\nSumma: {int(parsed['amount']):,} so‘m\nTo‘lov sanasi: {due_text}\n\nFaqat tasdiqlaganingizdan keyin saqlanadi.",reply_markup=debt_confirmation_keyboard(token))


@router.message(Command("qarz"))
async def add_debt(m:Message,session_factory,ai):
    text=m.text.partition(" ")[2].strip()
    if not text:
        await m.answer("Qarz haqida oddiy gap bilan yozing. Masalan: <code>TBC Osmon kartaga 9-noyabrda 2 mln so‘m solishim kerak</code>")
        return
    await stage_debt(m,text,session_factory,ai)


@router.callback_query(lambda c:c.data and c.data.startswith("debtconfirm:"))
async def confirm_debt(c:CallbackQuery,session_factory):
    token=c.data.split(":",1)[1];item=PENDING_DEBTS.pop(token,None)
    if not item or item[0]!=c.from_user.id:
        await c.answer("Bu tasdiqlash sizga tegishli emas yoki muddati tugagan.",show_alert=True);return
    data=item[1]
    async with session_factory() as db:
        user=await get_or_create_user(db,c.from_user.id)
        debt=Debt(user_id=user.id,title=data["title"],original_amount=data["amount"],remaining=data["amount"],due_date=data["due_date"])
        db.add(debt);await db.commit();await db.refresh(debt)
    await c.message.edit_text(f"✅ Qarz #{debt.id} qo‘shildi: {escape(debt.title)} · {debt.original_amount:,} so‘m"+(f" · {debt.due_date}" if debt.due_date else ""));await c.answer("Qarz saqlandi")


@router.callback_query(lambda c:c.data and c.data.startswith("debtcancel:"))
async def cancel_debt(c:CallbackQuery):
    token=c.data.split(":",1)[1];item=PENDING_DEBTS.pop(token,None)
    if item and item[0]==c.from_user.id: await c.message.edit_text("Qarz qo‘shish bekor qilindi; ma’lumot saqlanmadi.")
    await c.answer()

@router.message(Command("qarzlar"))
@router.message(lambda m: m.text=="💳 Qarzlar")
async def debts(m:Message,session_factory):
    async with session_factory() as db:
        u=await get_or_create_user(db,m.from_user.id);await db.commit();rows=await list_debts(db,u.id)
    if not rows: await m.answer("Ochiq qarz yo‘q. Yangi qarzni oddiy gap bilan yozing. Masalan: TBC Osmon kartaga 9-noyabrda 2 mln so‘m to‘lashim kerak");return
    total=sum(d.remaining for d in rows);body="💳 <b>Qarzlar</b>\n"+"\n".join(f"#{d.id} · {escape(d.title)} · qoldiq {d.remaining:,} so‘m"+(f" · {d.due_date}" if d.due_date else "") for d in rows)+f"\nJami: {total:,} so‘m"
    await m.answer(body)
@router.message(Command("pay"))
async def pay_start(m:Message,session_factory):
    async with session_factory() as db:
        u=await get_or_create_user(db,m.from_user.id);await db.commit();rows=await list_debts(db,u.id)
    if not rows: await m.answer("Ochiq qarz topilmadi.");return
    await m.answer("Qaysi qarz bo‘yicha to‘lov kiritamiz?",reply_markup=debt_keyboard(rows))
@router.callback_query(lambda c:c.data and c.data.startswith("debt:"))
async def select_debt(c:CallbackQuery,session_factory):
    did=int(c.data.split(":")[1])
    async with session_factory() as db:
        u=await get_or_create_user(db,c.from_user.id);d=await db.scalar(select(Debt).where(Debt.id==did,Debt.user_id==u.id,Debt.remaining>0))
    if not d: await c.answer("Qarz topilmadi",show_alert=True);return
    await c.message.answer(f"{escape(d.title)}: qoldiq {d.remaining:,} so‘m",reply_markup=payment_keyboard(did));await c.answer()
@router.callback_query(lambda c:c.data and c.data.startswith("payfull:"))
async def pay_full(c:CallbackQuery,session_factory):
    did=int(c.data.split(":")[1])
    async with session_factory() as db:
        u=await get_or_create_user(db,c.from_user.id)
        try: d,amount=await pay_debt(db,u.id,did)
        except ValueError as e: await c.answer(str(e),show_alert=True);return
    await c.message.edit_text(f"✅ {amount:,} so‘m to‘landi. Qoldiq: {d.remaining:,} so‘m");await c.answer()
@router.callback_query(lambda c:c.data and c.data.startswith("paypart:"))
async def pay_part(c:CallbackQuery): await c.message.answer("Qisman to‘lov uchun /pay_sum QARZ_ID SUMMA yuboring. Masalan: /pay_sum 2 100000");await c.answer()
@router.message(Command("pay_sum"))
async def pay_sum(m:Message,session_factory):
    try: _,ds,amount=m.text.split();did=int(ds);value=int(amount.replace(" ",""))
    except Exception: await m.answer("Format: /pay_sum QARZ_ID SUMMA");return
    async with session_factory() as db:
        u=await get_or_create_user(db,m.from_user.id)
        try: d,paid=await pay_debt(db,u.id,did,value)
        except ValueError as e: await m.answer(str(e));return
    await m.answer(f"✅ {paid:,} so‘m to‘landi. Qoldiq: {d.remaining:,} so‘m")


@router.message(Command("qarz_ozgartir"))
async def edit_debt(m:Message,session_factory):
    try:
        _,raw_id,ds,raw_amount,*title=m.text.split()
        did=int(raw_id);due=date.fromisoformat(ds);amount=int(raw_amount.replace(" ",""));name=" ".join(title)
        if amount<=0 or not name: raise ValueError()
    except Exception:
        await m.answer("Format: /qarz_ozgartir ID YYYY-MM-DD SUMMA NOMI");return
    async with session_factory() as db:
        user=await get_or_create_user(db,m.from_user.id)
        row=await db.scalar(select(Debt).where(Debt.id==did,Debt.user_id==user.id))
        if row:
            paid=row.original_amount-row.remaining
            if amount<paid: await m.answer(f"Yangi summa allaqachon to‘langan {paid:,} so‘mdan kam bo‘lolmaydi.");return
            row.title=name[:120];row.due_date=due;row.original_amount=amount;row.remaining=amount-paid;await db.commit()
    await m.answer("Qarz yangilandi." if row else "Qarz topilmadi.")

@router.message(Command("qarz_ochir"))
async def delete_debt(m:Message,session_factory):
    try: did=int(m.text.split(maxsplit=1)[1])
    except Exception: await m.answer("Format: /qarz_ochir ID");return
    async with session_factory() as db:
        user=await get_or_create_user(db,m.from_user.id)
        row=await db.scalar(select(Debt).where(Debt.id==did,Debt.user_id==user.id))
        if row:
            await db.execute(__import__("sqlalchemy").delete(DebtPayment).where(DebtPayment.debt_id==row.id,DebtPayment.user_id==user.id))
            await db.delete(row);await db.commit()
    await m.answer("Qarz va uning to‘lov tarixi o‘chirildi." if row else "Qarz topilmadi.")
