from supabase import create_client, Client
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    db: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    logger.info("✅ Supabase Connected!")
except Exception as e:
    logger.error(f"❌ DB Failed: {e}")
    db = None
