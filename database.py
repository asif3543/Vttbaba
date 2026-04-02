from supabase import create_client, Client
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase Client Initialize kar rahe hain
try:
    db: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    logger.info("✅ Supabase Database Connected Successfully!")
except Exception as e:
    logger.error(f"❌ Database Connection Failed: {e}")
    db = None
