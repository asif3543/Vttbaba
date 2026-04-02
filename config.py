import os

# Local testing ke liye dotenv (Render pe iski zaroorat nahi padegi auto-fetch hoga)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class Config:
    # Telegram API Details
    API_ID = int(os.environ.get("API_ID", "0"))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    
    # Supabase Database Details
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dxvnreuovwoncgonbggg.supabase.co")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_jNeOKE9aANf2hVZtEiB9dQ_YCinuxVP")
    
    # Security Setup (Owner & Access)
    # Apna Telegram User ID yaha dal dein backup ke liye
    OWNER_ID = int(os.environ.get("OWNER_ID", "5351848105")) 
    
    # Allowed Users ID list (Comma separated)
    ALLOWED_USERS = [int(x) for x in os.environ.get("ALLOWED_USERS", "").split(",") if x.strip()]
    
    # Database Channel ID (Jaha se bot files forward karke uthayega)
    STORAGE_CHANNEL = int(os.environ.get("STORAGE_CHANNEL", "-1000000000000")) 
    
    # Render Keep-Alive Port
    PORT = int(os.environ.get("PORT", "10000"))
