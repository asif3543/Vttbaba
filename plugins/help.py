from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMINS

@Client.on_message(filters.command(["settings", "help"]) & filters.private)
async def help_cmd(client: Client, message: Message):
    text = """🌵 **Help Menu**

I am a permanent file store bot. You can store files from your public channel without me being an admin there. Either your channel/group is private, make me admin.

📚 **Available Commands:**
➜ /start - Check I am alive.
➜ /post - Interactive post builder.
➜ /genlink - Shortcut for single file link.
➜ /batch - Shortcut for batch links.
➜ /settings - Show this menu.
 
🛡️ **Moderators Commands:**
➜ /broadcast - Broadcast a message to users.
➜ /add shortner account - Add shortener API.
➜ /add premium - Add premium user.
➜ /force sub - Setup Force Sub."""
    
    btns = [[InlineKeyboardButton("🛠️ Settings", callback_data="settings_menu")]]
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(btns))
