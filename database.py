from supabase import create_client
from config import Config
import requests
import logging

logging.basicConfig(level=logging.INFO)

try:
    db = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    print("✅ Supabase Database Connected!")
except Exception as e:
    print(f"❌ DB Failed: {e}")
    db = None

def get_short_link(long_url):
    try:
        res = db.table("shortner_accounts").select("*").execute()
        if not res.data:
            return long_url
            
        shortener = res.data[0]
        api_url = shortener.get("api_url", "https://api.gplinks.com/api")
        api_key = shortener["api_key"]
        
        r = requests.get(api_url, params={"api": api_key, "url": long_url}, timeout=10)
        data = r.json()
        if data.get("status") == "success" or data.get("shortenedUrl"):
            return data["shortenedUrl"]
    except Exception as e:
        print(f"Shortener Error: {e}")
    return long_url
