from supabase import create_client
from config import Config
import uuid

class Database:

    def __init__(self):
        self.db = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

    # ==============================
    # 🔰 POST
    # ==============================
    async def create_post(self, message_id, episode_message_id, number):
        post_id = str(uuid.uuid4())

        self.db.table("posts").insert({
            "id": post_id,
            "message_id": message_id,
            "file_id": str(episode_message_id),
            "button_text": f"Watch Episode {number}",
            "type": "single"
        }).execute()

        return post_id

    async def get_post(self, post_id):
        res = self.db.table("posts").select("*").eq("id", post_id).execute()
        return res.data[0] if res.data else None

    # ==============================
    # 🔰 BATCH
    # ==============================
    async def create_batch_post(self, start_message_id, end_message_id, range):
        post_id = str(uuid.uuid4())

        self.db.table("batch_posts").insert({
            "id": post_id,
            "start_message_id": start_message_id,
            "end_message_id": end_message_id,
            "range": range
        }).execute()

        return post_id

    # ==============================
    # 🔰 PREMIUM
    # ==============================
    async def add_premium(self, user_id, expiry_date):
        self.db.table("premium_users").upsert({
            "user_id": user_id,
            "expiry_date": str(expiry_date)
        }).execute()

    async def remove_premium(self, user_id):
        self.db.table("premium_users").delete().eq("user_id", user_id).execute()

    async def get_premium(self, user_id):
        res = self.db.table("premium_users").select("*").eq("user_id", user_id).execute()
        return res.data[0] if res.data else None

    async def get_all_premium(self):
        res = self.db.table("premium_users").select("*").execute()
        return res.data

    # ==============================
    # 🔰 CHANNELS
    # ==============================
    async def get_channels(self):
        res = self.db.table("channels").select("*").execute()
        return res.data

    async def add_force_channel(self, channel_id, channel_name):
        self.db.table("force_sub_channels").upsert({
            "channel_id": channel_id,
            "channel_name": channel_name
        }).execute()

    async def get_force_channels(self):
        res = self.db.table("force_sub_channels").select("*").execute()
        return res.data

    # ==============================
    # 🔰 SHORTNER (TEMP)
    # ==============================
    async def generate_short_link(self, user_id, post_id):
        return f"https://example.com/{post_id}"


db = Database()
