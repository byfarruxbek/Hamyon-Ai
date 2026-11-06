import asyncio,logging
from aiogram import Bot,Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.config import Settings
from app.db import make_session_factory,init_db
from app.middleware import RateLimitMiddleware,UserActivityMiddleware
from app.services.ai import AIService
from app.handlers import common,transactions,debts,ai,reminders,fallback,engagement
from app.services.reminders import reminder_loop
from app.services.engagement import engagement_loop
async def run():
    logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    s=Settings()
    if not s.telegram_bot_token or s.telegram_bot_token=="put_your_telegram_token_here": raise RuntimeError("TELEGRAM_BOT_TOKEN ni .env faylida sozlang")
    engine,factory=make_session_factory(s.database_url);await init_db(engine)
    bot=Bot(s.telegram_bot_token,default=DefaultBotProperties(parse_mode=ParseMode.HTML));dp=Dispatcher()
    for event_name in (dp.message,dp.callback_query):
        event_name.middleware(RateLimitMiddleware(s.rate_limit_per_minute))
        event_name.middleware(UserActivityMiddleware())
    dp.include_routers(common.router,transactions.router,debts.router,ai.router,reminders.router,engagement.router,fallback.router)
    api_key=s.ai_api_key or s.openai_api_key
    model=s.ai_model if s.ai_api_key else s.openai_model
    transcription_model=s.ai_transcribe_model or (s.openai_transcribe_model if s.openai_api_key and not s.ai_api_key else "")
    base_url=s.ai_base_url if s.ai_api_key else (None if s.openai_api_key else s.ai_base_url)
    dp["session_factory"]=factory;dp["ai"]=AIService(api_key,model,transcription_model,base_url);dp["timezone"]=s.timezone
    task=asyncio.create_task(reminder_loop(bot,factory,s.timezone))
    engagement_task=asyncio.create_task(engagement_loop(bot,factory,s.timezone,s.engagement_nudge_hour))
    try: await dp.start_polling(bot)
    finally:
        task.cancel();engagement_task.cancel()
        await asyncio.gather(task,engagement_task,return_exceptions=True)
        await bot.session.close();await engine.dispose()
