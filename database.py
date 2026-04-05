from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, DATABASE_NAME
from datetime import datetime, timedelta
import random

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

    # ---------- Premium ----------
    async def add_premium(self, user_id):
        expiry = datetime.utcnow() + timedelta(days=28)
        await self.users.update_one({"_id": user_id}, {"$set": {"premium": True, "expiry": expiry}}, upsert=True)
        return expiry
    async def remove_premium(self, user_id):
        await self.users.update_one({"_id": user_id}, {"$set": {"premium": False, "banned": True}})
    async def is_premium(self, user_id):
        u = await self.users.find_one({"_id": user_id})
        if not u or not u.get("premium"): return False
        if u["expiry"] < datetime.utcnow():
            await self.users.update_one({"_id": user_id}, {"$set": {"premium": False}})
            return False
        return True
    async def is_banned(self, user_id):
        u = await self.users.find_one({"_id": user_id})
        return u.get("banned", False) if u else False
    async def get_premium_list(self):
        return await self.users.find({"premium": True, "expiry": {"$gt": datetime.utcnow()}}).to_list(100)

    # ---------- Shortner ----------
    async def add_shortner(self, url, api):
        return await self.shortners.insert_one({"url": url, "api": api, "active": True})
    async def remove_shortner(self, sid):
        await self.shortners.delete_one({"_id": sid})
    async def get_shortners(self):
        return await self.shortners.find({"active": True}).to_list(100)
    async def get_random_shortner(self):
        s = await self.get_shortners()
        return random.choice(s) if s else None

    # ---------- Channels (for sending posts) ----------
    async def add_channel(self, cid, name):
        await self.channels.update_one({"_id": cid}, {"$set": {"name": name}}, upsert=True)
    async def get_channels(self):
        return await self.channels.find().to_list(100)

    # ---------- Force Sub ----------
    async def add_fsub(self, cid, name, link):
        await self.fsub.update_one({"_id": cid}, {"$set": {"name": name, "link": link}}, upsert=True)
    async def get_fsub(self):
        return await self.fsub.find().to_list(100)

    # ---------- Temp storage for post creation ----------
    async def save_temp(self, uid, data):
        await self.temp.update_one({"_id": uid}, {"$set": data}, upsert=True)
    async def get_temp(self, uid):
        return await self.temp.find_one({"_id": uid})
    async def del_temp(self, uid):
        await self.temp.delete_one({"_id": uid})

    # ---------- Final post storage ----------
    async def save_post(self, data):
        data["created_at"] = datetime.utcnow()
        return await self.posts.insert_one(data)
    async def get_latest_post(self):
        return await self.posts.find_one(sort=[("created_at", -1)])
    async def get_post_by_episode(self, ep):
        p = await self.posts.find_one({"episode": ep})
        if p: return p
        async for post in self.posts.find({"batch_range": {"$exists": True}}):
            if "-" in post.get("batch_range",""):
                s,e = post["batch_range"].split("-")
                if int(s) <= int(ep) <= int(e): return post
        return None

db = Database()
