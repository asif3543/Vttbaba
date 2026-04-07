from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, DATABASE_NAME
from datetime import datetime, timedelta
import random
from bson import ObjectId

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGODB_URL)
        self.db = self.client[DATABASE_NAME]
        self.users = self.db.users
        self.shortners = self.db.shortners
        self.channels = self.db.channels
        self.fsub = self.db.fsub
        self.posts = self.db.posts
        self.temp = self.db.temp
        self.batch_episodes = self.db.batch_episodes

    async def add_premium(self, user_id: int):
        expiry = datetime.utcnow() + timedelta(days=28)
        await self.users.update_one({"_id": user_id}, {"$set": {"premium": True, "expiry": expiry, "banned": False}}, upsert=True)
        return expiry

    async def remove_premium(self, user_id: int):
        await self.users.update_one({"_id": user_id}, {"$set": {"premium": False, "banned": True}})

    async def is_premium(self, user_id: int) -> bool:
        u = await self.users.find_one({"_id": user_id})
        if not u or not u.get("premium"): return False
        if u["expiry"] < datetime.utcnow():
            await self.users.update_one({"_id": user_id}, {"$set": {"premium": False}})
            return False
        return True

    async def is_banned(self, user_id: int) -> bool:
        u = await self.users.find_one({"_id": user_id})
        return u.get("banned", False) if u else False

    async def get_premium_list(self):
        return await self.users.find({"premium": True, "expiry": {"$gt": datetime.utcnow()}}).to_list(100)

    async def add_shortner(self, url: str, api: str):
        await self.shortners.insert_one({"url": url, "api": api, "active": True})

    async def remove_shortner(self, sid: ObjectId):
        await self.shortners.delete_one({"_id": sid})

    async def get_shortners(self):
        return await self.shortners.find({"active": True}).to_list(100)

    async def add_channel(self, channel_id: int, name: str):
        await self.channels.update_one({"_id": channel_id}, {"$set": {"name": name}}, upsert=True)

    async def get_channels(self):
        return await self.channels.find().to_list(100)

    async def add_fsub(self, channel_id: int, name: str, link: str):
        await self.fsub.update_one({"_id": channel_id}, {"$set": {"name": name, "link": link}}, upsert=True)

    async def get_fsub(self):
        return await self.fsub.find().to_list(100)

    async def save_temp(self, user_id: int, data: dict):
        old = await self.temp.find_one({"_id": user_id}) or {}
        old.update(data)
        await self.temp.update_one({"_id": user_id}, {"$set": old}, upsert=True)

    async def get_temp(self, user_id: int):
        return await self.temp.find_one({"_id": user_id})

    async def del_temp(self, user_id: int):
        await self.temp.delete_one({"_id": user_id})

    async def save_post(self, data: dict):
        data["created_at"] = datetime.utcnow()
        await self.posts.insert_one(data)

    async def get_latest_post(self):
        return await self.posts.find_one(sort=[("created_at", -1)])

    async def get_post_by_episode(self, episode: str):
        p = await self.posts.find_one({"episode": episode})
        if p: return p
        async for post in self.posts.find({"batch_range": {"$exists": True}}):
            if "-" in post.get("batch_range", ""):
                s, e = post["batch_range"].split("-")
                if int(s) <= int(episode) <= int(e):
                    return post
        return None

    # ====== BATCH EPISODES FIX ======
    async def add_batch_episode(self, episode_number: int, storage_msg_id: int, chat_id: int = None):
        data = {"storage_msg_id": storage_msg_id}
        if chat_id:
            data["chat_id"] = chat_id
        await self.batch_episodes.update_one({"episode": episode_number}, {"$set": data}, upsert=True)

    async def get_batch_range(self, start: int, end: int):
        cursor = self.batch_episodes.find({"episode": {"$gte": start, "$lte": end}})
        result = {}
        async for doc in cursor:
            result[doc["episode"]] = {
                "msg_id": doc["storage_msg_id"],
                "chat_id": doc.get("chat_id") # Null for old posts
            }
        return result

db = Database()
