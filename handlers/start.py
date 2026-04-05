from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from config import OWNER_ID, ALLOWED_USERS
from database import db

router = Router()

def is_admin(uid):
    return uid == OWNER_ID or uid in ALLOWED_USERS

@router.message(Command("start"))
async def start_cmd(message: Message):
    await message.reply(
        "🤖 Bot is alive!\n\n"
        "📌 Admin Commands:\n"
        "/post - Upload new post\n"
        "/add shortner account - Add shortner\n"
        "/remove shortner account - Remove shortner\n"
        "/add premium - Add premium user (28 days)\n"
        "/remove premium - Remove premium\n"
        "/show premium list - Show premium users\n"
        "/Force sub - Add force subscribe channel\n"
        "/send - Send to single channel\n"
        "/send more channel - Send to multiple channels\n"
        "/confirm - Confirm action\n"
        "/hmm - Confirm post\n"
        "/hu hu - Confirm premium\n"
        "/delete - Delete shortner"
    )
