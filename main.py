import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN, PORT
from handlers import router

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def main():
    dp.include_router(router)
    print(f"🚀 Bot starting on port {PORT}")
    await bot.delete_webhook()  # Webhook hatao
    await dp.start_polling(bot, skip_updates=True)  # Polling mode

if __name__ == "__main__":
    asyncio.run(main())
