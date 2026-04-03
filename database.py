from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY
from datetime import datetime, timedelta
import uuid

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- POSTS SYSTEM ---
def add_post(file_id, button_text, post_type="single"):
    post_id = str(uuid.uuid4())[:8]
    data = {"post_id": post_id, "file_id": file_id, "button_text": button_text, "type": post_type}
    supabase.table("posts").insert(data).execute()
    return post_id

def get_post(post_id):
    res = supabase.table("posts").select("*").eq("post_id", post_id).execute()
    return res.data[0] if res.data else None

# --- BATCH SYSTEM ---
def add_batch(start_id, end_id, range_text):
    batch_id = str(uuid.uuid4())[:8]
    data = {"batch_id": batch_id, "start_file_id": start_id, "end_file_id": end_id, "range_text": range_text}
    supabase.table("batch_posts").insert(data).execute()
    return batch_id

def get_batch(batch_id):
    res = supabase.table("batch_posts").select("*").eq("batch_id", batch_id).execute()
    return res.data[0] if res.data else None

# --- PREMIUM SYSTEM ---
def add_premium(user_id):
    expiry = (datetime.utcnow() + timedelta(days=28)).isoformat()
    supabase.table("premium_users").upsert({"user_id": user_id, "expiry_date": expiry}).execute()

def remove_premium(user_id):
    supabase.table("premium_users").delete().eq("user_id", user_id).execute()

def is_premium(user_id):
    res = supabase.table("premium_users").select("*").eq("user_id", user_id).execute()
    if res.data:
        expiry = datetime.fromisoformat(res.data[0]["expiry_date"])
        if expiry > datetime.utcnow():
            return True
        else:
            remove_premium(user_id) # expired
    return False

# --- SHORTENER SYSTEM ---
def add_shortener(name, api_url, api_key):
    supabase.table("shortner_accounts").insert({"name": name, "api_url": api_url, "api_key": api_key}).execute()

def remove_shortener(short_id):
    supabase.table("shortner_accounts").delete().eq("id", short_id).execute()

def get_shorteners():
    return supabase.table("shortner_accounts").select("*").execute().data

# --- FORCE SUB SYSTEM ---
def add_force_sub(channel_id, name):
    supabase.table("force_sub_channels").upsert({"channel_id": channel_id, "channel_name": name}).execute()

def get_force_subs():
    return supabase.table("force_sub_channels").select("*").execute().data

def get_channels():
    return supabase.table("channels").select("*").execute().data
