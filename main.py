import os

class Config:
    API_ID = int(os.environ.get("API_ID", "0"))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

    # Security Control
    OWNER_ID = 5351848105
    ALLOWED_USERS = [5344078567, 5351848105]

    # Channels & Groups
    STORAGE_CHANNEL = -1003096528862
    ALLOWED_GROUP = -1003899919015

    # Database
    SUPABASE_URL = "https://dxvnreuovwoncgonbggg.supabase.co"
    SUPABASE_KEY = "sb_publishable_jNeOKE9aANf2hVZtEiB9dQ_YCinuxVP"

    # Global State Memory
    STATE = {}
