import os

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# 👑 OWNER & ADMIN CONTROLS
OWNER_ID = 5351848105
ADMINS =[5351848105, 5344078567]

# 📺 CHANNELS
STORAGE_CHANNEL_ID = -1003096528862
ALLOWED_GROUP = -1003899919015

# 🗄️ SUPABASE DATABASE
SUPABASE_URL = "https://dxvnreuovwoncgonbggg.supabase.co"
SUPABASE_KEY = "sb_publishable_jNeOKE9aANf2hVZtEiB9dQ_YCinuxVP"

# 🧠 MEMORY (सभी प्लगइन्स इसे यूज़ करेंगे)
USER_STATE = {}
