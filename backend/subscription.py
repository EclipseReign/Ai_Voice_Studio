import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from models import Subscription, SubscriptionResponse, User
import paypalrestsdk
from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger(__name__)

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# PayPal Configuration
paypalrestsdk.configure({
    "mode": os.environ.get('PAYPAL_MODE', 'sandbox'),
    "client_id": os.environ['PAYPAL_CLIENT_ID'],
    "client_secret": os.environ['PAYPAL_SECRET']
})

# Constants
FREE_TIER_DAILY_LIMIT = 3

async def get_or_create_subscription(user_id: str) -> Subscription:
    """Get existing subscription or create free tier"""
    try:
        # Check if subscription exists
        sub_doc = await db.subscriptions.find_one({"user_id": user_id})
        
        if sub_doc:
            sub_doc["id"] = str(sub_doc["_id"])
            return Subscription(**sub_doc)
        
        # Create free tier subscription
        sub_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        sub_doc = {
            "_id": sub_id,
            "id": sub_id,
            "user_id": user_id,
            "tier": "free",
            "status": "active",
            "started_at": now,
            "created_at": now,
            "updated_at": now
        }
        
        await db.subscriptions.insert_one(sub_doc)
        
        return Subscription(**sub_doc)
        
    except Exception as e:
        logger.error(f"Error getting/creating subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Error managing subscription")

async def get_usage_count(user_id: str, hours: int = 24) -> int:
    """Get usage count for user in last N hours"""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        count = await db.usage_logs.count_documents({
            "user_id": user_id,
            "created_at": {"$gte": cutoff}
        })
        
        return count
        
    except Exception as e:
        logger.error(f"Error getting usage count: {str(e)}")
        return 0

async def log_usage(user_id: str, action_type: str):
    """Log usage action"""
    try:
        log_id = str(uuid.uuid4())
        
        log_doc = {
            "_id": log_id,
            "id": log_id,
            "user_id": user_id,
            "action_type": action_type,
            "created_at": datetime.now(timezone.utc)
        }
        
        await db.usage_logs.insert_one(log_doc)
        
    except Exception as e:
        logger.error(f"Error logging usage: {str(e)}")

async def check_can_generate(user_id: str) -> dict:
    """Check if user can generate (rate limiting)"""
    try:
        subscription = await get_or_create_subscription(user_id)
        
        # Pro users have unlimited access
        if subscription.tier == "pro" and subscription.status == "active":
            return {
                "can_generate": True,
                "tier": "pro",
                "usage_today": 0,
                "limit": None
            }
        
        # Free users have daily limit
        usage_today = await get_usage_count(user_id, hours=24)
        can_generate = usage_today < FREE_TIER_DAILY_LIMIT
        
        return {
            "can_generate": can_generate,
            "tier": "free",
            "usage_today": usage_today,
            "limit": FREE_TIER_DAILY_LIMIT
        }
        
    except Exception as e:
        logger.error(f"Error checking generation limit: {str(e)}")
        raise HTTPException(status_code=500, detail="Error checking limits")

async def get_subscription_status(user_id: str) -> SubscriptionResponse:
    """Get full subscription status for user"""
    try:
        subscription = await get_or_create_subscription(user_id)
        usage_info = await check_can_generate(user_id)
        
        return SubscriptionResponse(
            tier=subscription.tier,
            status=subscription.status,
            usage_today=usage_info["usage_today"],
            limit=usage_info["limit"],
            can_generate=usage_info["can_generate"],
            expires_at=subscription.expires_at
        )
        
    except Exception as e:
        logger.error(f"Error getting subscription status: {str(e)}")
        raise HTTPException(status_code=500, detail="Error getting subscription status")

async def create_paypal_subscription(user_id: str, plan_id: str) -> dict:
    """Create PayPal subscription"""
    try:
        # This will be called from frontend after PayPal button approval
        # For now, just upgrade user to pro manually
        # In production, you'd verify PayPal webhook
        
        subscription = await get_or_create_subscription(user_id)
        
        # Update to pro
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=30)
        
        await db.subscriptions.update_one(
            {"_id": subscription.id},
            {
                "$set": {
                    "tier": "pro",
                    "status": "active",
                    "paypal_subscription_id": plan_id,
                    "started_at": now,
                    "expires_at": expires_at,
                    "updated_at": now
                }
            }
        )
        
        logger.info(f"User {user_id} upgraded to Pro via PayPal")
        
        return {
            "success": True,
            "tier": "pro",
            "expires_at": expires_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating PayPal subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing subscription")

async def cancel_subscription(user_id: str) -> dict:
    """Cancel user subscription"""
    try:
        subscription = await get_or_create_subscription(user_id)
        
        if subscription.tier == "free":
            raise HTTPException(status_code=400, detail="Cannot cancel free tier")
        
        now = datetime.now(timezone.utc)
        
        # Update subscription
        await db.subscriptions.update_one(
            {"_id": subscription.id},
            {
                "$set": {
                    "status": "cancelled",
                    "cancelled_at": now,
                    "updated_at": now
                }
            }
        )
        
        # Note: In production, also cancel PayPal subscription via API
        
        logger.info(f"User {user_id} cancelled Pro subscription")
        
        return {
            "success": True,
            "message": "Subscription cancelled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Error cancelling subscription")

async def grant_pro_subscription(user_email: str, duration_months: int = 1) -> dict:
    """Admin: Grant Pro subscription to user by email"""
    try:
        # Find user by email
        user_doc = await db.users.find_one({"email": user_email})
        
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = str(user_doc["_id"])
        
        # Get or create subscription
        subscription = await get_or_create_subscription(user_id)
        
        # Update to pro
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=duration_months * 30)
        
        await db.subscriptions.update_one(
            {"_id": subscription.id},
            {
                "$set": {
                    "tier": "pro",
                    "status": "active",
                    "started_at": now,
                    "expires_at": expires_at,
                    "updated_at": now
                }
            }
        )
        
        logger.info(f"Admin granted Pro to user {user_email} for {duration_months} months")
        
        return {
            "success": True,
            "user_email": user_email,
            "tier": "pro",
            "expires_at": expires_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error granting Pro subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Error granting subscription")

async def revoke_pro_subscription(user_email: str) -> dict:
    """Admin: Revoke Pro subscription from user"""
    try:
        # Find user by email
        user_doc = await db.users.find_one({"email": user_email})
        
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = str(user_doc["_id"])
        
        # Get subscription
        subscription = await get_or_create_subscription(user_id)
        
        if subscription.tier == "free":
            raise HTTPException(status_code=400, detail="User already on free tier")
        
        now = datetime.now(timezone.utc)
        
        # Downgrade to free
        await db.subscriptions.update_one(
            {"_id": subscription.id},
            {
                "$set": {
                    "tier": "free",
                    "status": "active",
                    "expires_at": None,
                    "paypal_subscription_id": None,
                    "cancelled_at": now,
                    "updated_at": now
                }
            }
        )
        
        logger.info(f"Admin revoked Pro from user {user_email}")
        
        return {
            "success": True,
            "user_email": user_email,
            "tier": "free"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking Pro subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Error revoking subscription")
