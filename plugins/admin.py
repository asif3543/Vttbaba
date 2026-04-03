from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import OWNER_ID, USER_STATE
from database import add_premium, remove_premium, add_shortener, add_force_sub

# --- CANCEL COMMAND TO PREVENT STUCK STATES ---
@Client.on_message(filters.command("cancel") & filters.user(OWNER_ID))
async def cancel_process(client: Client, message: Message):
    if message.from_user.id in USER_STATE:
        del USER_STATE[message.from_user.id]
    await message.reply_text("✅ Process cancelled. Memory cleared.")

# --- ADD PREMIUM ---
@Client.on_message(filters.regex(r"(?i)^/add premium") & filters.user(OWNER_ID) & filters.private)
async def cmd_add_prem(client: Client, message: Message):
    USER_STATE[message.from_user.id] = {"step": "premium_add"}
    await message.reply_text("👤 Send the User ID to add to premium:")

# --- ADD SHORTENER ---
@Client.on_message(filters.regex(r"(?i)^/add shortner account") & filters.user(OWNER_ID) & filters.private)
async def cmd_add_short(client: Client, message: Message):
    USER_STATE[message.from_user.id] = {"step": "shortner_url"}
    await message.reply_text("🔗 Provide Shortener API URL (e.g., https://gplinks.in/api):")

# --- FORCE SUB ---
@Client.on_message(filters.regex(r"(?i)^/force sub") & filters.user(OWNER_ID) & filters.private)
async def cmd_fsub(client: Client, message: Message):
    USER_STATE[message.from_user.id] = {"step": "fsub_input"}
    await message.reply_text("📢 Forward a message from the channel OR send Channel ID (-100...):")

# --- GLOBAL ADMIN TEXT HANDLER (WITH TRY/EXCEPT) ---
@Client.on_message(filters.user(OWNER_ID) & filters.private, group=3)
async def admin_flow(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in USER_STATE: return
    
    step = USER_STATE[user_id].get("step")
    text = message.text.strip() if message.text else ""

    try:
        # PREMIUM ADD LOGIC
        if step == "premium_add" and text:
            try:
                target_id = int(text)
                USER_STATE[user_id]["target_id"] = target_id
                
                btn = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Confirm", callback_data="confirm_premium"), 
                     InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")]
                ])
                await message.reply_text(f"Confirm adding `{target_id}` to premium?", reply_markup=btn)
            except ValueError:
                await message.reply_text("❌ Invalid ID! Please send numbers only or type /cancel.")

        # SHORTENER URL LOGIC
        elif step == "shortner_url" and text.startswith("http"):
            USER_STATE[user_id]["url"] = text
            USER_STATE[user_id]["step"] = "shortner_api"
            await message.reply_text("🔑 Now send the API token:")
            
        # SHORTENER API LOGIC
        elif step == "shortner_api" and text:
            await add_shortener(USER_STATE[user_id]["url"], text)
            await message.reply_text("✅ Shortener account successfully added!")
            del USER_STATE[user_id]

        # FORCE SUB LOGIC (Accepts both Forwarded and Manual ID)
        elif step == "fsub_input":
            if message.forward_from_chat:
                chat = message.forward_from_chat
                await add_force_sub(chat.id, chat.title)
                await message.reply_text(f"✅ Force Join set for: {chat.title}")
                del USER_STATE[user_id]
            elif text:
                try:
                    chat_id = int(text)
                    chat_info = await client.get_chat(chat_id)
                    await add_force_sub(chat_id, chat_info.title)
                    await message.reply_text(f"✅ Force Join set for: {chat_info.title}")
                    del USER_STATE[user_id]
                except ValueError:
                    await message.reply_text("❌ Invalid Input. Send Channel ID or Forward message. Type /cancel to abort.")
                except Exception as e:
                    await message.reply_text(f"❌ Bot must be admin in that channel! Error: {e}")

    except Exception as e:
        del USER_STATE[user_id]
        await message.reply_text(f"❌ An error occurred: {e}\nProcess cancelled.")


# --- INLINE CALLBACK QUERY HANDLER ---
@Client.on_callback_query(filters.regex(r"^(confirm_premium|cancel_action)$"))
async def admin_callbacks(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data

    if data == "cancel_action":
        if user_id in USER_STATE: del USER_STATE[user_id]
        await query.message.edit_text("❌ Process Cancelled.")
    
    elif data == "confirm_premium":
        if user_id in USER_STATE and "target_id" in USER_STATE[user_id]:
            target = USER_STATE[user_id]["target_id"]
            res = await add_premium(target)
            if res is not None:
                await query.message.edit_text(f"✅ Premium added for user: `{target}` (28 Days)")
            else:
                await query.message.edit_text("❌ Failed to update Database.")
            del USER_STATE[user_id]
        else:
            await query.message.edit_text("❌ Session expired.")
