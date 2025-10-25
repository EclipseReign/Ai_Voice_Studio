from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, Depends, Response, Request
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal, Dict
import uuid
from datetime import datetime, timezone
import asyncio
import io
from emergentintegrations.llm.chat import LlmChat, UserMessage
import json
import urllib.request
import wave
from piper import PiperVoice
from piper.config import SynthesisConfig
from pydub import AudioSegment
import re
import struct
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

# Import auth and subscription modules
from auth import (
    get_current_user, 
    get_current_user_optional, 
    require_admin,
    get_google_oauth_url,
    exchange_code_for_tokens,
    get_google_user_info,
    create_or_update_user,
    create_session,
    verify_email_token
)
from subscription import (
    get_subscription_status,
    check_can_generate,
    log_usage,
    create_paypal_subscription,
    cancel_subscription,
    grant_pro_subscription,
    revoke_pro_subscription
)
from models import (
    User, 
    UserResponse, 
    SubscriptionResponse, 
    PayPalSubscriptionRequest,
    AdminGrantProRequest,
    AdminStatsResponse
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Piper configuration
PIPER_MODELS_DIR = ROOT_DIR / "piper_models"
PIPER_MODELS_DIR.mkdir(exist_ok=True)
VOICES_CACHE_FILE = PIPER_MODELS_DIR / "voices_cache.json"

# Cache for loaded Piper voices
loaded_voices: Dict[str, PiperVoice] = {}

# Thread pool executor for maximum parallelization (optimized for Railway 8 vCPU)
max_workers = max(multiprocessing.cpu_count() * 2, 16)  # Use 2x CPU cores or minimum 16 threads
executor = ThreadPoolExecutor(max_workers=max_workers)
logger.info(f"Initialized ThreadPoolExecutor with {max_workers} workers")

# ============================================================================
# QUEUE MANAGEMENT SYSTEM (Fair Share with Pro Priority)
# ============================================================================
import time
from dataclasses import dataclass, field
from typing import Dict, List
from collections import defaultdict

@dataclass
class QueueJob:
    """Represents a job in the queue"""
    job_id: str
    user_id: str
    is_pro: bool
    segments_count: int
    start_time: float = field(default_factory=time.time)
    priority_score: float = 0.0
    
    def __post_init__(self):
        # Pro users get 2x priority
        base_priority = 2.0 if self.is_pro else 1.0
        # FIFO: jobs that arrived earlier get slight priority boost
        wait_time_bonus = (time.time() - self.start_time) * 0.01
        self.priority_score = base_priority + wait_time_bonus

class QueueManager:
    """Manages audio generation queue with fair share and priority"""
    def __init__(self, max_concurrent_jobs: int = 3):
        self.max_concurrent_jobs = max_concurrent_jobs
        self.active_jobs: Dict[str, QueueJob] = {}
        self.queue: List[QueueJob] = []
        self.lock = asyncio.Lock()
        self.user_active_jobs: Dict[str, int] = defaultdict(int)
        
    async def add_job(self, job: QueueJob) -> int:
        """Add job to queue and return position"""
        async with self.lock:
            self.queue.append(job)
            # Sort by priority (higher priority first)
            self.queue.sort(key=lambda j: j.priority_score, reverse=True)
            return self.queue.index(job) + 1
    
    async def can_start_job(self, job: QueueJob) -> bool:
        """Check if job can start based on fair share policy"""
        async with self.lock:
            # If under max concurrent limit, allow
            if len(self.active_jobs) < self.max_concurrent_jobs:
                return True
            
            # Fair share: check if this user has fewer active jobs than others
            user_job_count = self.user_active_jobs[job.user_id]
            avg_jobs_per_user = len(self.active_jobs) / max(len(self.user_active_jobs), 1)
            
            # Allow if user has fewer than average jobs
            if user_job_count < avg_jobs_per_user:
                return True
            
            # Pro users can bypass if they have priority
            if job.is_pro and len(self.active_jobs) < self.max_concurrent_jobs * 1.5:
                return True
                
            return False
    
    async def start_job(self, job: QueueJob):
        """Mark job as started"""
        async with self.lock:
            if job in self.queue:
                self.queue.remove(job)
            self.active_jobs[job.job_id] = job
            self.user_active_jobs[job.user_id] += 1
    
    async def finish_job(self, job_id: str):
        """Mark job as finished"""
        async with self.lock:
            if job_id in self.active_jobs:
                job = self.active_jobs.pop(job_id)
                self.user_active_jobs[job.user_id] = max(0, self.user_active_jobs[job.user_id] - 1)
                if self.user_active_jobs[job.user_id] == 0:
                    del self.user_active_jobs[job.user_id]
    
    async def get_queue_position(self, job_id: str) -> Optional[int]:
        """Get position in queue (None if active or not found)"""
        async with self.lock:
            if job_id in self.active_jobs:
                return 0  # Active
            for idx, job in enumerate(self.queue):
                if job.job_id == job_id:
                    return idx + 1
            return None
    
    def get_batch_size_for_user(self, is_pro: bool) -> int:
        """Calculate batch size based on user tier and current load"""
        base_batch = 50 if is_pro else 30  # Pro gets larger batches
        
        # Reduce batch size if many concurrent jobs
        active_count = len(self.active_jobs)
        if active_count > 2:
            base_batch = int(base_batch * 0.7)
        if active_count > 4:
            base_batch = int(base_batch * 0.5)
            
        return max(base_batch, 20)  # Minimum 20

# Global queue manager
queue_manager = QueueManager(max_concurrent_jobs=3)  # 3 concurrent generations for 8 vCPU

# Models
class Voice(BaseModel):
    name: str
    short_name: str
    language: str
    quality: str
    locale: str

class TextGenerateRequest(BaseModel):
    prompt: str
    duration_minutes: int
    language: str = "en-US"
    
class TextGenerateResponse(BaseModel):
    id: str
    text: str
    word_count: int
    estimated_duration: float

class AudioSynthesizeRequest(BaseModel):
    text: str
    voice: str
    rate: float = 1.0  # Speed: 0.5 to 2.0 (1.0 = normal)
    language: str = "en-US"

class AudioSynthesizeResponse(BaseModel):
    id: str
    audio_url: str
    text: str
    voice: str
    created_at: str

class GenerationHistory(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    text: str
    audio_url: Optional[str] = None
    voice: Optional[str] = None
    language: str
    created_at: str

# Helper function to estimate speaking duration
def estimate_duration(text: str, rate: float = 1.0) -> float:
    """Estimate audio duration in seconds. Average: 150 words per minute"""
    words = len(text.split())
    
    # Base: 150 words per minute
    base_minutes = words / 150
    adjusted_minutes = base_minutes / rate
    
    return adjusted_minutes * 60  # Convert to seconds

# Helper function to calculate target word count
def calculate_word_count(duration_minutes: int) -> int:
    """Calculate target word count for desired duration"""
    return duration_minutes * 150  # 150 words per minute

# Helper function to get audio duration from WAV file
def get_audio_duration(wav_path: Path) -> float:
    """Get duration of WAV audio file in seconds"""
    try:
        with wave.open(str(wav_path), 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate)
            return duration
    except Exception as e:
        logger.error(f"Error getting audio duration: {str(e)}")
        return 0.0

# Helper function to generate text chunks
async def generate_text_chunk(
    prompt: str, 
    target_words: int, 
    language: str,
    is_complete: bool = True,
    is_first: bool = True,
    is_last: bool = False,
    previous_content: Optional[str] = None
) -> str:
    """Generate a chunk of text using LLM"""
    
    # For short texts (≤5 minutes = ≤750 words): use EXACT target, no compensation
    # For long texts (>5 minutes): slight compensation (1.1x) because LLM tends to underproduce
    if target_words <= 750:
        adjusted_words = target_words  # No compensation for short texts - be precise!
    else:
        adjusted_words = int(target_words * 1.1)  # Only 10% extra for long texts
    
    # Create LLM chat instance with strict system message
    chat = LlmChat(
        api_key=os.environ.get('EMERGENT_LLM_KEY'),
        session_id=str(uuid.uuid4()),
        system_message="You are a professional narrator and content writer. Create engaging, natural-flowing narration scripts suitable for audio. Write in a continuous narrative style without section headers or labels. IMPORTANT: Write EXACTLY the requested word count - no more, no less. Be precise with length."
    ).with_model("openai", "gpt-4o-mini")
    
    # Build prompt based on chunk position
    if is_complete:
        # Single complete text
        user_prompt = f"""Create a narration script about: {prompt}

CRITICAL REQUIREMENT: Write EXACTLY {adjusted_words} words in {language}. Not more, not less. This is very important for timing.
Style: Natural, conversational narration suitable for audio storytelling.
Write as a continuous narrative without any section labels, headers, or markers like "Introduction", "Conclusion", etc.
Just tell the story or explain the topic in an engaging, flowing way.
Be concise and precise - hit exactly {adjusted_words} words."""
    
    elif is_first:
        # First chunk of multi-part text
        user_prompt = f"""Begin a narration script about: {prompt}

This is the opening of a longer narration. Write EXACTLY {adjusted_words} words in {language}.
Style: Natural, conversational narration suitable for audio.
Start the story/topic naturally without labels like "Introduction".
Write in a continuous narrative flow that will continue in the next part.
End at a natural pause point, but don't conclude the topic.
Be precise - exactly {adjusted_words} words."""
    
    elif is_last:
        # Last chunk
        context_preview = previous_content[-500:] if previous_content and len(previous_content) > 500 else previous_content
        user_prompt = f"""Continue and conclude the narration about: {prompt}

Previous content ended with: "...{context_preview}"

Write EXACTLY {adjusted_words} words in {language} to conclude this narration.
Continue naturally from where the previous part ended.
Wrap up the topic naturally without using labels like "Conclusion" or "In conclusion".
Just bring the narrative to a natural, satisfying end.
Be precise - exactly {adjusted_words} words."""
    
    else:
        # Middle chunk
        context_preview = previous_content[-500:] if previous_content and len(previous_content) > 500 else previous_content
        user_prompt = f"""Continue the narration about: {prompt}

Previous content ended with: "...{context_preview}"

Write EXACTLY {adjusted_words} words in {language} to continue this narration.
Continue naturally from where the previous part ended.
Maintain the same tone and style.
End at a natural pause point, but don't conclude - there's more to come.
Be precise - exactly {adjusted_words} words."""
    
    # Generate text
    user_message = UserMessage(text=user_prompt)
    response = await chat.send_message(user_message)
    
    return response.strip()

# Piper helper functions
async def fetch_available_voices() -> Dict:
    """Fetch available Piper voices from HuggingFace"""
    try:
        if VOICES_CACHE_FILE.exists():
            with open(VOICES_CACHE_FILE, 'r') as f:
                return json.load(f)
        
        url = "https://huggingface.co/rhasspy/piper-voices/raw/main/voices.json"
        with urllib.request.urlopen(url, timeout=10) as response:
            voices_data = json.loads(response.read())
        
        # Cache the data
        with open(VOICES_CACHE_FILE, 'w') as f:
            json.dump(voices_data, f)
        
        return voices_data
    except Exception as e:
        logger.error(f"Error fetching voices: {e}")
        return {}

async def download_voice_model(voice_key: str, voices_data: Dict) -> tuple[Path, Path]:
    """Download a Piper voice model and config if not already present"""
    try:
        voice_info = voices_data.get(voice_key)
        if not voice_info:
            raise ValueError(f"Voice {voice_key} not found")
        
        # Find .onnx and .onnx.json files in the files dict
        model_file_path = None
        config_file_path = None
        
        for file_path in voice_info['files'].keys():
            if file_path.endswith('.onnx.json'):
                config_file_path = file_path
            elif file_path.endswith('.onnx'):
                model_file_path = file_path
        
        if not model_file_path or not config_file_path:
            raise ValueError(f"Model or config file not found for {voice_key}")
        
        # Construct URLs
        model_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{model_file_path}"
        config_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{config_file_path}"
        
        model_path = PIPER_MODELS_DIR / f"{voice_key}.onnx"
        config_path = PIPER_MODELS_DIR / f"{voice_key}.onnx.json"
        
        # Download if not exists
        if not model_path.exists():
            logger.info(f"Downloading model for {voice_key}...")
            urllib.request.urlretrieve(model_url, model_path)
            logger.info(f"Model downloaded: {model_path}")
        
        if not config_path.exists():
            logger.info(f"Downloading config for {voice_key}...")
            urllib.request.urlretrieve(config_url, config_path)
            logger.info(f"Config downloaded: {config_path}")
        
        return model_path, config_path
    except Exception as e:
        logger.error(f"Error downloading voice model: {e}")
        raise

def get_or_load_voice(voice_key: str, model_path: Path, config_path: Path) -> PiperVoice:
    """Get a cached voice or load it"""
    if voice_key not in loaded_voices:
        logger.info(f"Loading voice: {voice_key}")
        loaded_voices[voice_key] = PiperVoice.load(str(model_path), str(config_path))
    return loaded_voices[voice_key]

@api_router.get("/")
async def root():
    return {"message": "Text-to-Speech API"}

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@api_router.get("/auth/google")
async def google_login():
    """Initiate Google OAuth flow"""
    try:
        auth_url = await get_google_oauth_url()
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error(f"Error initiating Google OAuth: {str(e)}")
        raise HTTPException(status_code=500, detail="OAuth initialization error")

@api_router.get("/auth/google/callback")
async def google_callback(code: str, response: Response):
    """Handle Google OAuth callback"""
    try:
        # Exchange code for tokens
        tokens = await exchange_code_for_tokens(code)
        
        if not tokens or "access_token" not in tokens:
            raise HTTPException(status_code=401, detail="Failed to get access token")
        
        # Get user info from Google
        user_info = await get_google_user_info(tokens["access_token"])
        
        if not user_info or "email" not in user_info:
            raise HTTPException(status_code=401, detail="Failed to get user info")
        
        # Create or get user
        user = await create_or_update_user(user_info)
        
        # Create session in our database
        session_token = str(uuid.uuid4())
        await create_session(user.id, session_token)
        
        # Set httpOnly cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="none",
            max_age=7 * 24 * 60 * 60,  # 7 days
            path="/"
        )
        
        logger.info(f"User {user.email} authenticated successfully via Google")
        
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
            "session_token": session_token
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Google callback: {str(e)}")
        raise HTTPException(status_code=500, detail="Authentication error")

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        picture=current_user.picture,
        is_admin=current_user.is_admin,
        email_verified=current_user.email_verified
    )

