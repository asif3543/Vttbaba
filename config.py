import os

API_ID = int(os.getenv("API_ID", 57785446)) 
API_HASH = os.getenv("API_HASH", "YOUR_API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://dxvnreuovwoncgonbggg.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "YOUR_SUPABASE_KEY")

OWNER_ID = int(os.getenv("OWNER_ID", 5351848105))
ALLOWED_USER = int(os.getenv("ALLOWED_USER", 5344078567))
ALLOWED_GROUP = int(os.getenv("ALLOWED_GROUP", -1003899919015))
STORAGE_CHANNEL_ID = int(os.getenv("STORAGE_CHANNEL_ID", -1003096528862))

# Sirf ye log/groups bot use kar payenge Admin mode me
ADMINS = [OWNER_ID, ALLOWED_USER, ALLOWED_GROUP]
