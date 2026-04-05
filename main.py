import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiohttp import web
from config import BOT_TOKEN, PORT
from handlers import router

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def health_check(request):
    """Health check endpoint for Render to keep bot alive"""
    return web.Response(text="Bot is running!", status=200)

async def main():
    dp.include_router(router)
    
    # Delete any existing webhook
    await bot.delete_webhook()
    print("✅ Webhook deleted")
    
    # Start web server for health checks (keeps Render from sleeping)
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    
    print(f"🚀 Bot started on port {PORT}")
    print(f"🤖 Polling mode active")
    print(f"📡 Health check available at /health")
    
    # Start polling
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
