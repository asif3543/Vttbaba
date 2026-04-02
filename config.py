import os

class Config:
    # Render Environment Variables se aayenge
    API_ID = int(os.environ.get("API_ID", "0"))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

    # Hardcoded Database & Keys (Aapki di hui)
    SUPABASE_URL = "https://dxvnreuovwoncgonbggg.supabase.co"
    SUPABASE_KEY = "sb_publishable_jNeOKE9aANf2hVZtEiB9dQ_YCinuxVP"

    # Security Setup
    OWNER_ID = 5351848105
    ALLOWED_USERS = [5344078567]
    ALLOWED_GROUP = -1003899919015 # Apna allowed group ID yaha dal lein agar koi specific hai
    
    # Storage Channel Jaha se files forward hongi
    STORAGE_CHANNEL = -1003143681742
    
    # Render Keep-Alive Port
    PORT = 10000
