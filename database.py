import aiohttp
import uuid
from datetime import datetime, timedelta, timezone
from config import SUPABASE_URL, SUPABASE_KEY

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}
BASE_URL = f"{SUPABASE_URL}/rest/v1"

async def _req(method, endpoint, payload=None):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(method, f"{BASE_URL}/{endpoint}", headers=HEADERS, json=payload) as res:
                if res.status in[200, 201]: return await res.json()
    except: pass
    return[]

# --- POSTS SYSTEM ---
async def add_post(file_id, button_text, post_type="single"):
    post_id = str(uuid.uuid4())[:8]
    data = {"id": post_id, "file_id": str(file_id), "button_text": button_text, "type": post_type}
    await _req("POST", "posts", data)
    return post_id

async def get_post(post_id):
    res = await _req("GET", f"posts?id=eq.{post_id}")
    return res[0] if res else None

# --- BATCH SYSTEM ---
async def add_batch(start_id, end_id, range_text):
    batch_id = str(uuid.uuid4())[:8]
    data = {"id": batch_id, "start_message_id": start_id, "end_message_id": end_id, "range": range_text}
    await _req("POST", "batch_posts", data)
    return batch_id

async def get_batch(batch_id):
    res = await _req("GET", f"batch_posts?id=eq.{batch_id}")
    return res[0] if res else None

# --- PREMIUM SYSTEM ---
async def add_premium(user_id):
    expiry = (datetime.now(timezone.utc) + timedelta(days=28)).isoformat()
    await _req("POST", "premium_users?on_conflict=user_id", {"user_id": user_id, "expiry_date": expiry})

async def remove_premium(user_id):
    await _req("DELETE", f"premium_users?user_id=eq.{user_id}")

async def is_premium(user_id):
    res = await _req("GET", f"premium_users?user_id=eq.{user_id}")
    if res:
        expiry = datetime.fromisoformat(res[0]["expiry_date"])
        if expiry > datetime.now(timezone.utc): return True
        else: await remove_premium(user_id)
    return False

# --- SHORTENER SYSTEM ---
async def add_shortener(name, api_url, api_key):
    await _req("POST", "shortner_accounts", {"name": name, "api_url": api_url, "api_key": api_key})

async def get_shorteners():
    return await _req("GET", "shortner_accounts")

async def remove_shortener(short_id):
    await _req("DELETE", f"shortner_accounts?id=eq.{short_id}")

# --- FORCE SUB SYSTEM ---
async def add_force_sub(channel_id, name):
    await _req("POST", "force_sub_channels?on_conflict=channel_id", {"channel_id": channel_id, "channel_name": name})
    await _req("POST", "channels?on_conflict=channel_id", {"channel_id": channel_id, "channel_name": name})

async def get_force_subs():
    return await _req("GET", "force_sub_channels")

async def get_channels():
    return await _req("GET", "channels")
