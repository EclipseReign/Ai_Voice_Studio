import os
import uuid
import logging
import aiosmtplib
import httpx
from fastapi import HTTPException, Request, Depends, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from motor.motor_asyncio import AsyncIOMotorClient
from models import User, UserSession, UserResponse
from dotenv import load_dotenv
from pathlib import Path
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI')
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# Security
security = HTTPBearer(auto_error=False)

async def send_verification_email(email: str, name: str, verification_token: str):
    """Send email verification link"""
    try:
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        verification_link = f"{frontend_url}/verify-email?token={verification_token}"
        
        message = MIMEMultipart("alternative")
        message["Subject"] = "Подтвердите ваш email - AI Voice Studio"
        message["From"] = f"{os.environ.get('FROM_NAME', 'AI Voice Studio')} <{os.environ['FROM_EMAIL']}>"
        message["To"] = email
        
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <h2 style="color: #4F46E5;">Добро пожаловать, {name}!</h2>
              <p>Спасибо за регистрацию в AI Voice Studio.</p>
              <p>Пожалуйста, подтвердите ваш email, нажав на кнопку ниже:</p>
              <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_link}" 
                   style="background-color: #4F46E5; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                  Подтвердить Email
                </a>
              </div>
              <p style="color: #666; font-size: 14px;">
                Или скопируйте эту ссылку в браузер:<br>
                <a href="{verification_link}">{verification_link}</a>
              </p>
              <p style="color: #999; font-size: 12px; margin-top: 30px;">
                Если вы не регистрировались на AI Voice Studio, проигнорируйте это письмо.
              </p>
            </div>
          </body>
        </html>
        """
        
        message.attach(MIMEText(html, "html"))
        
        await aiosmtplib.send(
            message,
            hostname=os.environ['SMTP_HOST'],
            port=int(os.environ['SMTP_PORT']),
            username=os.environ['SMTP_USER'],
            password=os.environ['SMTP_PASSWORD'],
            start_tls=True
        )
        
        logger.info(f"Verification email sent to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending verification email: {str(e)}")
        return False

async def get_google_oauth_url(state: str = None) -> str:
    """Generate Google OAuth authorization URL"""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    
    if state:
        params["state"] = state
    
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

async def exchange_code_for_tokens(code: str) -> Optional[dict]:
    """Exchange authorization code for access token"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": GOOGLE_REDIRECT_URI
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Google token exchange returned {response.status_code}: {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Error exchanging code for tokens: {str(e)}")
        return None

async def get_google_user_info(access_token: str) -> Optional[dict]:
    """Get user information from Google"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Google userinfo returned {response.status_code}")
                return None
                
    except Exception as e:
        logger.error(f"Error fetching Google user info: {str(e)}")
        return None

async def create_or_update_user(user_info: dict) -> User:
    """Create new user or return existing user"""
    try:
        # Check if user exists
        existing_user = await db.users.find_one({"email": user_info["email"]})
        
        if existing_user:
            # Return existing user (don't update data)
            existing_user["id"] = str(existing_user["_id"])
            return User(**existing_user)
        
        # Create new user
        user_id = str(uuid.uuid4())
        verification_token = str(uuid.uuid4())
        
        # Check if user is admin
        is_admin = (user_info["email"] == os.environ.get('ADMIN_EMAIL', ''))
        
        user_doc = {
            "_id": user_id,
            "id": user_id,
            "email": user_info["email"],
            "name": user_info.get("name", user_info["email"]),
            "picture": user_info.get("picture"),
            "is_admin": is_admin,
            "email_verified": user_info.get("verified_email", False),
            "verification_token": verification_token if not user_info.get("verified_email") else None,
            "created_at": datetime.now(timezone.utc)
        }
        
        await db.users.insert_one(user_doc)
        
        # Send verification email only if not verified by Google
        if not user_info.get("verified_email", False):
            await send_verification_email(
                user_info["email"],
                user_info.get("name", user_info["email"]),
                verification_token
            )
        
        user_doc["id"] = user_id
        return User(**user_doc)
        
    except Exception as e:
        logger.error(f"Error creating/updating user: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating user")

async def create_session(user_id: str, session_token: str) -> UserSession:
    """Create a new session in database"""
    try:
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        session_doc = {
            "user_id": user_id,
            "session_token": session_token,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc)
        }
        
        await db.user_sessions.insert_one(session_doc)
        
        return UserSession(**session_doc)
        
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating session")

async def get_user_by_session_token(session_token: str) -> Optional[User]:
    """Get user by session token"""
    try:
        # Find session
        session = await db.user_sessions.find_one({"session_token": session_token})
        
        if not session:
            return None
        
        # Check if session expired
        if session["expires_at"] < datetime.now(timezone.utc):
            await db.user_sessions.delete_one({"session_token": session_token})
            return None
        
        # Get user
        user_doc = await db.users.find_one({"_id": session["user_id"]})
        
        if not user_doc:
            return None
        
        user_doc["id"] = str(user_doc["_id"])
        return User(**user_doc)
        
    except Exception as e:
        logger.error(f"Error getting user by session token: {str(e)}")
        return None

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session_token: Optional[str] = Cookie(default=None)
) -> User:
    """Get current authenticated user (from cookie or Authorization header)"""
    
    # Try cookie first (preferred method)
    token = session_token
    
    # Fallback to Authorization header
    if not token and credentials:
        token = credentials.credentials
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = await get_user_by_session_token(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return user

async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session_token: Optional[str] = Cookie(default=None)
) -> Optional[User]:
    """Get current user or None if not authenticated"""
    try:
        return await get_current_user(request, credentials, session_token)
    except HTTPException:
        return None

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin privileges"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

async def verify_email_token(token: str) -> bool:
    """Verify email verification token"""
    try:
        user_doc = await db.users.find_one({"verification_token": token})
        
        if not user_doc:
            return False
        
        # Update user as verified
        await db.users.update_one(
            {"_id": user_doc["_id"]},
            {
                "$set": {
                    "email_verified": True,
                    "verification_token": None
                }
            }
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Error verifying email token: {str(e)}")
        return False
