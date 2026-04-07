limport hashlib
import asyncio
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import (
    OWNER_ID,
    ALLOWED_USERS,
    BOT_USERNAME,
    STORAGE_CHANNEL_ID,
    EPISODE_CHANNEL_ID,
    SECRET_HASH
)

from database import db
from .shortner import make_shortlink

router = Router()

# ================= ADMIN CHECK =================

def is_admin(uid):
    return uid == OWNER_ID or uid in ALLOWED_USERS

# ================= HASH GENERATOR =================

def generate_hash(episode: str) -> str:
    return hashlib.md5(
        f"{episode}_{SECRET_HASH}".encode()
    ).hexdigest()[:10]

# ================= FORCE SUB CHECK =================

async def get_unjoined_channels(bot, uid):
    fsubs = await db.get_fsub()
    not_joined = []

    for ch in fsubs:
        try:
            member = await bot.get_chat_member(
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

    return not_joined

# ================= START COMMAND =================

@router.message(Command("start"))
async def start_cmd(message: Message):

    uid = message.from_user.id

    if await db.is_banned(uid):
        await message.reply(
            "❌ You are banned from using this bot."
        )
        return

    # ========= HANDLE ARGUMENT =========

    if message.text and " " in message.text:

        arg = message.text.split(
            " ",
            1
        )[1].strip()

        # ===== NEW REQUEST =====

        if arg.startswith("ep_"):

            ep = arg.replace("ep_", "")

            await handle_new_request(
                message,
                ep
            )

            return

        # ===== RESOLVED LINK =====

        elif arg.startswith("res_"):

            parts = arg.replace(
                "res_",
                ""
            ).rsplit("_", 1)

            if len(parts) == 2:

                ep, received_hash = parts

                expected_hash = generate_hash(ep)

                # ===== DEBUG LOG =====
                print("Episode:", ep)
                print("Received:", received_hash)
                print("Expected:", expected_hash)

                if received_hash == expected_hash:

                    await handle_resolved_request(
                        message,
                        ep
                    )

                else:

                    await message.reply(
                        "❌ <b>Invalid or expired link!</b>\n"
                        "Please click the button from the channel again.",
                        parse_mode="HTML"
                    )

            else:

                await message.reply(
                    "❌ <b>Broken Link!</b>",
                    parse_mode="HTML"
                )

            return

        else:

            await message.reply(
                "⚠️ <b>Invalid Command!</b>",
                parse_mode="HTML"
            )

            return

    # ========= ADMIN PANEL =========

    if is_admin(uid):

        text = (
            "🤖 <b>Bot is alive!</b>\n\n"
            "📌 <b>Admin Commands:</b>\n"
            "/post\n"
            "/send\n"
            "/sendmorechannel\n"
            "/confirm\n"
            "/hmm\n"
            "/adshort\n"
            "/removeshot\n"
            "/delete\n"
            "/addpri\n"
            "/removepri\n"
            "/showpremiumlist\n"
            "/forcesub"
        )

        await message.reply(
            text,
            parse_mode="HTML"
        )

    else:

        await message.reply(
            "👋 <b>Welcome!</b>\n"
            "Please use buttons from channel.",
            parse_mode="HTML"
        )

# ================= NEW REQUEST =================

async def handle_new_request(
    message: Message,
    ep: str
):

    uid = message.from_user.id

    if await db.is_premium(uid):

        await send_episode_direct(
            message,
            ep
        )

        return

    not_joined = await get_unjoined_channels(
        message.bot,
        uid
    )

    if not_joined:

        await ask_for_fsub(
            message,
            not_joined,
            f"ep_{ep}"
        )

        return

    msg = await message.reply(
        "⏳ Generating secure link..."
    )

    hash_val = generate_hash(ep)

    bot_name = BOT_USERNAME.replace(
        "@",
        ""
    )

    original_url = (
        f"https://t.me/{bot_name}"
        f"?start=res_{ep}_{hash_val}"
    )

    shortners = await db.get_shortners()

    short_url = original_url

    if shortners:

        import random

        random.shuffle(shortners)

        for s in shortners:

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
                break

    if short_url == original_url and shortners:

        await msg.edit_text(
            "❌ <b>Shortner API Error!</b>",
            parse_mode="HTML"
        )

        return

    await msg.edit_text(
        f"🔗 <b>Solve shortner:</b>\n\n"
        f"{short_url}",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

# ================= RESOLVED =================

async def handle_resolved_request(
    message: Message,
    ep: str
):

    uid = message.from_user.id

    not_joined = await get_unjoined_channels(
        message.bot,
        uid
    )

    if not_joined:

        hash_val = generate_hash(ep)

        await ask_for_fsub(
            message,
            not_joined,
            f"res_{ep}_{hash_val}"
        )

        return

    await send_episode_direct(
        message,
        ep
    )

# ================= SEND EPISODE =================

async def send_episode_direct(
    message: Message,
    ep: str
):

    uid = message.from_user.id

    # ===== BATCH =====

    if "-" in ep:

        try:

            start_str, end_str = ep.split("-")

            start_ep = int(start_str)
            end_ep = int(end_str)

            batch_data = await db.get_batch_range(
                start_ep,
                end_ep
            )

            if not batch_data:

                await message.reply(
                    "❌ No episodes found."
                )

                return

            msg = await message.reply(
                "📤 Sending batch..."
            )

            for ep_num in range(
                start_ep,
                end_ep + 1
            ):

                msg_id = batch_data.get(ep_num)

                if msg_id:

                    try:

                        await message.bot.copy_message(
                            uid,
                            EPISODE_CHANNEL_ID,
                            msg_id
                        )

                        await asyncio.sleep(0.8)

                    except Exception as e:

                        print(
                            f"Failed {ep_num}: {e}"
                        )

                else:

                    await message.reply(
                        f"⚠️ Episode {ep_num} missing."
                    )

            await msg.delete()

        except:

            await message.reply(
                "❌ Invalid batch format."
            )

    # ===== SINGLE =====

    else:

        post = await db.get_post_by_episode(ep)

        if not post:

            await message.reply(
                "❌ Episode not found."
            )

            return

        try:

            msg_id = post.get(
                "episode_msg_id"
            )

            if not msg_id:

                await message.reply(
                    "❌ Video not found."
                )

                return

            await message.bot.copy_message(
                uid,
                EPISODE_CHANNEL_ID,
                msg_id
            )

        except Exception as e:

            await message.reply(
                f"❌ Failed: {e}"
            )

# ================= FORCE SUB =================

async def ask_for_fsub(
    message: Message,
    not_joined: list,
    payload: str
):

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
            url=(
                f"https://t.me/"
                f"{BOT_USERNAME.replace('@','')}"
                f"?start={payload}"
            )
        )
    ])

    await message.reply(
        "❌ <b>Join required channels first!</b>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        ),
        parse_mode="HTML"
    )
