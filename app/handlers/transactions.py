import secrets, logging, re
from html import escape
from datetime import date, timedelta
from aiogram import Router,F
from aiogram.filters import Command
from aiogram.types import Message,CallbackQuery,InlineKeyboardMarkup,InlineKeyboardButton
from sqlalchemy import delete, func, select
from app.models import Transaction,User
from app.domain import parse_manual_entry,InputError,ParsedEntry
from app.keyboards import confirm_keyboard,category_keyboard,category_options
from app.services.finance import get_or_create_user,save_entry,monthly_totals
from app.services.ai import AIUnavailable
router=Router();log=logging.getLogger(__name__)
PENDING={}
ENTRY_KIND_BY_USER={}
CATEGORY_INPUT_BY_USER={}
EDIT_INPUT_BY_USER={}

def confirmation_text(entry):
    label="Xarajat" if entry.kind=="expense" else "Daromad"
    return f"🧾 <b>Yozuvni tekshiring</b>\nSumma: {entry.amount:,} so‘m\nTuri: {label}\nKategoriya: {escape(entry.category)}\nIzoh: {escape(entry.note or '—')}\nSana: {entry.occurred_on.isoformat()}\n\nFaqat tasdiqlaganingizdan keyin saqlanadi."

async def stage_entry(m,entry,user_id=None):
    token=secrets.token_urlsafe(9);PENDING[token]=(user_id or m.from_user.id,entry)
    await m.answer(confirmation_text(entry),reply_markup=confirm_keyboard(token))

async def stage(m,kind,text,ai,user_id=None):
    uid=user_id or m.from_user.id
    text=(text or "").strip()
    amount_first=bool(re.match(r"^\d",text))
    natural_action=bool(re.search(r"\b(?:yedim|yeydim|jedim|ichdim|oldim|sotib|sarfladim|ketdi|ketayapti|ketvotti|berdim|qildim|ob|olib|topdim|ishladim|ishlab|to‘ladim|to'ladim|toladim)\b",text,re.I))
    entry=None
    # Simple amount-first entries use deterministic parsing. Sentences with an
    # action go through AI so it can infer meaning/category from context.
    if amount_first and kind and not natural_action:
        try: entry=parse_manual_entry(text,kind)
        except InputError: pass
    if entry is None:
        try:
            await m.bot.send_chat_action(m.chat.id, "typing")
            entry=await ai.parse_entry(text,kind_hint=kind)
            # Trust an explicit numeric phrase for the amount, even if AI confuses
            # “400 ming” with “400”; keep AI's semantic category when useful.
            try:
                deterministic=parse_manual_entry(text,entry.kind)
                entry.amount=deterministic.amount
                if entry.category=="Boshqa": entry.category=deterministic.category
                if deterministic.note: entry.note=deterministic.note
            except InputError:
                pass
        except AIUnavailable as e:
            log.info("AI parse unavailable for uid=%s: %s",uid,e)
            if kind:
                try: entry=parse_manual_entry(text,kind)
                except InputError:
                    await m.answer("Matnni tushunmadim. Masalan: 400000 video xizmati yoki ‘video tayyorladim, 400 ming so‘m oldim’.");return
            else:
                if re.search(r"\d",text):
                    token=secrets.token_urlsafe(6)
                    PENDING[token]=(uid,ParsedEntry("expense",1,"Boshqa",text[:300]))
                    clarification=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="➖ Xarajat",callback_data=f"kind:{token}:e"),InlineKeyboardButton(text="➕ Daromad",callback_data=f"kind:{token}:i")],[InlineKeyboardButton(text="❌ Bekor",callback_data=f"cancel:{token}")]])
                    await m.answer("Bu summa xarajatmi yoki daromadmi?",reply_markup=clarification)
                    return
                await m.answer("AI tahlili ishlamadi. Internet va AI_API_KEY ni tekshiring.");return
    await stage_entry(m,entry,uid)

