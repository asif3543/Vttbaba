import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
PORT = os.getenv("PORT")

OWNER_ID = int(os.getenv("OWNER_ID", 5351848105))
ALLOWED_USERS = [int(x) for x in os.getenv("ALLOWED_USERS", "5344078567").split(",")]
ALLOWED_GROUPS = [int(x) for x in os.getenv("ALLOWED_GROUPS", "-1003899919015").split(",")]

STORAGE_CHANNEL_ID = int(os.getenv("STORAGE_CHANNEL_ID", -1003096528862))

MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME", "telegram_bot")
