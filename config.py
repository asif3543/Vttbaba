import os

class Config:
    API_ID = int(os.getenv("API_ID", "0"))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")

    OWNER_ID = 5351848105
    ALLOWED_USERS = [5344078567, 5351848105]

    STORAGE_CHANNEL = -1003096528862
    ALLOWED_GROUP = -1003899919015

    SUPABASE_URL = "https://dxvnreuovwoncgonbggg.supabase.co"
    SUPABASE_KEY = "sb_publishable_jNeOKE9aANf2hVZtEiB9dQ_YCinuxVP"

    # Centralized Dictionary for User States
    STATE = {}
