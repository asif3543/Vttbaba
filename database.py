from supabase import create_client
from config import Config
import asyncio

class Database:
    def __init__(self):
        self.db = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

    async def _execute(self, query):
        """Helper to run Supabase sync queries asynchronously"""
        return await asyncio.to_thread(query.execute)

    # 🔰 POST
    async def create_post(self, message_id, episode_message_id, button_text):
        res = await self._execute(self.db.table("posts").insert({
            "message_id": message_id,
            "file_id": str(episode_message_id),
            "button_text": button_text,
            "type": "single"
        }))
        return res.data[0]["id"] if res.data else None

    async def get_post(self, post_id):
        res = await self._execute(self.db.table("posts").select("*").eq("id", post_id))
        return res.data[0] if res.data else None

    # 🔰 BATCH
    async def create_batch_post(self, start_message_id, end_message_id, range_text):
        res = await self._execute(self.db.table("batch_posts").insert({
            "start_message_id": start_message_id,
            "end_message_id": end_message_id,
            "range": range_text,
            "link": ""
        }))
        return res.data[0]["id"] if res.data else None

    async def get_batch(self, batch_id):
        res = await self._execute(self.db.table("batch_posts").select("*").eq("id", batch_id))
        return res.data[0] if res.data else None

    # 🔰 PREMIUM
    async def add_premium(self, user_id, expiry_date):
        await self._execute(self.db.table("premium_users").upsert({
            "user_id": user_id,
            "expiry_date": str(expiry_date)
        }))

    async def remove_premium(self, user_id):
        await self._execute(self.db.table("premium_users").delete().eq("user_id", user_id))

    async def get_premium(self, user_id):
        res = await self._execute(self.db.table("premium_users").select("*").eq("user_id", user_id))
        return res.data[0] if res.data else None

    async def get_all_premium(self):
        res = await self._execute(self.db.table("premium_users").select("*"))
        return res.data

    # 🔰 CHANNELS & FORCE SUB
    async def get_channels(self):
        res = await self._execute(self.db.table("channels").select("*"))
        return res.data

    async def add_force_channel(self, channel_id, channel_name):
        await self._execute(self.db.table("force_sub_channels").upsert({
            "channel_id": channel_id,
            "channel_name": channel_name
        }))

    async def get_force_channels(self):
        res = await self._execute(self.db.table("force_sub_channels").select("*"))
        return res.data

    # 🔰 SHORTNER
    async def add_shortner(self, name, api_url, api_key):
        await self._execute(self.db.table("shortner_accounts").insert({
            "name": name,
            "api_url": api_url,
            "api_key": api_key
        }))

    async def get_shortners(self):
        res = await self._execute(self.db.table("shortner_accounts").select("*"))
        return res.data

    async def delete_shortner(self, shortner_id):
        await self._execute(self.db.table("shortner_accounts").delete().eq("id", shortner_id))

db = Database()