@router.callback_query(F.data.startswith("kind:"))
async def clarify_kind(c:CallbackQuery,ai):
    try: _,token,kind_code=c.data.split(":");kind={"e":"expense","i":"income"}[kind_code]
    except (ValueError,KeyError): await c.answer("Tanlov yaroqsiz.",show_alert=True);return
    item=PENDING.pop(token,None)
    if not item or item[0]!=c.from_user.id:
        await c.answer("Tanlov eskirgan yoki sizga tegishli emas.",show_alert=True);return
    await c.message.edit_reply_markup(reply_markup=None)
    await stage(c.message,kind,item[1].note,ai,user_id=c.from_user.id)
    await c.answer()

@router.message(Command("xarajat"))
async def expense(m:Message,ai):
    text=m.text.partition(" ")[2].strip()
    if not text: await m.answer("Xarajat misoli: /xarajat 45000 ovqat tushlik");return
    await stage(m,"expense",text,ai)
@router.message(Command("daromad"))
async def income(m:Message,ai):
    text=m.text.partition(" ")[2].strip()
    if not text: await m.answer("Daromad misoli: /daromad 5000000 oylik ish haqi");return
    await stage(m,"income",text,ai)
@router.message(F.text.in_({"➕ Xarajat","➕ Daromad"}))
async def menu_entry(m:Message):
    ENTRY_KIND_BY_USER[m.from_user.id]="expense" if m.text=="➕ Xarajat" else "income"
    sample="45000 ovqat tushlik" if m.text=="➕ Xarajat" else "5000000 oylik"
    await m.answer(f"Summani va izohni yuboring. Masalan: {sample}")

@router.message(lambda m: bool(m.text) and not m.text.startswith("/") and m.from_user.id in ENTRY_KIND_BY_USER)
async def menu_entry_text(m:Message,ai):
    kind=ENTRY_KIND_BY_USER.pop(m.from_user.id,None)
    if kind: await stage(m,kind,m.text,ai)
@router.message(lambda m: m.from_user and m.from_user.id in CATEGORY_INPUT_BY_USER)
async def receive_custom_category(m:Message):
    token=CATEGORY_INPUT_BY_USER.pop(m.from_user.id,None)
    item=PENDING.get(token) if token else None
    category=(m.text or "").strip()
    if not item or item[0]!=m.from_user.id:
        await m.answer("Kiritish muddati tugadi. Tranzaksiyani qayta yuboring.");return
    if not category or category.startswith("/"):
        CATEGORY_INPUT_BY_USER[m.from_user.id]=token
        await m.answer("Kategoriya nomini matn bilan yozing.");return
    item[1].category=category[:80]
    await m.answer(confirmation_text(item[1]),reply_markup=confirm_keyboard(token))

@router.callback_query(F.data.startswith("edit:"))
async def edit_entry(c:CallbackQuery):
    try:
        _,token,field=c.data.split(":")
    except ValueError:
        await c.answer("Tugma yaroqsiz.",show_alert=True);return
    item=PENDING.get(token)
    if not item or item[0]!=c.from_user.id or field not in {"amount","category","note"}:
        await c.answer("Bu tahrirlash so‘rovi eskirgan yoki sizga tegishli emas.",show_alert=True);return
    if field=="category":
        await c.message.edit_text("Kategoriyani tanlang yoki o‘zingiz kiriting:",reply_markup=category_keyboard(token,item[1].kind))
    else:
        EDIT_INPUT_BY_USER[c.from_user.id]=(token,field)
        prompt={"amount":"Yangi summani so‘mda yuboring (masalan, 450000).", "note":"Yangi izohni yuboring. Bo‘sh izoh uchun — yozing."}[field]
        await c.message.answer(prompt)
    await c.answer()