@api_router.post("/auth/logout")
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    session_token: Optional[str] = None
):
    """Logout user"""
    try:
        # Delete session from database
        if session_token:
            await db.user_sessions.delete_one({"session_token": session_token})
        
        # Clear cookie
        response.delete_cookie(key="session_token", path="/")
        
        return {"success": True, "message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        raise HTTPException(status_code=500, detail="Logout error")

@api_router.get("/auth/verify-email")
async def verify_email(token: str):
    """Verify user email with token"""
    try:
        success = await verify_email_token(token)
        
        if not success:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")
        
        return {"success": True, "message": "Email verified successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying email: {str(e)}")
        raise HTTPException(status_code=500, detail="Verification error")

# ============================================================================
# SUBSCRIPTION ENDPOINTS
# ============================================================================

@api_router.get("/subscription/status", response_model=SubscriptionResponse)
async def get_subscription(current_user: User = Depends(get_current_user)):
    """Get current user's subscription status"""
    return await get_subscription_status(current_user.id)

@api_router.post("/subscription/create")
async def create_subscription(
    request: PayPalSubscriptionRequest,
    current_user: User = Depends(get_current_user)
):
    """Create Pro subscription via PayPal"""
    try:
        result = await create_paypal_subscription(current_user.id, request.plan_id)
        return result
    except Exception as e:
        logger.error(f"Error creating subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing subscription")

@api_router.post("/subscription/cancel")
async def cancel_user_subscription(current_user: User = Depends(get_current_user)):
    """Cancel Pro subscription"""
    return await cancel_subscription(current_user.id)

# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@api_router.get("/admin/users")
async def get_all_users(
    skip: int = 0,
    limit: int = 50,
    admin_user: User = Depends(require_admin)
):
    """Get all users (admin only)"""
    try:
        users_cursor = db.users.find().skip(skip).limit(limit).sort("created_at", -1)
        users = []
        
        async for user_doc in users_cursor:
            user_doc["id"] = str(user_doc["_id"])
            
            # Get subscription info
            sub_doc = await db.subscriptions.find_one({"user_id": user_doc["id"]})
            tier = sub_doc.get("tier", "free") if sub_doc else "free"
            
            users.append({
                "id": user_doc["id"],
                "email": user_doc["email"],
                "name": user_doc["name"],
                "tier": tier,
                "email_verified": user_doc.get("email_verified", False),
                "created_at": user_doc["created_at"].isoformat()
            })
        
        return {"users": users, "total": await db.users.count_documents({})}
        
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching users")

@api_router.get("/admin/stats", response_model=AdminStatsResponse)
async def get_admin_stats(admin_user: User = Depends(require_admin)):
    """Get admin statistics"""
    try:
        # Count users
        total_users = await db.users.count_documents({})
        
        # Count by subscription tier
        pro_users = await db.subscriptions.count_documents({"tier": "pro", "status": "active"})
        free_users = total_users - pro_users
        
        # Count generations
        total_generations = await db.audio_generations.count_documents({})
        
        # Generations today
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        generations_today = await db.usage_logs.count_documents({
            "created_at": {"$gte": today_start}
        })
        
        return AdminStatsResponse(
            total_users=total_users,
            free_users=free_users,
            pro_users=pro_users,
            total_generations_today=generations_today,
            total_generations_all_time=total_generations
        )
        
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching statistics")

@api_router.post("/admin/grant-pro")
async def admin_grant_pro(
    request: AdminGrantProRequest,
    admin_user: User = Depends(require_admin)
):
    """Grant Pro subscription to user"""
    return await grant_pro_subscription(request.user_email, request.duration_months)

@api_router.post("/admin/revoke-pro")
async def admin_revoke_pro(
    user_email: str,
    admin_user: User = Depends(require_admin)
):
    """Revoke Pro subscription from user"""
    return await revoke_pro_subscription(user_email)

# ============================================================================
# TEXT & AUDIO GENERATION ENDPOINTS (Updated with auth)
# ============================================================================

@api_router.get("/voices", response_model=List[Voice])
async def get_voices():
    """Get available voices from Piper"""
    try:
        voices_data = await fetch_available_voices()
        
        # Priority languages mapping
        lang_map = {
            'en': 'en-US',
            'ru': 'ru-RU',
            'es': 'es-ES',
            'fr': 'fr-FR',
            'de': 'de-DE',
            'it': 'it-IT',
            'pt': 'pt-BR',
            'zh': 'zh-CN',
            'ja': 'ja-JP',
            'ko': 'ko-KR',
            'ar': 'ar-SA',
            'hi': 'hi-IN'
        }
        
        filtered_voices = []
        
        for voice_key in sorted(voices_data.keys()):
            # Extract language code
            lang_code = voice_key.split('_')[0]
            
            # Only include priority languages
            if lang_code in lang_map:
                voice_info = voices_data[voice_key]
                
                # Get quality from voice_info
                quality = voice_info.get('quality', 'medium')
                
                # Extract voice name from key (e.g., en_US-lessac-medium -> Lessac)
                voice_name = voice_info.get('name', voice_key.split('-')[1] if '-' in voice_key else voice_key)
                voice_name = voice_name.capitalize()
                
                # Get full locale from voice_key (e.g., en_US -> en-US)
                locale_parts = voice_key.split('-')[0].replace('_', '-')
                
                filtered_voices.append(Voice(
                    name=f"{voice_name} ({quality})",
                    short_name=voice_key,
                    language=voice_info.get('language', {}).get('name_english', lang_code.upper()),
                    quality=quality,
                    locale=locale_parts
                ))
        
        return filtered_voices[:100]  # Limit to 100 voices
    except Exception as e:
        logger.error(f"Error fetching voices: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching voices: {str(e)}")

# Text generation with progress tracking via SSE
@api_router.get("/text/generate-with-progress")
async def generate_text_with_progress(
    prompt: str,
    duration_minutes: int,
    language: str = "en-US",
    current_user: User = Depends(get_current_user)
):
    """Generate text with real-time progress updates via SSE (requires auth)"""
    
    async def generate_progress():
        try:
            # Check if user can generate
            can_generate_info = await check_can_generate(current_user.id)
            
            if not can_generate_info["can_generate"]:
                error_msg = f'Достигнут дневной лимит ({can_generate_info["limit"]} генераций). Обновитесь до Pro для безлимитного доступа.'
                yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                return
            
            # Log usage
            await log_usage(current_user.id, "text_generation")
            
            text_id = str(uuid.uuid4())
            target_words = calculate_word_count(duration_minutes)
            chunk_size = 1200
            
            info_msg = f'Генерация текста ({target_words} слов)'
            yield f"data: {json.dumps({'type': 'info', 'message': info_msg, 'progress': 0})}\n\n"
            
            if target_words <= chunk_size:
                # Short text
                yield f"data: {json.dumps({'type': 'progress', 'progress': 50, 'message': 'Генерация текста...'})}\n\n"
                
                generated_text = await generate_text_chunk(
                    prompt, 
                    target_words, 
                    language, 
                    is_complete=True
                )
                
                yield f"data: {json.dumps({'type': 'progress', 'progress': 100, 'message': 'Текст готов'})}\n\n"
            else:
                # Long text with chunks
                num_chunks = (target_words + chunk_size - 1) // chunk_size
                chunks = []
                
                yield f"data: {json.dumps({'type': 'info', 'message': f'Генерация {num_chunks} частей', 'progress': 0})}\n\n"
                
                for i in range(num_chunks):
                    remaining_words = target_words - sum(len(chunk.split()) for chunk in chunks)
                    chunk_words = min(chunk_size, remaining_words)
                    
                    if chunk_words <= 0:
                        break
                    
                    is_first = (i == 0)
                    is_last = (i == num_chunks - 1)
                    
                    chunk_text = await generate_text_chunk(
                        prompt,
                        chunk_words,
                        language,
                        is_complete=False,
                        is_first=is_first,
                        is_last=is_last,
                        previous_content=" ".join(chunks) if chunks else None
                    )
                    
                    chunks.append(chunk_text)
                    progress = int(((i + 1) / num_chunks) * 100)
                    
                    yield f"data: {json.dumps({'type': 'progress', 'progress': progress, 'message': f'Часть {i+1}/{num_chunks}'})}\n\n"
                
                generated_text = " ".join(chunks)
            
            word_count = len(generated_text.split())
            estimated_duration = estimate_duration(generated_text)
            
            # Save to database
            generation_doc = {
                "id": text_id,
                "user_id": current_user.id,
                "text": generated_text,
                "prompt": prompt,
                "language": language,
                "word_count": word_count,
                "duration_minutes": duration_minutes,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.text_generations.insert_one(generation_doc)
            
            # Send completion
            yield f"data: {json.dumps({'type': 'complete', 'progress': 100, 'text_id': text_id, 'text': generated_text, 'word_count': word_count, 'estimated_duration': estimated_duration})}\n\n"
            
        except Exception as e:
            logger.error(f"Error in SSE text generation: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(generate_progress(), media_type="text/event-stream")

@api_router.post("/text/generate", response_model=TextGenerateResponse)
async def generate_text(request: TextGenerateRequest, current_user: User = Depends(get_current_user)):
    """Generate text based on prompt and duration using LLM (requires auth)"""
    try:
        # Check if user can generate
        can_generate_info = await check_can_generate(current_user.id)
        
        if not can_generate_info["can_generate"]:
            raise HTTPException(
                status_code=429, 
                detail=f'Достигнут дневной лимит ({can_generate_info["limit"]} генераций). Обновитесь до Pro для безлимитного доступа.'
            )
        
        # Log usage
        await log_usage(current_user.id, "text_generation")
        
        # Calculate target word count
        target_words = calculate_word_count(request.duration_minutes)
        
        # For long texts, generate in chunks to avoid LLM token limits
        # Each chunk targets ~1200 words (LLM can handle this comfortably)
        chunk_size = 1200
        
        if target_words <= chunk_size:
            # Short text - generate in one go
            generated_text = await generate_text_chunk(
                request.prompt, 
                target_words, 
                request.language, 
                is_complete=True
            )
        else:
            # Long text - generate in multiple chunks
            num_chunks = (target_words + chunk_size - 1) // chunk_size  # Ceiling division
            chunks = []
            
            for i in range(num_chunks):
                # Calculate words for this chunk
                remaining_words = target_words - sum(len(chunk.split()) for chunk in chunks)
                chunk_words = min(chunk_size, remaining_words)
                
                if chunk_words <= 0:
                    break
                
                # Generate chunk
                is_first = (i == 0)
                is_last = (i == num_chunks - 1)
                
                chunk_text = await generate_text_chunk(
                    request.prompt,
                    chunk_words,
                    request.language,
                    is_complete=False,
                    is_first=is_first,
                    is_last=is_last,
                    previous_content=" ".join(chunks) if chunks else None
                )
                
                chunks.append(chunk_text)
                logger.info(f"Generated chunk {i+1}/{num_chunks}: {len(chunk_text.split())} words")
            
            # Combine all chunks
            generated_text = " ".join(chunks)
        
        word_count = len(generated_text.split())
        estimated_duration = estimate_duration(generated_text)
        
        logger.info(f"Generated text: {word_count} words, estimated duration: {estimated_duration:.1f}s")
        
        # Save to database
        text_id = str(uuid.uuid4())
        generation_doc = {
            "id": text_id,
            "user_id": current_user.id,
            "text": generated_text,
            "prompt": request.prompt,
            "language": request.language,
            "word_count": word_count,
            "duration_minutes": request.duration_minutes,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.text_generations.insert_one(generation_doc)
        
        return TextGenerateResponse(
            id=text_id,
            text=generated_text,
            word_count=word_count,
            estimated_duration=estimated_duration
        )
        
    except Exception as e:
        logger.error(f"Error generating text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating text: {str(e)}")

# Helper function to split text into segments
def split_text_into_segments(text: str, max_segment_length: int = 600) -> list:
    """
    Split text into segments by sentences while trying to keep segment lengths reasonable
    Optimized at 600 chars for maximum parallelization on 8 vCPU
    Smaller segments = more parallel tasks = faster generation
    Also adds pauses at punctuation marks for more natural speech
    """
    # Add pauses at punctuation for natural speech rhythm
    # Add longer pause after sentence-ending punctuation (.!?)
    text = re.sub(r'([.!?])\s+', r'\1 ... ', text)  # Add pause after sentences
    # Add shorter pause after commas, semicolons, colons
    text = re.sub(r'([,;:])\s+', r'\1 .. ', text)  # Add pause after internal punctuation
    
    # Split by sentences (periods, exclamation marks, question marks)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    segments = []
    current_segment = ""
    
    for sentence in sentences:
        # If adding this sentence would exceed max length, start a new segment
        if current_segment and len(current_segment) + len(sentence) > max_segment_length:
            segments.append(current_segment.strip())
            current_segment = sentence
        else:
            current_segment += " " + sentence if current_segment else sentence
    
    # Add remaining segment
    if current_segment:
        segments.append(current_segment.strip())
    
    return segments

# Helper function to synthesize a single audio segment (optimized - no voice loading)
async def synthesize_audio_segment_fast(
    text: str,
    voice: PiperVoice,
    rate: float,
    segment_idx: int,
    temp_dir: Path
) -> Path:
    """Synthesize audio for a single text segment using pre-loaded voice"""
    try:
        # Generate audio file path
        segment_file = temp_dir / f"segment_{segment_idx:04d}.wav"
        
        # Synthesize using optimized thread pool
        def synthesize():
            syn_config = SynthesisConfig(
                length_scale=1.0 / rate,
                noise_scale=0.667,
                noise_w_scale=0.8
            )
            
            with wave.open(str(segment_file), 'wb') as wav_out:
                voice.synthesize_wav(text, wav_out, syn_config=syn_config)
        
        # Use shared thread pool executor for better performance
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(executor, synthesize)
        
        return segment_file
        
    except Exception as e:
        logger.error(f"Error synthesizing segment {segment_idx}: {str(e)}")
        raise

# New endpoint with parallel processing and progress tracking
@api_router.post("/audio/synthesize-parallel", response_model=AudioSynthesizeResponse)
async def synthesize_audio_parallel(request: AudioSynthesizeRequest):
    """Synthesize audio from text using parallel processing for faster generation"""
    try:
        audio_id = str(uuid.uuid4())
        audio_dir = Path("/app/backend/audio_files")
        audio_dir.mkdir(exist_ok=True)
        
        # Create temp directory for segments
        temp_dir = audio_dir / f"temp_{audio_id}"
        temp_dir.mkdir(exist_ok=True)
        
        text_length = len(request.text)
        logger.info(f"Starting parallel audio generation for {text_length} characters")
        
        # Load voice once (optimization)
        voices_data = await fetch_available_voices()
        model_path, config_path = await download_voice_model(request.voice, voices_data)
        voice = get_or_load_voice(request.voice, model_path, config_path)
        
        # Split text into segments (using larger segments for better performance)
        segments = split_text_into_segments(request.text)
        logger.info(f"Split text into {len(segments)} segments for parallel processing")
        
        # Generate segments in batches to avoid memory issues
        batch_size = 25  # Process 25 segments at a time (optimized for speed)
        all_segment_files = []
        
        for batch_start in range(0, len(segments), batch_size):
            batch_end = min(batch_start + batch_size, len(segments))
            batch_segments = segments[batch_start:batch_end]
            
            # Generate batch in parallel using pre-loaded voice
            tasks = []
            for idx, segment in enumerate(batch_segments):
                global_idx = batch_start + idx
                task = synthesize_audio_segment_fast(
                    text=segment,
                    voice=voice,
                    rate=request.rate,
                    segment_idx=global_idx,
                    temp_dir=temp_dir
                )
                tasks.append(task)
            
            # Wait for batch to complete
            batch_files = await asyncio.gather(*tasks)
            all_segment_files.extend(batch_files)
            logger.info(f"Batch {batch_start//batch_size + 1} complete: {len(batch_files)} segments")
        
        segment_files = all_segment_files
        logger.info(f"All {len(segment_files)} segments generated, combining...")
        
        # Combine all audio segments into one file
        final_audio = AudioSegment.empty()
        for segment_file in sorted(segment_files):
            segment_audio = AudioSegment.from_wav(str(segment_file))
            final_audio += segment_audio
        
        # Export combined audio
        final_file = audio_dir / f"{audio_id}.wav"
        final_audio.export(str(final_file), format="wav")
        
        logger.info(f"Combined audio saved: {final_file}")
        
        # Clean up temp directory
        for file in temp_dir.glob("*.wav"):
            file.unlink()
        temp_dir.rmdir()
        
        # Save to database
        audio_doc = {
            "id": audio_id,
            "text": request.text,
            "voice": request.voice,
            "rate": request.rate,
            "language": request.language,
            "audio_path": str(final_file),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.audio_generations.insert_one(audio_doc)
        
        return AudioSynthesizeResponse(
            id=audio_id,
            audio_url=f"/audio/download/{audio_id}",
            text=request.text[:100] + "..." if len(request.text) > 100 else request.text,
            voice=request.voice,
            created_at=audio_doc["created_at"]
        )
        
    except Exception as e:
        logger.error(f"Error in parallel audio synthesis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error synthesizing audio: {str(e)}")

# SSE endpoint for audio synthesis with progress tracking
@api_router.post("/audio/synthesize-with-progress")
async def synthesize_audio_with_progress(
    request: AudioSynthesizeRequest,
    current_user: User = Depends(get_current_user)
):
    """Synthesize audio with real-time progress updates via SSE (requires auth)
    Uses POST method to support large texts (up to 1 hour audio) that exceed URL length limits"""
    
    async def generate_progress():
        try:
            # Check if user can generate
            can_generate_info = await check_can_generate(current_user.id)
            
            if not can_generate_info["can_generate"]:
                error_msg = f'Достигнут дневной лимит ({can_generate_info["limit"]} генераций). Обновитесь до Pro для безлимитного доступа.'
                yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                return
            
            # Log usage
            await log_usage(current_user.id, "audio_generation")
            
            audio_id = str(uuid.uuid4())
            BASE_DIR = Path(__file__).resolve().parent
            audio_dir = Path(os.getenv("AUDIO_OUTPUT_DIR", BASE_DIR / "audio_files"))
            audio_dir.mkdir(parents=True, exist_ok=True)
            
            temp_dir = audio_dir / f"temp_{audio_id}"
            temp_dir.mkdir(exist_ok=True)
            
            # Load voice once (optimization)
            yield f"data: {json.dumps({'type': 'info', 'message': 'Загрузка модели голоса...', 'progress': 5})}\n\n"
            voices_data = await fetch_available_voices()
            model_path, config_path = await download_voice_model(request.voice, voices_data)
            voice_obj = get_or_load_voice(request.voice, model_path, config_path)
            
            # Split text into segments (using larger segments for better performance)
            segments = split_text_into_segments(request.text)
            total_segments = len(segments)
            
            yield f"data: {json.dumps({'type': 'info', 'message': f'Разбито на {total_segments} сегментов', 'progress': 10})}\n\n"
            
            # Generate segments in parallel batches (optimized for maximum speed)
            # Process all segments at once for maximum parallelization
            batch_size = max(total_segments, 200)  # Process all segments or at least 200 at a time
            completed_segments = 0
            all_segment_files = []
            
            for batch_start in range(0, total_segments, batch_size):
                batch_end = min(batch_start + batch_size, total_segments)
                batch_segments = segments[batch_start:batch_end]
                
                # Generate batch in parallel using pre-loaded voice
                tasks = []
                for idx, segment in enumerate(batch_segments):
                    global_idx = batch_start + idx
                    task = synthesize_audio_segment_fast(
                        text=segment,
                        voice=voice_obj,
                        rate=request.rate,
                        segment_idx=global_idx,
                        temp_dir=temp_dir
                    )
                    tasks.append(task)
                
                # Wait for batch to complete
                batch_files = await asyncio.gather(*tasks)
                all_segment_files.extend(batch_files)
                
                completed_segments += len(batch_segments)
                progress = int(10 + (completed_segments / total_segments) * 80)  # 10-90% for generation
                
                yield f"data: {json.dumps({'type': 'progress', 'progress': progress, 'message': f'Сегмент {completed_segments}/{total_segments}'})}\n\n"
            
            # Combine segments
            yield f"data: {json.dumps({'type': 'info', 'message': 'Объединение аудио...', 'progress': 90})}\n\n"
            
            final_audio = AudioSegment.empty()
            total_files = len(all_segment_files)
            for idx, segment_file in enumerate(sorted(all_segment_files), 1):
                segment_audio = AudioSegment.from_wav(str(segment_file))
                final_audio += segment_audio
                
                # Progress during combining (90-98%)
                combine_progress = int(90 + (idx / total_files) * 8)
                yield f"data: {json.dumps({'type': 'progress', 'progress': combine_progress, 'message': f'Склейка {idx}/{total_files}'})}\n\n"
            
            yield f"data: {json.dumps({'type': 'info', 'message': 'Сохранение файла...', 'progress': 98})}\n\n"
            
            final_file = audio_dir / f"{audio_id}.wav"
            final_audio.export(str(final_file), format="wav")
            
            # Get real audio duration
            audio_duration = get_audio_duration(final_file)
            
            # Clean up temp files
            for file in temp_dir.glob("*.wav"):
                file.unlink()
            temp_dir.rmdir()
            
            # Save to database
            audio_doc = {
                "id": audio_id,
                "user_id": current_user.id,
                "text": request.text,
                "voice": request.voice,
                "rate": request.rate,
                "language": request.language,
                "audio_path": str(final_file),
                "duration": audio_duration,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.audio_generations.insert_one(audio_doc)
            
            # Send completion
            yield f"data: {json.dumps({'type': 'complete', 'progress': 100, 'audio_id': audio_id, 'audio_url': f'/audio/download/{audio_id}', 'duration': audio_duration})}\n\n"
            
        except Exception as e:
            logger.error(f"Error in SSE audio synthesis: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(generate_progress(), media_type="text/event-stream")

@api_router.post("/audio/synthesize", response_model=AudioSynthesizeResponse)
async def synthesize_audio(request: AudioSynthesizeRequest):
    """Synthesize audio from text using Piper TTS"""
    try:
        # Create unique ID
        audio_id = str(uuid.uuid4())
        
        # Create audio directory if it doesn't exist
        audio_dir = Path("/app/backend/audio_files")
        audio_dir.mkdir(exist_ok=True)
        
        # Generate audio file paths
        wav_file = audio_dir / f"{audio_id}.wav"
        
        text_length = len(request.text)
        logger.info(f"Generating audio for text of length: {text_length} characters with voice: {request.voice}")
        
        # Fetch voices data and download model if needed
        voices_data = await fetch_available_voices()
        model_path, config_path = await download_voice_model(request.voice, voices_data)
        
        # Load or get cached voice
        voice = get_or_load_voice(request.voice, model_path, config_path)
        
        # Synthesize audio
        logger.info(f"Synthesizing with Piper voice: {request.voice}, rate: {request.rate}")
        
        # Run synthesis in thread pool to avoid blocking
        def synthesize():
            # Create synthesis config with speed adjustment
            # length_scale is inverse of speed (higher = slower, lower = faster)
            syn_config = SynthesisConfig(
                length_scale=1.0 / request.rate,  # Convert rate to length_scale
                noise_scale=0.667,
                noise_w_scale=0.8
            )
            
            with wave.open(str(wav_file), 'wb') as wav_out:
                # Synthesize directly to WAV file
                voice.synthesize_wav(request.text, wav_out, syn_config=syn_config)
        
        # Run in thread pool
        await asyncio.to_thread(synthesize)
        
        logger.info(f"Audio file saved: {wav_file}")
        
        # Save to database
        audio_doc = {
            "id": audio_id,
            "text": request.text,
            "voice": request.voice,
            "rate": request.rate,
            "language": request.language,
            "audio_path": str(wav_file),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.audio_generations.insert_one(audio_doc)
        
        return AudioSynthesizeResponse(
            id=audio_id,
            audio_url=f"/audio/download/{audio_id}",
            text=request.text[:100] + "..." if len(request.text) > 100 else request.text,
            voice=request.voice,
            created_at=audio_doc["created_at"]
        )
        
    except Exception as e:
        logger.error(f"Error synthesizing audio: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error synthesizing audio: {str(e)}")

@api_router.get("/audio/download/{audio_id}")
async def download_audio(audio_id: str):
    """Download generated audio file"""
    try:
        # Fetch from database
        audio_doc = await db.audio_generations.find_one({"id": audio_id}, {"_id": 0})
        
        if not audio_doc:
            raise HTTPException(status_code=404, detail="Audio not found")
        
        audio_path = Path(audio_doc["audio_path"])
        
        if not audio_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        # Determine media type based on file extension
        media_type = "audio/wav" if audio_path.suffix == '.wav' else "audio/mpeg"
        
        return FileResponse(
            path=audio_path,
            media_type=media_type,
            filename=f"generated_audio_{audio_id}{audio_path.suffix}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error downloading audio: {str(e)}")

@api_router.get("/history", response_model=List[GenerationHistory])
async def get_history(current_user: User = Depends(get_current_user)):
    """Get generation history for current user"""
    try:
        # Fetch audio generations for current user only, most recent first
        audio_gens = await db.audio_generations.find(
            {"user_id": current_user.id}, {"_id": 0}
        ).sort("created_at", -1).limit(50).to_list(50)
        
        history = []
        for gen in audio_gens:
            history.append(GenerationHistory(
                id=gen["id"],
                text=gen["text"][:100] + "..." if len(gen["text"]) > 100 else gen["text"],
                audio_url=f"/audio/download/{gen['id']}",
                voice=gen.get("voice"),
                language=gen.get("language", "en-US"),
                created_at=gen["created_at"]
            ))
        
        return history
        
    except Exception as e:
        logger.error(f"Error fetching history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()