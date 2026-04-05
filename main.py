import asyncio, logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN, PORT
from handlers import router

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def main():
    dp.include_router(router)
    await bot.delete_webhook()
    print(f"🚀 Bot started on port {PORT}")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
