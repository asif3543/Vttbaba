from pyrogram import Client, filters
from pyrogram.types import Message
import database
import config

@Client.on_message(filters.command("Force sub") & (filters.user(config.ADMINS) | filters.chat(config.ALLOWED_GROUP)))
async def force_sub(client: Client, message: Message):
    await message.reply("Bot reply please send massage and chack I'm admin gc\n(Ab channel ka koi message forward karo yaha)")

@Client.on_message(filters.forwarded & (filters.user(config.ADMINS) | filters.chat(config.ALLOWED_GROUP)))
async def check_forward(client: Client, message: Message):
    if message.forward_from_chat:
        channel_id = message.forward_from_chat.id
        # Check if bot is admin
        try:
            member = await client.get_chat_member(channel_id, client.me.id)
            if member.privileges:
                database.add_force_sub(channel_id)
                await message.reply("😘 adding successfully 😲")
            else:
                await message.reply("Bot channel me admin nahi hai!")
        except Exception as e:
            await message.reply("Bot ko channel me admin bana ke fir message forward karo.")
