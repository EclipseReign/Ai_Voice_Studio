#!/usr/bin/env python3
"""
Create a test user for testing purposes
"""

import asyncio
import uuid
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path(__file__).parent / "backend"
load_dotenv(ROOT_DIR / '.env')

async def create_test_user():
    """Create a test user and session for testing"""
    
    # MongoDB connection
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    # Test user data
    test_user_id = str(uuid.uuid4())
    test_email = "test@example.com"
    test_name = "Test User"
    session_token = str(uuid.uuid4())
    
    try:
        # Check if test user already exists
        existing_user = await db.users.find_one({"email": test_email})
        
        if existing_user:
            print(f"Test user already exists: {test_email}")
            user_id = existing_user["_id"]  # Don't convert to string here
        else:
            # Create test user
            user_doc = {
                "_id": test_user_id,
                "email": test_email,
                "name": test_name,
                "picture": "",
                "google_id": "test_google_id",
                "is_admin": False,
                "email_verified": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            await db.users.insert_one(user_doc)
            print(f"Created test user: {test_email}")
            user_id = test_user_id
        
        # Create or update session
        session_doc = {
            "user_id": user_id,
            "session_token": session_token,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc).replace(year=2025)  # Long expiry
        }
        
        # Remove existing sessions for this user
        await db.user_sessions.delete_many({"user_id": user_id})
        
        # Insert new session
        await db.user_sessions.insert_one(session_doc)
        
        print(f"Created session token: {session_token}")
        print(f"User ID: {user_id}")
        
        # Create subscription record (free tier)
        subscription_doc = {
            "user_id": user_id,
            "tier": "free",
            "status": "active",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Remove existing subscription
        await db.subscriptions.delete_many({"user_id": user_id})
        await db.subscriptions.insert_one(subscription_doc)
        
        print("Created free subscription")
        
        return session_token, user_id
        
    except Exception as e:
        print(f"Error creating test user: {str(e)}")
        return None, None
    finally:
        client.close()

async def main():
    session_token, user_id = await create_test_user()
    
    if session_token:
        # Save to file for use in tests
        with open('/app/test_session.txt', 'w') as f:
            f.write(session_token)
        
        print(f"\nTest session saved to /app/test_session.txt")
        print(f"Use this session token in your tests: {session_token}")
    else:
        print("Failed to create test user")

if __name__ == "__main__":
    asyncio.run(main())