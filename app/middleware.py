import time
from collections import defaultdict,deque
from datetime import datetime
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy import select
from app.models import UserActivity
from app.services.finance import get_or_create_user

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self,limit): self.limit=limit;self.events=defaultdict(deque)
    async def __call__(self,handler,event:TelegramObject,data):
        user=getattr(event,"from_user",None)
        if user:
            now=time.monotonic();q=self.events[user.id]
            while q and now-q[0]>60:q.popleft()
            if len(q)>=self.limit:
                msg=getattr(event,"answer",None)
                if msg: await msg("Juda tez yuboryapsiz. Biroz kuting.")
                return None
            q.append(now)
        return await handler(event,data)

class UserActivityMiddleware(BaseMiddleware):
    async def __call__(self,handler,event:TelegramObject,data):
        telegram_user=getattr(event,"from_user",None)
        factory=data.get("session_factory")
        if telegram_user and factory:
            async with factory() as db:
                user=await get_or_create_user(db,telegram_user.id)
                activity=await db.get(UserActivity,user.id)
                now=datetime.utcnow()
                if activity is None:
                    activity=UserActivity(user_id=user.id,first_name=telegram_user.first_name,last_seen_at=now)
                    db.add(activity)
                else:
                    activity.first_name=telegram_user.first_name or activity.first_name
                    activity.last_seen_at=now
                await db.commit()
        return await handler(event,data)
