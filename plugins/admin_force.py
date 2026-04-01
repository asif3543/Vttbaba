from pyrogram import Client, filters
from pyrogram.types import Message
import database
import config

@Client.on_message(filters.command("Force sub") & filters.user(config.ADMINS))
async def cmd_force_sub(client: Client, message: Message):
    await message.reply("Bot reply please send massage and chack I'm admin gc\n(Forward message from channel)")

@Client.on_message(filters.forwarded & filters.user(config.ADMINS))
async def handle_forward(client: Client, message: Message):
    if message.forward_from_chat:
        ch_id = message.forward_from_chat.id
        title = message.forward_from_chat.title
        try:
            member = await client.get_chat_member(ch_id, client.me.id)
            if member.privileges:
                database.add_force_sub(ch_id)
                # Auto add to target channels for /send
                database.add_target_channel(ch_id, title)
                await message.reply("😘 adding successfully 😲\n(Also added to /send channel list!)")
            else:
                await message.reply("Bot admin nahi hai us channel me!")
        except:
            await message.reply("Bot ko pehle channel me admin banao!")
