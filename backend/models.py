from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional, Literal
from datetime import datetime

# User Models
class User(BaseModel):
    """User model for authentication"""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    
    id: str
    email: EmailStr
    name: str
    picture: Optional[str] = None
    is_admin: bool = False
    created_at: datetime
    email_verified: bool = False
    verification_token: Optional[str] = None

class UserSession(BaseModel):
    """User session model"""
    model_config = ConfigDict(extra="ignore")
    
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime

# Subscription Models
class Subscription(BaseModel):
    """User subscription model"""
    model_config = ConfigDict(extra="ignore")
    
    id: str
    user_id: str
    tier: Literal["free", "pro"] = "free"
    status: Literal["active", "cancelled", "expired"] = "active"
    paypal_subscription_id: Optional[str] = None
    paypal_payer_id: Optional[str] = None
    started_at: datetime
    expires_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

# Usage tracking
class UsageLog(BaseModel):
    """Usage log for rate limiting"""
    model_config = ConfigDict(extra="ignore")
    
    id: str
    user_id: str
    action_type: Literal["text_generation", "audio_generation"]
    created_at: datetime

# Audio generation with user_id
class AudioGeneration(BaseModel):
    """Audio generation record"""
    model_config = ConfigDict(extra="ignore")
    
    id: str
    user_id: str
    text: str
    audio_url: str
    voice: str
    language: str
    duration: Optional[float] = None
    created_at: datetime

# Request/Response Models
class SessionDataResponse(BaseModel):
    """Response from Emergent Auth session data"""
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    session_token: str

class UserResponse(BaseModel):
    """User response model"""
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    is_admin: bool
    email_verified: bool

class SubscriptionResponse(BaseModel):
    """Subscription status response"""
    tier: Literal["free", "pro"]
    status: Literal["active", "cancelled", "expired"]
    usage_today: int
    limit: Optional[int] = None  # None for pro (unlimited)
    can_generate: bool
    expires_at: Optional[datetime] = None

class PayPalSubscriptionRequest(BaseModel):
    """PayPal subscription creation request"""
    plan_id: str  # Will be created in PayPal dashboard

class AdminGrantProRequest(BaseModel):
    """Admin request to grant Pro subscription"""
    user_email: EmailStr
    duration_months: int = 1

class AdminStatsResponse(BaseModel):
    """Admin statistics response"""
    total_users: int
    free_users: int
    pro_users: int
    total_generations_today: int
    total_generations_all_time: int
