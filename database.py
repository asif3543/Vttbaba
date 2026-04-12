import random
import string
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, DATABASE_NAME
from datetime import datetime, timedelta
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
        self.tokens = self.db.tokens 

    # ================= ANTI-BYPASS SYSTEM =================
    async def create_verify_token(self, uid: int, post_id: str) -> str:
        await self.tokens.delete_many({"uid": uid}) 
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=15))
        await self.tokens.insert_one({
            "token": token,
            "uid": uid,
            "post_id": post_id,
            "created_at": datetime.utcnow()
        })
        return token

    async def check_verify_token(self, uid: int, token: str):
        data = await self.tokens.find_one({"token": token, "uid": uid})
        if not data: return None
        
        await self.tokens.delete_one({"_id": data["_id"]}) # Delete right after use
        
        if datetime.utcnow() - data["created_at"] > timedelta(hours=24):
            return None
        return data["post_id"]
    # ======================================================

    # ================= UNIQUE ID FINDER ===================
    async def get_post_by_id(self, post_id: str):
        # 1. Pehle strictly String ID check karega (NAYI POSTS)
        p = await self.posts.find_one({"_id": post_id})
        if p: return p
        
        # 2. Agar purani ObjectID hai (Pichli posts)
        try:
            if ObjectId.is_valid(post_id):
                p = await self.posts.find_one({"_id": ObjectId(post_id)})
                if p: return p
        except: pass

        # 3. Agar purana Episode Number hai (PURANE BUTTONS)
        p = await self.posts.find_one({"episode": post_id}, sort=[("created_at", -1)])
        if p: return p
        
        async for post in self.posts.find({"batch_range": {"$exists": True}}, sort=[("created_at", -1)]):
            if "-" in post.get("batch_range", ""):
                s, e = post["batch_range"].split("-")
                try:
                    if int(s) <= int(post_id) <= int(e): return post
                except: pass
        return None
    # ======================================================

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
        if "_id" in old: del old["_id"]
        old.update(data)
        await self.temp.update_one({"_id": user_id}, {"$set": old}, upsert=True)

    async def get_temp(self, user_id: int):
        return await self.temp.find_one({"_id": user_id})

    async def del_temp(self, user_id: int):
        await self.temp.delete_one({"_id": user_id})

    async def get_latest_post(self):
        return await self.posts.find_one(sort=[("created_at", -1)])

    async def get_batch_range(self, start: int, end: int):
        cursor = self.batch_episodes.find({"episode": {"$gte": start, "$lte": end}})
        result = {}
        async for doc in cursor:
            result[doc["episode"]] = {"msg_id": doc["storage_msg_id"], "chat_id": doc.get("chat_id")}
        return result

db = Database()
