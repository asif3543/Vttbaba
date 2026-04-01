from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
import requests
import database

async def check_joined(client, user_id):
    for ch in database.get_force_subs():
        try: await client.get_chat_member(ch, user_id)
        except UserNotParticipant: return False
        except Exception: pass
    return True

@Client.on_message(filters.command("start") & filters.private)
async def cmd_start(client: Client, message: Message):
    user_id = message.from_user.id
    text = message.text

    if len(text.split()) > 1:
        param = text.split()[1]

        # Force Sub Check
        if not await check_joined(client, user_id):
            btns = [[InlineKeyboardButton(f"Join Channel {i+1}", url=f"https://t.me/c/{str(ch).replace('-100', '')}/1")] for i, ch in enumerate(database.get_force_subs())]
            btns.append([InlineKeyboardButton("Try again", url=f"https://t.me/{client.me.username}?start={param}")])
            await message.reply("Bot reply - join first", reply_markup=InlineKeyboardMarkup(btns))
            return

        if param.startswith("post_"):
            post_id = param.replace("post_", "")
            if database.is_premium(user_id):
                await send_episode(client, message.chat.id, post_id)
            else:
                shortner = database.get_random_shortner()
                if shortner:
                    target_url = f"https://t.me/{client.me.username}?start=unlock_{post_id}"
                    api_url = f"https://{shortner['shortner_url']}/api?api={shortner['api_key']}&url={target_url}"
                    try:
                        res = requests.get(api_url).json()
                        short_url = res.get("shortenedUrl", res.get("shorturl"))
                        btn = InlineKeyboardMarkup([[InlineKeyboardButton("Unlock Episode", url=short_url)]])
                        await message.reply("Please solve this link to get your episode:", reply_markup=btn)
                    except:
                        await message.reply("Shortner API error.")
                else:
                    await message.reply("No shortner accounts linked. Admins need to add one.")

        elif param.startswith("unlock_"):
            post_id = param.replace("unlock_", "")
            await send_episode(client, message.chat.id, post_id)
    else:
        await message.reply("Hello! Use /Setting to see bot commands.")

async def send_episode(client, chat_id, post_id):
    post = database.get_post(post_id)
    if not post: return await client.send_message(chat_id, "Post not found.")
    file_ids = post['link'].split(',')
    for fid in file_ids:
        await client.send_cached_media(chat_id, fid)
