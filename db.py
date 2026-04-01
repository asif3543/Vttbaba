from supabase import create_client, Client
import config
from datetime import datetime, timedelta

supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

def add_premium_user(user_id):
    valid_until = (datetime.utcnow() + timedelta(days=28)).isoformat()
    data = {"user_id": user_id, "valid_until": valid_until, "added_at": datetime.utcnow().isoformat()}
    # Upsert logic
    supabase.table("premium_users").upsert(data).execute()

def remove_premium_user(user_id):
    supabase.table("premium_users").delete().eq("user_id", user_id).execute()

def check_premium(user_id):
    res = supabase.table("premium_users").select("*").eq("user_id", user_id).execute()
    if res.data:
        valid_until = datetime.fromisoformat(res.data[0]['valid_until'])
        if datetime.utcnow() < valid_until:
            return True
        else:
            remove_premium_user(user_id) # Auto remove expired
    return False

def add_force_sub(channel_id):
    supabase.table("force_sub_channels").upsert({"channel_id": channel_id}).execute()

def get_force_sub_channels():
    res = supabase.table("force_sub_channels").select("channel_id").execute()
    return [int(row['channel_id']) for row in res.data]

def add_shortner(domain, api_key):
    supabase.table("shortners").insert({"shortner_url": domain, "api_key": api_key}).execute()

def get_shortners():
    res = supabase.table("shortners").select("*").execute()
    return res.data

def remove_shortner(shortner_id):
    supabase.table("shortners").delete().eq("id", shortner_id).execute()

def save_post(link_data, button_text):
    data = {"link": link_data, "button_text": button_text}
    res = supabase.table("posts").insert(data).execute()
    return res.data[0]['id'] # Returns UUID

def get_post(post_id):
    res = supabase.table("posts").select("*").eq("id", post_id).execute()
    return res.data[0] if res.data else None