@router.message(lambda m: m.from_user and m.from_user.id in EDIT_INPUT_BY_USER)
async def receive_edit(m:Message):
    token,field=EDIT_INPUT_BY_USER.pop(m.from_user.id)
    item=PENDING.get(token)
    if not item or item[0]!=m.from_user.id:
        await m.answer("Tahrirlash muddati tugadi. Yozuvni qayta yuboring.");return
    value=(m.text or "").strip()
    if field=="amount":
        try:
            amount=int(value.replace(" ","").replace(",",""))
            if not 0<amount<=10**12: raise ValueError()
        except ValueError:
            EDIT_INPUT_BY_USER[m.from_user.id]=(token,field)
            await m.answer("Summa musbat butun son bo‘lsin. Masalan: 450000");return
        item[1].amount=amount
    else:
        item[1].note="" if value=="—" else value[:300]
    await m.answer(confirmation_text(item[1]),reply_markup=confirm_keyboard(token))

@router.callback_query(F.data.startswith("category:"))
async def choose_category(c:CallbackQuery):
    token=c.data.split(":",1)[1];item=PENDING.get(token)
    if not item or item[0]!=c.from_user.id:
        await c.answer("Bu tasdiqlash sizga tegishli emas yoki muddati tugagan.",show_alert=True);return
    await c.message.edit_text("Kategoriyani tanlang yoki o‘zingiz kiriting:",reply_markup=category_keyboard(token,item[1].kind));await c.answer()

@router.callback_query(F.data.startswith("catcustom:"))
async def request_custom_category(c:CallbackQuery):
    token=c.data.split(":",1)[1];item=PENDING.get(token)
    if not item or item[0]!=c.from_user.id:
        await c.answer("Bu tasdiqlash sizga tegishli emas yoki muddati tugagan.",show_alert=True);return
    CATEGORY_INPUT_BY_USER[c.from_user.id]=token
    await c.message.answer("O‘zingiz xohlagan kategoriya nomini yozing:")
    await c.answer()

@router.callback_query(F.data.startswith("catback:"))
async def category_back(c:CallbackQuery):
    token=c.data.split(":",1)[1];item=PENDING.get(token)
    if not item or item[0]!=c.from_user.id:
        await c.answer("Bu tasdiqlash sizga tegishli emas yoki muddati tugagan.",show_alert=True);return
    await c.message.edit_text(confirmation_text(item[1]),reply_markup=confirm_keyboard(token));await c.answer()

@router.callback_query(F.data.startswith("cat:"))
async def set_category(c:CallbackQuery):
    try: _,token,index=c.data.split(":");index=int(index)
    except Exception: await c.answer("Kategoriyani tanib bo‘lmadi.",show_alert=True);return
    item=PENDING.get(token)
    if not item or item[0]!=c.from_user.id:
        await c.answer("Bu tasdiqlash sizga tegishli emas yoki muddati tugagan.",show_alert=True);return
    options=category_options(item[1].kind)
    if index<0 or index>=len(options): await c.answer("Bunday kategoriya yo‘q.",show_alert=True);return
    item[1].category=options[index]
    await c.message.edit_text(confirmation_text(item[1]),reply_markup=confirm_keyboard(token));await c.answer("Kategoriya yangilandi")

@router.callback_query(F.data.startswith("confirm:"))
async def confirm(c:CallbackQuery,session_factory):
    token=c.data.split(":",1)[1]; item=PENDING.pop(token,None)
    if not item or item[0]!=c.from_user.id: await c.answer("Tasdiqlash eskirgan yoki sizga tegishli emas",show_alert=True);return
    async with session_factory() as db:
        user=await get_or_create_user(db,c.from_user.id);row=await save_entry(db,user.id,item[1]);totals=await monthly_totals(db,user.id,date.today().year,date.today().month);limit=user.monthly_limit
    notice=f"✅ #{row.id} saqlandi: {row.amount:,} so‘m · {row.category}"
    if row.kind=="expense" and limit and totals["expense"]>limit: notice+=f"\n⚠️ Oylik limitdan {totals['expense']-limit:,} so‘m oshdi."
    await c.message.edit_text(notice);await c.answer("Saqlandi")
