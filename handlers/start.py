from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
Message,
CallbackQuery,
InlineKeyboardMarkup,
InlineKeyboardButton
)

from config import OWNER_ID, ALLOWED_USERS, BOT_USERNAME, STORAGE_CHANNEL_ID
from database import db
from .shortner import make_shortlink

router = Router()

================= ADMIN CHECK =================

def is_admin(uid):
return uid == OWNER_ID or uid in ALLOWED_USERS

================= START COMMAND =================

@router.message(Command("start"))
async def start_cmd(message: Message):

# ===== DEEP LINK CHECK =====

if message.text and " " in message.text:

    arg = message.text.split(" ", 1)[1]

    if arg.startswith("ep_"):

        episode_param = arg.replace("ep_", "")

        await process_episode_request(
            message,
            episode_param
        )

        return

# ===== NORMAL START =====

text = (
    "🤖 Bot is alive!\n\n"
    "📌 **Admin Commands:**\n"
    "/post - Upload new post\n"
    "/send - Send to single channel\n"
    "/sendmorechannel - Send to multiple channels\n"
    "/confirm - Confirm send\n"
    "/hmm - Confirm post\n"
    "/adshort - Add shortner\n"
    "/addpri - Add premium\n"
    "/removepri - Remove premium\n"
    "/forcesub - Add force subscribe\n"
)

await message.reply(
    text,
    parse_mode="Markdown"
)

================= MAIN EPISODE HANDLER =================

async def process_episode_request(
message: Message,
episode_param: str
):

uid = message.from_user.id

print(
    f"📥 Episode Request: {episode_param} from user {uid}"
)

# ===== BAN CHECK =====

if await db.is_banned(uid):

    await message.reply(
        "❌ You are banned from using this bot."
    )

    return

# ===== PREMIUM CHECK =====

if await db.is_premium(uid):

    print("⭐ Premium user detected")

    await send_episode_direct(
        message,
        episode_param
    )

    return

# ===== FORCE SUB CHECK =====

fsubs = await db.get_fsub()

not_joined = []

for ch in fsubs:

    try:

        member = await message.bot.get_chat_member(
            ch["_id"],
            uid
        )

        if member.status not in [
            "member",
            "administrator",
            "creator"
        ]:

            not_joined.append(ch)

    except:

        not_joined.append(ch)

if not_joined:

    buttons = []

    for ch in not_joined:

        buttons.append([
            InlineKeyboardButton(
                text=f"📢 Join {ch['name']}",
                url=ch["link"]
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="✅ Try Again",
            callback_data=f"retry_{episode_param}"
        )
    ])

    await message.reply(
        "❌ **Join all channels first:**",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        ),
        parse_mode="Markdown"
    )

    return

# ===== SHORTNER FLOW =====

shortners = await db.get_shortners()

original_url = (
    f"https://t.me/{BOT_USERNAME}"
    f"?start=ep_{episode_param}"
)

short_url = original_url

if shortners:

    import random

    random.shuffle(shortners)

    for s in shortners:

        try:

            temp = await make_shortlink(
                s,
                original_url
            )

            if (
                temp
                and temp.startswith("http")
                and temp != original_url
            ):

                short_url = temp

                print(
                    f"✅ Short URL generated: {short_url}"
                )

                break

        except Exception as e:

            print(
                f"❌ Shortner failed: {e}"
            )

# ===== SEND SHORTNER =====

await message.reply(
    f"🔗 **Solve this shortner:**\n\n{short_url}\n\n"
    "After solving, you will get the episode.",
    parse_mode="Markdown"
)

================= PREMIUM / DIRECT SEND =================

async def send_episode_direct(
message: Message,
episode_param: str
):

uid = message.from_user.id

print(
    f"📤 Sending episode directly to premium user {uid}: {episode_param}"
)

# ===== BATCH RANGE =====

if "-" in episode_param:

    try:

        start_str, end_str = episode_param.split("-")

        start = int(start_str)

        end = int(end_str)

        batch_data = await db.get_batch_range(
            start,
            end
        )

        if not batch_data:

            await message.reply(
                "❌ No episodes found."
            )

            return

        for ep_num in range(
            start,
            end + 1
        ):

            msg_id = batch_data.get(ep_num)

            if msg_id:

                try:

                    await message.bot.copy_message(
                        uid,
                        STORAGE_CHANNEL_ID,
                        msg_id
                    )

                    print(
                        f"✅ Sent episode {ep_num}"
                    )

                except Exception as e:

                    print(
                        f"❌ Episode send fail {ep_num}: {e}"
                    )

            else:

                await message.reply(
                    f"⚠️ Episode {ep_num} missing."
                )

    except Exception as e:

        print(
            f"Batch range error: {e}"
        )

        await message.reply(
            "❌ Invalid batch range."
        )

    return

# ===== SINGLE EPISODE =====

post = await db.get_post_by_episode(
    episode_param
)

if not post:

    await message.reply(
        "❌ Episode not found."
    )

    return

try:

    await message.bot.copy_message(
        uid,
        STORAGE_CHANNEL_ID,
        post["storage_msg_id"]
    )

    print(
        "✅ Single episode sent"
    )

except Exception as e:

    await message.reply(
        f"❌ Failed to send episode:\n{e}"
    )

================= RETRY BUTTON =================

@router.callback_query(F.data.startswith("retry_"))
async def retry_callback(callback: CallbackQuery):

episode_param = callback.data.split("_", 1)[1]

await callback.message.delete()

await process_episode_request(
    callback.message,
    episode_param
)

await callback.answer()
