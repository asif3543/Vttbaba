from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, DATABASE_NAME
from datetime import datetime, timedelta

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGODB_URL)
        self.db = self.client[DATABASE_NAME]
        
        # Collections
        self.users = self.db.users
        self.shortners = self.db.shortners
        self.channels = self.db.channels
        self.posts = self.db.posts
        self.fsub_channels = self.db.fsub_channels
    
    # ========== USER PREMIUM SYSTEM ==========
    async def add_premium(self, user_id: int):
        expiry = datetime.utcnow() + timedelta(days=28)
        await self.users.update_one(
            {"_id": user_id},
            {"$set": {"is_premium": True, "premium_expiry": expiry, "is_banned": False}},
            upsert=True
        )
        return expiry
    
    async def remove_premium(self, user_id: int):
        await self.users.update_one(
            {"_id": user_id},
            {"$set": {"is_premium": False, "is_banned": True}}
        )
    
    async def is_premium(self, user_id: int) -> bool:
        user = await self.users.find_one({"_id": user_id})
        if not user or not user.get("is_premium"):
            return False
        if user["premium_expiry"] < datetime.utcnow():
            await self.users.update_one({"_id": user_id}, {"$set": {"is_premium": False}})
            return False
        return True
    
    async def show_premium_list(self):
        cursor = self.users.find({"is_premium": True, "premium_expiry": {"$gt": datetime.utcnow()}})
        return await cursor.to_list(length=100)
    
    # ========== SHORTNER ACCOUNTS ==========
    async def add_shortner(self, deskboard_url: str, api_token: str):
        result = await self.shortners.insert_one({
            "deskboard_url": deskboard_url,
            "api_token": api_token,
            "is_active": True
        })
        return result.inserted_id
    
    async def remove_shortner(self, shortner_id: str):
        await self.shortners.delete_one({"_id": shortner_id})
    
    async def get_all_shortners(self):
        cursor = self.shortners.find({"is_active": True})
        return await cursor.to_list(length=100)
    
    # ========== CHANNEL MANAGEMENT ==========
    async def add_channel(self, channel_id: int, channel_name: str):
        await self.channels.update_one(
            {"_id": channel_id},
            {"$set": {"name": channel_name, "is_active": True}},
            upsert=True
        )
    
    async def get_all_channels(self):
        cursor = self.channels.find({"is_active": True})
        return await cursor.to_list(length=100)
    
    async def remove_channel(self, channel_id: int):
        await self.channels.delete_one({"_id": channel_id})
    
    # ========== FORCE SUBSCRIBE CHANNELS ==========
    async def add_fsub_channel(self, channel_id: int, channel_name: str, join_link: str):
        await self.fsub_channels.update_one(
            {"_id": channel_id},
            {"$set": {"name": channel_name, "join_link": join_link}},
            upsert=True
        )
    
    async def get_fsub_channels(self):
        cursor = self.fsub_channels.find()
        return await cursor.to_list(length=100)
    
    async def remove_fsub_channel(self, channel_id: int):
        await self.fsub_channels.delete_one({"_id": channel_id})
    
    # ========== POST STORAGE ==========
    async def save_post(self, episode: str, message_id: int, shortner_link: str = None):
        result = await self.posts.insert_one({
            "episode": episode,
            "storage_message_id": message_id,
            "shortner_link": shortner_link,
            "created_at": datetime.utcnow()
        })
        return result.inserted_id
    
    async def get_post(self, episode: str):
        return await self.posts.find_one({"episode": episode})

# Global database instance
db = Database()
