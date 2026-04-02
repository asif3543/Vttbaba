import httpx
from database import db
from config import Config

USER_STATE = {}

# 🔰 SECURITY LOGIC (OWNER, ALLOWED USER, ALLOWED GROUP)
def is_admin(user_id):
    return user_id == Config.OWNER_ID or user_id in Config.ALLOWED_USERS

def check_group_access(chat_id):
    # Agar chat private nahi hai, toh check karo ALLOWED_GROUP hai ya nahi
    return chat_id == Config.ALLOWED_GROUP

# 🔰 DATABASE LOGIC
def add_premium(user_id, days=28):
    db.table("premium_users").insert({"user_id": user_id, "expiry_date": f"now() + interval '{days} days'"}).execute()

def remove_premium(user_id):
    db.table("premium_users").delete().eq("user_id", user_id).execute()

def check_is_premium(user_id):
    res = db.table("premium_users").select("*").eq("user_id", user_id).execute()
    return bool(res.data)

def get_force_sub_channels():
    return db.table("force_sub_channels").select("*").execute().data

def get_saved_channels():
    return db.table("channels").select("*").execute().data

# 🔰 SHORTNER LOGIC
async def get_short_link(long_url):
    res = db.table("shortner_accounts").select("*").execute()
    if not res.data:
        return long_url
    shortner = res.data[0]
    try:
        async with httpx.AsyncClient() as client:
            req_url = f"{shortner['api_url']}?api={shortner['api_key']}&url={long_url}"
            resp = await client.get(req_url)
            data = resp.json()
            return data.get("shortenedUrl", long_url)
    except:
        return long_url
