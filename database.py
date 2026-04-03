import aiohttp
from config import Config

class Database:
    def __init__(self):
        self.base_url = f"{Config.SUPABASE_URL}/rest/v1"
        self.headers = {
            "apikey": Config.SUPABASE_KEY,
            "Authorization": f"Bearer {Config.SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    async def _request(self, method, endpoint, payload=None):
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/{endpoint}"
                async with session.request(method, url, headers=self.headers, json=payload) as resp:
                    if resp.status in [200, 201]:
                        return await resp.json()
                    return []
        except:
            return[]

    # 🔰 POSTS
    async def create_post(self, msg_id, file_id, btn_text):
        data = {"message_id": msg_id, "file_id": str(file_id), "button_text": btn_text, "type": "single"}
        res = await self._request("POST", "posts", data)
        return res[0]["id"] if res else None

    async def get_post(self, post_id):
        res = await self._request("GET", f"posts?id=eq.{post_id}")
        return res[0] if res else None

    # 🔰 BATCH POSTS
    async def create_batch_post(self, start_id, end_id, range_text):
        data = {"start_message_id": start_id, "end_message_id": end_id, "range": range_text, "link": ""}
        res = await self._request("POST", "batch_posts", data)
        return res[0]["id"] if res else None

    async def get_batch(self, batch_id):
        res = await self._request("GET", f"batch_posts?id=eq.{batch_id}")
        return res[0] if res else None

    # 🔰 PREMIUM
    async def add_premium(self, user_id, expiry_date):
        payload = {"user_id": user_id, "expiry_date": str(expiry_date)}
        await self._request("POST", "premium_users?on_conflict=user_id", payload)

    async def remove_premium(self, user_id):
        await self._request("DELETE", f"premium_users?user_id=eq.{user_id}")

    async def get_premium(self, user_id):
        res = await self._request("GET", f"premium_users?user_id=eq.{user_id}")
        return res[0] if res else None

    async def get_all_premium(self):
        return await self._request("GET", "premium_users")

    # 🔰 CHANNELS & FORCE SUB
    async def get_channels(self):
        return await self._request("GET", "channels")

    async def add_force_channel(self, channel_id, channel_name):
        payload = {"channel_id": channel_id, "channel_name": channel_name}
        await self._request("POST", "force_sub_channels?on_conflict=channel_id", payload)
        await self._request("POST", "channels?on_conflict=channel_id", payload)

    async def get_force_channels(self):
        return await self._request("GET", "force_sub_channels")

    # 🔰 SHORTNER
    async def add_shortner(self, name, api_url, api_key):
        payload = {"name": name, "api_url": api_url, "api_key": api_key}
        await self._request("POST", "shortner_accounts", payload)

    async def get_shortners(self):
        return await self._request("GET", "shortner_accounts")

    async def delete_shortner(self, shortner_id):
        await self._request("DELETE", f"shortner_accounts?id=eq.{shortner_id}")

db = Database()
