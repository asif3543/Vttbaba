Enterimport httpx
import uuid
from database import db
from config import Config

# Temporary memory bot ke steps yaad rakhne ke liye
USER_STATE = {}

# === DATABASE FUNCTIONS ===
def add_premium(user_id, days=28):
    db.table("premium_users").insert({"user_id": user_id, "expiry_date": f"now() + interval '{days} days'"}).execute()

def remove_premium(user_id):
    db.table("premium_users").delete().eq("user_id", user_id).execute()

def check_is_premium(user_id):
    res = db.table("premium_users").select("*").eq("user_id", user_id).execute()
    if res.data:
        # Here you can add logic to check expiry date against current time
        return True
    return False

def get_force_sub_channels():
    res = db.table("force_sub_channels").select("*").execute()
    return res.data

def get_saved_channels():
    res = db.table("channels").select("*").execute()
    return res.data

# === SHORTNER LOGIC ===
async def get_short_link(long_url):
    res = db.table("shortner_accounts").select("*").execute()
    if not res.data:
        return long_url # Agar shortner nahi hai to direct de do
    
    # Simple rotation: pehla shortner use kar rahe hain
    shortner = res.data[0]
    api_url = shortner['api_url']
    api_key = shortner['api_key']
    
    try:
        async with httpx.AsyncClient() as client:
            req_url = f"{api_url}?api={api_key}&url={long_url}"
            response = await client.get(req_url)
            data = response.json()
            if data.get("status") == "success" or data.get("status"):
                return data.get("shortenedUrl") or data.get("url")
    except Exception as e:
        print(f"Shortner Error: {e}")
    return long_url

# Security Check
def is_admin(user_id):
    return user_id == Config.OWNER_ID or user_id in Config.ALLOWED_USERS
