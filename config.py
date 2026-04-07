import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
PORT = int(os.getenv("PORT", 10000))

BOT_USERNAME = os.getenv("BOT_USERNAME", "Leechkun_bot")

OWNER_ID = int(os.getenv("OWNER_ID", 5351848105))
ALLOWED_USERS = [int(x) for x in os.getenv("ALLOWED_USERS", "5344078567").split(",") if x.strip()]

STORAGE_CHANNEL_ID = int(os.getenv("STORAGE_CHANNEL_ID", -1003629012882))

MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME", "telegram_bot")

# Ye secret hash shortner loop aur link bypass rokne ka kaam karega
SECRET_HASH = os.getenv("SECRET_HASH", "kuch_bhi_random_text_daal_do_12345")
