import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiohttp import web
from config import BOT_TOKEN
from handlers import router

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 🔥 PORT force detect
PORT = int(os.environ.get("PORT", 8080))

async def handle_webhook(request):
    json_data = await request.json()
    update = Update(**json_data)
    await dp.feed_update(bot, update)
    return web.Response(status=200)

async def on_startup():
    await bot.delete_webhook()
    webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/webhook"
    await bot.set_webhook(webhook_url)
    print(f"✅ Webhook set to {webhook_url}")
    print(f"🚀 Bot running on port {PORT}")

async def main():
    dp.include_router(router)
    
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    app.on_startup.append(lambda _: on_startup())
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    
    print(f"🤖 Bot is alive on port {PORT}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
