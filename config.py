import os

class Config:
    # Render se auto fetch hoga
    API_ID = int(os.environ.get("API_ID", "0"))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

    # Hardcoded Database
    SUPABASE_URL = "https://dxvnreuovwoncgonbggg.supabase.co"
    SUPABASE_KEY = "sb_publishable_jNeOKE9aANf2hVZtEiB9dQ_YCinuxVP"

    # Security & Admin Setup
    OWNER_ID = 5351848105
    ALLOWED_USERS = [5344078567, 5351848105]
    ALLOWED_GROUP = -1003899919015

    # Storage Channel (ASI Anime - jaha episodes save honge)
    STORAGE_CHANNEL = -1003143681742
    
    # Port for Render
    PORT = 10000
