import os

def get_int(key, default=0):
    try: return int(str(os.getenv(key, default)).strip())
    except: return default

API_ID = get_int("API_ID", 57785446)
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

OWNER_ID = get_int("OWNER_ID", 5351848105)
ALLOWED_USER = get_int("ALLOWED_USER", 5344078567)
ALLOWED_GROUP = get_int("ALLOWED_GROUP", -1003899919015)
STORAGE_CHANNEL_ID = get_int("STORAGE_CHANNEL_ID", -1003096528862)

PORT = get_int("PORT", 10000)

# Admins list
ADMINS = [OWNER_ID, ALLOWED_USER, ALLOWED_GROUP]
