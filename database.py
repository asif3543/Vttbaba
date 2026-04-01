from supabase import create_client, Client
import config
from datetime import datetime, timedelta

supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

def save_post(link_data, button_text):
    data = {"link": link_data, "button_text": button_text}
    res = supabase.table("posts").insert(data).execute()
    return res.data[0]['id']

def get_post(post_id):
    res = supabase.table("posts").select("*").eq("id", post_id).execute()
    return res.data[0] if res.data else None

def add_premium(user_id):
    expiry = datetime.utcnow() + timedelta(days=28)
    data = {"user_id": user_id, "valid_until": expiry.isoformat()}
    supabase.table("premium_users").upsert(data).execute()

def remove_premium(user_id):
    supabase.table("premium_users").delete().eq("user_id", user_id).execute()

def get_all_premium():
    res = supabase.table("premium_users").select("*").execute()
    return res.data if res.data else []

def is_premium(user_id):
    res = supabase.table("premium_users").select("valid_until").eq("user_id", user_id).execute()
    if res.data:
        valid_until = datetime.fromisoformat(res.data[0]['valid_until'])
        if valid_until > datetime.utcnow():
            return True
        else:
            remove_premium(user_id) # Auto remove after 28 days
    return False

def add_shortner(domain, api_key):
    # Storing domain and key together separated by '|' in shortner_url column
    supabase.table("shortners").insert({"shortner_url": f"{domain}|{api_key}", "user_id": config.OWNER_ID}).execute()

def get_shortners():
    res = supabase.table("shortners").select("*").execute()
    return res.data if res.data else []

def remove_shortner(shortner_id):
    supabase.table("shortners").delete().eq("id", shortner_id).execute()

def add_force_sub(channel_id):
    supabase.table("force_sub_channels").upsert({"channel_id": channel_id}).execute()

def get_force_subs():
    res = supabase.table("force_sub_channels").select("channel_id").execute()
    return [int(x['channel_id']) for x in res.data] if res.data else []

def get_target_channels():
    res = supabase.table("target_channels").select("*").execute()
    return res.data if res.data else []
