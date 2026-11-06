from datetime import date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, Transaction, Debt, DebtPayment
from app.domain import ParsedEntry, validate_payment

async def get_or_create_user(db: AsyncSession, telegram_id: int) -> User:
    user = await db.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(telegram_id=telegram_id); db.add(user); await db.flush()
    return user

async def save_entry(db, user_id: int, entry: ParsedEntry) -> Transaction:
    row=Transaction(user_id=user_id,kind=entry.kind,amount=entry.amount,category=entry.category,note=entry.note,occurred_on=entry.occurred_on)
    db.add(row); await db.commit(); await db.refresh(row); return row

async def create_debt(db,user_id,title,amount,due_date=None):
    if amount<=0: raise ValueError("Summa musbat bo‘lsin")
    row=Debt(user_id=user_id,title=title[:120],original_amount=amount,remaining=amount,due_date=due_date);db.add(row);await db.commit();await db.refresh(row);return row

async def list_debts(db,user_id):
    return list((await db.scalars(select(Debt).where(Debt.user_id==user_id,Debt.remaining>0).order_by(Debt.due_date))).all())

async def pay_debt(db,user_id,debt_id,amount=None):
    debt=await db.scalar(select(Debt).where(Debt.id==debt_id,Debt.user_id==user_id).with_for_update())
    if debt is None: raise ValueError("Qarz topilmadi")
    paid=validate_payment(debt.remaining,amount);debt.remaining-=paid;db.add(DebtPayment(user_id=user_id,debt_id=debt.id,amount=paid));await db.commit();return debt,paid

async def monthly_totals(db,user_id,year,month):
    from calendar import monthrange
    start=date(year,month,1); end=date(year,month,monthrange(year,month)[1])
    rows=(await db.execute(select(Transaction.kind,func.sum(Transaction.amount)).where(Transaction.user_id==user_id,Transaction.occurred_on.between(start,end)).group_by(Transaction.kind))).all()
    result={kind:int(total or 0) for kind,total in rows};return {"income":result.get("income",0),"expense":result.get("expense",0)}
