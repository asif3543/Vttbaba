import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiohttp import web
from config import BOT_TOKEN
from handlers import router

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

PORT = int(os.environ.get("PORT", 10000))

async def main():
    dp.include_router(router)
    
    # Webhook delete karo
    await bot.delete_webhook()
    
    # Simple web server to keep Render happy
    app = web.Application()
    
    async def health_check(request):
        return web.Response(text="Bot is running!")
    
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    
    # Run polling + web server together
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    
    print(f"🚀 Bot started on port {PORT}")
    print(f"🤖 Polling mode active")
    
    # Start polling in background
    polling_task = asyncio.create_task(dp.start_polling(bot, skip_updates=True))
    
    # Keep running
    await polling_task

if __name__ == "__main__":
    asyncio.run(main())
