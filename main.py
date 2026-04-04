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

# 🔥 PORT ko int mein convert karo
PORT = int(os.environ.get("PORT", 10000))

async def health_check(request):
    return web.Response(text="Bot is running!")

async def main():
    dp.include_router(router)
    
    # Webhook delete
    await bot.delete_webhook()
    
    # Web server for health check
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    
    # Start web server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    
    print(f"🚀 Bot started on port {PORT}")
    print(f"🤖 Polling mode active")
    
    # Start polling
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
