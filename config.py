import os

# Render Environment Variables
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Supabase Database
SUPABASE_URL = "https://dxvnreuovwoncgonbggg.supabase.co"
SUPABASE_KEY = "sb_publishable_jNeOKE9aANf2hVZtEiB9dQ_YCinuxVP"

# User Settings (As requested)
OWNER_ID = 5351848105
ALLOWED_USERS = [5344078567]
ALLOWED_GROUP = -1003899919015
STORAGE_CHANNEL_ID = -1003096528862

# Merge Owner and Allowed Users for Admin checks
ADMINS = [OWNER_ID] + ALLOWED_USERS
