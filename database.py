from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, DATABASE_NAME
from datetime import datetime, timedelta
import random

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGODB_URL)
        self.db = self.client[DATABASE_NAME]
        
        # Collections
        self.users = self.db.users
        self.shortners = self.db.shortners
        self.channels = self.db.channels
        self.fsub_channels = self.db.fsub_channels
        self.posts = self.db.posts
        self.temp_posts = self.db.temp_posts
    
    # ==================== USER PREMIUM SYSTEM ====================
    async def add_premium(self, user_id: int):
        expiry = datetime.utcnow() + timedelta(days=28)
        await self.users.update_one(
            {"_id": user_id},
            {"$set": {"premium": True, "premium_expiry": expiry, "banned": False}},
            upsert=True
        )
        return expiry
    
    async def remove_premium(self, user_id: int):
        await self.users.update_one(
            {"_id": user_id},
            {"$set": {"premium": False, "banned": True}}
        )
    
    async def is_premium(self, user_id: int) -> bool:
        user = await self.users.find_one({"_id": user_id})
        if not user or not user.get("premium"):
            return False
        if user["premium_expiry"] < datetime.utcnow():
            await self.users.update_one({"_id": user_id}, {"$set": {"premium": False}})
            return False
        return True
    
    async def is_banned(self, user_id: int) -> bool:
        user = await self.users.find_one({"_id": user_id})
        return user.get("banned", False) if user else False
    
    async def get_premium_list(self):
        cursor = self.users.find({"premium": True, "premium_expiry": {"$gt": datetime.utcnow()}})
        return await cursor.to_list(length=100)
    
    # ==================== SHORTNER SYSTEM ====================
    async def add_shortner(self, deskboard_url: str, api_token: str):
        result = await self.shortners.insert_one({
            "url": deskboard_url,
            "api": api_token,
            "active": True,
            "created_at": datetime.utcnow()
        })
        return str(result.inserted_id)
    
    async def remove_shortner(self, shortner_id: str):
        await self.shortners.delete_one({"_id": shortner_id})
    
    async def get_shortners(self):
        cursor = self.shortners.find({"active": True})
        return await cursor.to_list(length=100)
    
    async def get_random_shortner(self):
        shortners = await self.get_shortners()
        return random.choice(shortners) if shortners else None
    
    # ==================== CHANNELS (where bot sends posts) ====================
    async def add_channel(self, channel_id: int, channel_name: str):
        await self.channels.update_one(
            {"_id": channel_id},
            {"$set": {"name": channel_name, "active": True}},
            upsert=True
        )
    
    async def get_channels(self):
        cursor = self.channels.find({"active": True})
        return await cursor.to_list(length=100)
    
    async def remove_channel(self, channel_id: int):
        await self.channels.delete_one({"_id": channel_id})
    
    # ==================== FORCE SUBSCRIBE CHANNELS ====================
    async def add_fsub_channel(self, channel_id: int, channel_name: str, join_link: str = None):
        await self.fsub_channels.update_one(
            {"_id": channel_id},
            {"$set": {"name": channel_name, "link": join_link or f"https://t.me/{channel_name}"}},
            upsert=True
        )
    
    async def get_fsub_channels(self):
        cursor = self.fsub_channels.find()
        return await cursor.to_list(length=100)
    
    async def remove_fsub_channel(self, channel_id: int):
        await self.fsub_channels.delete_one({"_id": channel_id})
    
    # ==================== TEMP POST STORAGE (during creation) ====================
    async def save_temp_post(self, user_id: int, data: dict):
        await self.temp_posts.update_one(
            {"user_id": user_id},
            {"$set": data},
            upsert=True
        )
    
    async def get_temp_post(self, user_id: int):
        return await self.temp_posts.find_one({"user_id": user_id})
    
    async def delete_temp_post(self, user_id: int):
        await self.temp_posts.delete_one({"user_id": user_id})
    
    # ==================== FINAL POST STORAGE ====================
    async def save_post(self, post_data: dict):
        post_data["created_at"] = datetime.utcnow()
        result = await self.posts.insert_one(post_data)
        return str(result.inserted_id)
    
    async def get_latest_post(self):
        return await self.posts.find_one(sort=[("created_at", -1)])
    
    async def get_post_by_episode(self, episode: str):
        # Check single episode
        post = await self.posts.find_one({"episode": episode})
        if post:
            return post
        
        # Check batch range
        all_posts = await self.posts.find({"batch_range": {"$exists": True}}).to_list(length=100)
        for post in all_posts:
            batch_range = post.get("batch_range", "")
            if "-" in batch_range:
                try:
                    start, end = batch_range.split("-")
                    if int(start) <= int(episode) <= int(end):
                        return post
                except:
                    pass
        return None
    
    # ==================== ADD THIS MISSING FUNCTION ====================
    async def get_post_by_episode(self, episode: str):
        """Get post by episode number (supports batch ranges)"""
        # Check exact episode match
        post = await self.posts.find_one({"episode": episode})
        if post:
            return post
        
        # Check batch range
        async for post in self.posts.find({"batch_range": {"$exists": True}}):
            range_str = post.get("batch_range", "")
            if "-" in range_str:
                try:
                    start, end = range_str.split("-")
                    if int(start) <= int(episode) <= int(end):
                        return post
                except:
                    pass
        return None

db = Database()
