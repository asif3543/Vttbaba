
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

async def health(request):
    return web.Response(text="Bot is running", status=200)

async def main():
    dp.include_router(router)
    await bot.delete_webhook()
    
    # Web server for Render port binding
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    
    print(f"🚀 Bot started on port {PORT}")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