@router.callback_query(F.data.startswith("cancel:"))
async def cancel(c:CallbackQuery):
    token=c.data.split(":",1)[1];item=PENDING.pop(token,None)
    if item and item[0]==c.from_user.id: await c.message.edit_text("Bekor qilindi; ma'lumot saqlanmadi.")
    await c.answer()
@router.message(Command("hisobot"))
@router.message(F.text=="📊 Hisobot")
async def report(m:Message,session_factory):
    mode=(m.text or "").partition(" ")[2].strip().casefold()
    async with session_factory() as db:
        u=await get_or_create_user(db,m.from_user.id);await db.commit()
        today=date.today()
        if mode in {"kun","bugun","bugun"}: start=end=today; title="Bugungi hisobot"
        elif mode in {"hafta","haftalik"}: start=today-timedelta(days=today.weekday());end=today;title="Shu haftadagi hisobot"
        elif mode in {"kategoriya","kategoriyalar"}: start=today.replace(day=1);end=today;title="Shu oy kategoriya bo‘yicha"
        else: start=today.replace(day=1);end=today;title="Shu oy hisoboti"
        rows=(await db.execute(select(Transaction.kind,func.sum(Transaction.amount)).where(Transaction.user_id==u.id,Transaction.occurred_on.between(start,end)).group_by(Transaction.kind))).all()
        values={kind:int(total or 0) for kind,total in rows};s={"income":values.get("income",0),"expense":values.get("expense",0)}
        cats=(await db.execute(select(Transaction.category,func.sum(Transaction.amount)).where(Transaction.user_id==u.id,Transaction.kind=="expense",Transaction.occurred_on.between(start,end)).group_by(Transaction.category).order_by(func.sum(Transaction.amount).desc()).limit(10))).all() if mode in {"kategoriya","kategoriyalar"} else []
        limit=u.monthly_limit
    diff=s['income']-s['expense'];remaining=max(0,limit-s['expense']) if limit else 0
    extra=(f"\n🎯 Oylik limit qoldig‘i: {remaining:,} so‘m" if limit else "\n🎯 Oylik limit belgilanmagan (/limit SUMMA)") if mode not in {"kun","bugun","hafta","haftalik","kategoriya","kategoriyalar"} else ""
    categories="\n\n<b>Kategoriyalar:</b>\n"+"\n".join(f"• {escape(name)}: {int(amount):,} so‘m" for name,amount in cats) if cats else ""
    await m.answer(f"📊 <b>{title}</b> ({start.isoformat()} – {end.isoformat()})\n📥 Daromad: {s['income']:,} so‘m\n📤 Xarajat: {s['expense']:,} so‘m\n💰 Farq: {diff:,} so‘m{extra}{categories}\n\nBu hisob kiritilgan yozuvlar asosida; bank balansi emas.")
@router.message(Command("limit"))
async def set_limit(m:Message,session_factory):
    try: amount=int(m.text.split(maxsplit=1)[1].replace(" ",""));assert amount>=0
    except Exception: await m.answer("Misol: /limit 1500000 (o‘chirish uchun /limit 0)");return
    async with session_factory() as db:
        u=await get_or_create_user(db,m.from_user.id);u.monthly_limit=amount;await db.commit()
    await m.answer("Oylik limit yangilandi.")
@router.message(Command("oxirgi"))
async def recent(m:Message,session_factory):
    async with session_factory() as db:
        u=await get_or_create_user(db,m.from_user.id);rows=(await db.scalars(select(Transaction).where(Transaction.user_id==u.id).order_by(Transaction.id.desc()).limit(10))).all()
    await m.answer("Oxirgi yozuvlar:\n"+("\n".join(f"#{r.id} {r.kind} {r.amount:,} so‘m · {escape(r.category)}" for r in rows) if rows else "Hozircha yozuv yo‘q"))
