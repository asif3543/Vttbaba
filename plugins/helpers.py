from database import db
import aiohttp
import asyncio

async def generate_short_link(original_url: str):
    accounts = await db.get_shortners()
    if not accounts: return original_url

    for acc in accounts:
        try:
            url = f"{acc['api_url']}?api={acc['api_key']}&url={original_url}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as res:
                    data = await res.json()
                    if "shortenedUrl" in data: return data["shortenedUrl"]
                    if "short" in data: return data["short"]
        except:
            continue
    return original_url

async def send_and_delete(client, chat_id, from_chat_id, message_id):
    try:
        msg = await client.copy_message(chat_id, from_chat_id, message_id)
        await asyncio.sleep(300) # 5 minutes auto delete
        await client.delete_messages(chat_id, msg.id)
    except:
        pass
