from config import Config
from database import db
import aiohttp
import asyncio

async def generate_short_link(original_url: str):
    """Rotates through shorteners and generates a bypassed short link."""
    accounts = await db.get_shortners()
    if not accounts:
        return original_url

    for acc in accounts:
        try:
            api_url = acc["api_url"]
            api_key = acc["api_key"]
            url = f"{api_url}?api={api_key}&url={original_url}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as res:
                    data = await res.json()
                    if data.get("status") == "success":
                        return data.get("shortenedUrl") or data.get("short")
        except Exception:
            continue
    return original_url

async def send_and_delete(client, chat_id, from_chat_id, message_id):
    """Sends a message and deletes it after 5 minutes (300 sec)."""
    try:
        msg = await client.copy_message(chat_id, from_chat_id, message_id)
        await asyncio.sleep(300)
        await client.delete_messages(chat_id, msg.id)
    except Exception:
        pass
