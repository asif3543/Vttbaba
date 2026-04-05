from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from config import OWNER_ID, ALLOWED_USERS

router = Router()

def is_admin(uid):
    return uid == OWNER_ID or uid in ALLOWED_USERS

@router.message(Command("start"))
async def start_cmd(message: Message):
    await message.reply(
        "🤖 Bot is alive!\n\n"
        "📌 Admin Commands:\n"
        "/post - Upload new post\n"
        "/adshort - Add shortner account\n"
        "/removeshot - Remove shortner account\n"
        "/addpri - Add premium user (28 days)\n"
        "/removepri - Remove premium\n"
        "/showpremiumlist - Show premium users\n"
        "/Forcesub - Add force subscribe channel\n"
        "/send - Send to single channel\n"
        "/sendmorechannel - Send to multiple channels\n"
        "/confirm - Confirm action\n"
        "/hmm - Confirm post\n"
        "/huhu - Confirm premium\n"
        "/delete - Delete shortner"
    )
