import os

# IDs ko safely integer me convert karne ka function
def safe_int(value, default=0):
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return default

API_ID = safe_int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

OWNER_ID = safe_int(os.getenv("OWNER_ID", 0))
ALLOWED_USER = safe_int(os.getenv("ALLOWED_USER", 0))
ALLOWED_GROUP = safe_int(os.getenv("ALLOWED_GROUP", 0))
STORAGE_CHANNEL_ID = safe_int(os.getenv("STORAGE_CHANNEL_ID", 0))

# Ye log bot ko control kar sakte hain
ADMINS = [OWNER_ID, ALLOWED_USER]
if ALLOWED_GROUP != 0:
    ADMINS.append(ALLOWED_GROUP)
