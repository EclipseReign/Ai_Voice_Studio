import os
import uuid
import logging
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from models import Subscription, SubscriptionResponse, User
import requests
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
PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')
PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
PAYPAL_SECRET = os.environ.get('PAYPAL_SECRET', '')
PAYPAL_WEBHOOK_ID = os.environ.get('PAYPAL_WEBHOOK_ID', '')  # For webhook verification

# PayPal API URLs
if PAYPAL_MODE == 'live':
    PAYPAL_API_URL = 'https://api-m.paypal.com'
else:
    PAYPAL_API_URL = 'https://api-m.sandbox.paypal.com'

# Constants
FREE_TEXT_DAILY_LIMIT = 5  # Free users: 5 text generations per day
FREE_AUDIO_DAILY_LIMIT = 2  # Free users: 2 audio generations per day
FREE_MAX_DURATION_MINUTES = 30  # Free users: max 30 minutes per generation
PRO_PRICE_USD = 19.99  # Pro subscription price in USD
PAYPAL_PLAN_ID = os.environ.get('PAYPAL_PLAN_ID', '')  # Will be created in PayPal dashboard

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

async def get_usage_count(user_id: str, action_type: Optional[str] = None, hours: int = 24) -> int:
    """Get usage count for user in last N hours
    
    Args:
        user_id: User ID
        action_type: Optional filter by action type ('text_generation' or 'audio_generation')
        hours: Number of hours to look back (default 24)
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        query = {
            "user_id": user_id,
            "created_at": {"$gte": cutoff}
        }
        
        if action_type:
            query["action_type"] = action_type
        
        count = await db.usage_logs.count_documents(query)
        
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

async def check_can_generate(user_id: str, action_type: str, duration_minutes: Optional[float] = None) -> dict:
    """Check if user can generate (rate limiting and duration check)
    
    Args:
        user_id: User ID
        action_type: 'text_generation' or 'audio_generation'
        duration_minutes: Duration in minutes (for Free tier limit check)
    """
    try:
        subscription = await get_or_create_subscription(user_id)
        
        # Pro users have unlimited access
        if subscription.tier == "pro" and subscription.status == "active":
            return {
                "can_generate": True,
                "tier": "pro",
                "usage_today": 0,
                "limit": None,
                "reason": None
            }
        
        # Free users have daily limits and duration limits
        if action_type == "text_generation":
            usage_today = await get_usage_count(user_id, action_type="text_generation", hours=24)
            limit = FREE_TEXT_DAILY_LIMIT
            can_generate = usage_today < limit
            reason = f"Вы достигли дневного лимита текстовых генераций ({limit})" if not can_generate else None
        elif action_type == "audio_generation":
            usage_today = await get_usage_count(user_id, action_type="audio_generation", hours=24)
            limit = FREE_AUDIO_DAILY_LIMIT
            can_generate = usage_today < limit
            reason = f"Вы достигли дневного лимита озвучек ({limit})" if not can_generate else None
        else:
            # Unknown action type
            return {
                "can_generate": False,
                "tier": "free",
                "usage_today": 0,
                "limit": 0,
                "reason": "Неизвестный тип операции"
            }
        
        # Check duration limit for Free tier
        if can_generate and duration_minutes is not None and duration_minutes > FREE_MAX_DURATION_MINUTES:
            can_generate = False
            reason = f"Бесплатный тариф: максимум {FREE_MAX_DURATION_MINUTES} минут на генерацию. Обновитесь до Pro для безлимита!"
        
        return {
            "can_generate": can_generate,
            "tier": "free",
            "usage_today": usage_today,
            "limit": limit,
            "reason": reason
        }
        
    except Exception as e:
        logger.error(f"Error checking generation limit: {str(e)}")
        raise HTTPException(status_code=500, detail="Error checking limits")

async def get_subscription_status(user_id: str) -> SubscriptionResponse:
    """Get full subscription status for user"""
    try:
        subscription = await get_or_create_subscription(user_id)
        
        # Get separate usage counts for text and audio
        text_usage_today = await get_usage_count(user_id, action_type="text_generation", hours=24)
        audio_usage_today = await get_usage_count(user_id, action_type="audio_generation", hours=24)
        
        # Pro users
        if subscription.tier == "pro" and subscription.status == "active":
            return SubscriptionResponse(
                tier=subscription.tier,
                status=subscription.status,
                text_usage_today=text_usage_today,
                audio_usage_today=audio_usage_today,
                text_limit=None,
                audio_limit=None,
                can_generate_text=True,
                can_generate_audio=True,
                max_duration_minutes=None,
                expires_at=subscription.expires_at
            )
        
        # Free users
        can_generate_text = text_usage_today < FREE_TEXT_DAILY_LIMIT
        can_generate_audio = audio_usage_today < FREE_AUDIO_DAILY_LIMIT
        
        return SubscriptionResponse(
            tier=subscription.tier,
            status=subscription.status,
            text_usage_today=text_usage_today,
            audio_usage_today=audio_usage_today,
            text_limit=FREE_TEXT_DAILY_LIMIT,
            audio_limit=FREE_AUDIO_DAILY_LIMIT,
            can_generate_text=can_generate_text,
            can_generate_audio=can_generate_audio,
            max_duration_minutes=FREE_MAX_DURATION_MINUTES,
            expires_at=subscription.expires_at
        )
        
    except Exception as e:
        logger.error(f"Error getting subscription status: {str(e)}")
        raise HTTPException(status_code=500, detail="Error getting subscription status")

async def create_paypal_subscription(user_id: str, plan_id: str) -> dict:
    """Create PayPal subscription - DEPRECATED, use approve_paypal_subscription instead"""
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


def get_paypal_access_token() -> str:
    """Get PayPal OAuth access token"""
    try:
        url = f"{PAYPAL_API_URL}/v1/oauth2/token"
        headers = {
            "Accept": "application/json",
            "Accept-Language": "en_US",
        }
        data = {"grant_type": "client_credentials"}
        
        response = requests.post(
            url,
            headers=headers,
            data=data,
            auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET)
        )
        response.raise_for_status()
        
        return response.json()["access_token"]
        
    except Exception as e:
        logger.error(f"Error getting PayPal access token: {str(e)}")
        raise HTTPException(status_code=500, detail="PayPal authentication error")


async def create_paypal_plan() -> dict:
    """Create PayPal subscription plan (call this once to setup)"""
    try:
        access_token = get_paypal_access_token()
        
        url = f"{PAYPAL_API_URL}/v1/billing/plans"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        
        plan_data = {
            "product_id": "PROD-AIVOICE-PRO",  # You need to create product first
            "name": "AI Voice Studio Pro",
            "description": "Безлимитная генерация текста и озвучка с максимальной скоростью",
            "status": "ACTIVE",
            "billing_cycles": [
                {
                    "frequency": {
                        "interval_unit": "MONTH",
                        "interval_count": 1
                    },
                    "tenure_type": "REGULAR",
                    "sequence": 1,
                    "total_cycles": 0,  # 0 means unlimited (recurring)
                    "pricing_scheme": {
                        "fixed_price": {
                            "value": str(PRO_PRICE_USD),
                            "currency_code": "USD"
                        }
                    }
                }
            ],
            "payment_preferences": {
                "auto_bill_outstanding": True,
                "setup_fee": {
                    "value": "0",
                    "currency_code": "USD"
                },
                "setup_fee_failure_action": "CONTINUE",
                "payment_failure_threshold": 3
            }
        }
        
        response = requests.post(url, json=plan_data, headers=headers)
        response.raise_for_status()
        
        plan = response.json()
        logger.info(f"Created PayPal plan: {plan['id']}")
        
        return {
            "success": True,
            "plan_id": plan["id"],
            "name": plan["name"],
            "status": plan["status"]
        }
        
    except Exception as e:
        logger.error(f"Error creating PayPal plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating PayPal plan: {str(e)}")


async def approve_paypal_subscription(user_id: str, subscription_id: str) -> dict:
    """Activate Pro subscription after user approves PayPal subscription
    
    Args:
        user_id: User ID
        subscription_id: PayPal subscription ID from frontend
    """
    try:
        # Verify subscription with PayPal
        access_token = get_paypal_access_token()
        
        url = f"{PAYPAL_API_URL}/v1/billing/subscriptions/{subscription_id}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        paypal_sub = response.json()
        
        # Check if subscription is active
        if paypal_sub["status"] not in ["ACTIVE", "APPROVED"]:
            raise HTTPException(status_code=400, detail="PayPal subscription not active")
        
        # Get payer info
        payer_id = paypal_sub.get("subscriber", {}).get("payer_id", "")
        
        # Update user subscription in database
        subscription = await get_or_create_subscription(user_id)
        
        now = datetime.now(timezone.utc)
        # Set expiration to next billing date
        next_billing_time = paypal_sub.get("billing_info", {}).get("next_billing_time")
        if next_billing_time:
            expires_at = datetime.fromisoformat(next_billing_time.replace('Z', '+00:00'))
        else:
            expires_at = now + timedelta(days=30)
        
        await db.subscriptions.update_one(
            {"_id": subscription.id},
            {
                "$set": {
                    "tier": "pro",
                    "status": "active",
                    "paypal_subscription_id": subscription_id,
                    "paypal_payer_id": payer_id,
                    "started_at": now,
                    "expires_at": expires_at,
                    "updated_at": now
                }
            }
        )
        
        logger.info(f"User {user_id} upgraded to Pro via PayPal subscription {subscription_id}")
        
        return {
            "success": True,
            "tier": "pro",
            "status": "active",
            "expires_at": expires_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving PayPal subscription: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error approving subscription: {str(e)}")

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