@router.message(Command("ochir"))
async def remove(m:Message,session_factory):
    try: item_id=int(m.text.split(maxsplit=1)[1])
    except Exception: await m.answer("Misol: /ochir 12");return
    async with session_factory() as db:
        u=await get_or_create_user(db,m.from_user.id);row=await db.scalar(select(Transaction).where(Transaction.id==item_id,Transaction.user_id==u.id))
        if row: await db.delete(row);await db.commit()
    await m.answer("Yozuv o‘chirildi." if row else "Bunday yozuv topilmadi.")


@router.message(F.voice | F.audio)
async def voice_entry(m:Message,bot,ai):
    media=m.voice or m.audio
    if media.file_size and media.file_size>20*1024*1024:
        await m.answer("Audio fayl 20 MB dan kichik bo‘lsin.");return
    try:
        await m.bot.send_chat_action(m.chat.id,"typing")
        file=await bot.get_file(media.file_id)
        from io import BytesIO
        buffer=BytesIO();await bot.download_file(file.file_path,destination=buffer)
        transcript=await ai.transcribe(getattr(media,"file_name",None) or "voice.ogg",buffer.getvalue())
        if not transcript.strip(): raise AIUnavailable("Audio ichida matn topilmadi")
        await m.answer(f"🎙 Eshitilgan matn: <i>{escape(transcript[:500])}</i>")
        await stage(m,None,transcript,ai)
    except AIUnavailable as e:
        log.info("Voice parse failed uid=%s: %s",m.from_user.id,e)
        await m.answer("Ovoz tahlili bajarilmadi. AI_API_KEY, audio sifati va internetni tekshiring.")
    except Exception as e:
        log.warning("Voice handling failed uid=%s error=%s",m.from_user.id,type(e).__name__)
        await m.answer("Ovoz faylini olish yoki tahlil qilishda xatolik yuz berdi. Xarajatni matn bilan kiriting: /xarajat 45000 ovqat.")

@router.message(F.photo)
async def image_entry(m:Message,bot,ai):
    photo=m.photo[-1]
    if photo.file_size and photo.file_size>10*1024*1024:
        await m.answer("Rasm 10 MB dan kichik bo‘lsin.");return
    try:
        await m.bot.send_chat_action(m.chat.id,"typing")
        file=await bot.get_file(photo.file_id)
        from io import BytesIO
        buffer=BytesIO();await bot.download_file(file.file_path,destination=buffer)
        entry=await ai.parse_image("image/jpeg",buffer.getvalue())
        await stage_entry(m,entry)
    except AIUnavailable as e:
        log.info("Image parse failed uid=%s: %s",m.from_user.id,e)
        await m.answer("Rasmdan summa aniqlanmadi. Aniqroq chek yuboring yoki /xarajat SUMMA izoh shaklida kiriting.")
    except Exception as e:
        log.warning("Image handling failed uid=%s error=%s",m.from_user.id,type(e).__name__)
        await m.answer("Rasmni tahlil qilishda xatolik yuz berdi. Summani matn bilan kiriting: /xarajat 45000 ovqat.")


@router.message(Command("ozgartir"))
async def edit_transaction(m:Message,session_factory):
    try:
        _,raw_id,raw_amount,*note=m.text.split()
        item_id=int(raw_id);entry=parse_manual_entry(raw_amount+" "+" ".join(note),"expense")
    except Exception:
        await m.answer("Format: /ozgartir ID SUMMA KATEGORIYA IZOHH\nEslatma: tranzaksiya turi o‘zgarmaydi.");return
    async with session_factory() as db:
        user=await get_or_create_user(db,m.from_user.id)
        row=await db.scalar(select(Transaction).where(Transaction.id==item_id,Transaction.user_id==user.id))
        if row:
            # Preserve the original kind while updating the other editable fields.
            row.amount=entry.amount;row.category=entry.category;row.note=entry.note;await db.commit()
    await m.answer("Yozuv yangilandi." if row else "Bunday yozuv topilmadi.")
