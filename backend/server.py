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
from datetime import datetime, timezone, timedelta
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
import psutil
import time

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

# Cache for loaded Piper voices with LRU eviction (max 2 models ~200MB to prevent OOM)
from collections import OrderedDict

VOICE_MAX_CONCURRENCY = int(os.getenv("VOICE_MAX_CONCURRENCY", "4"))

class VoiceCache:
    """Thread-safe LRU cache for Piper voice models to prevent OOM and race conditions
    
    FIXES:
    1. Added asyncio.Lock for thread-safety when multiple users access same model (cache ops)
    2. Added per-voice SEMAPHORE to limit parallel synthesis on the SAME model
       - Prevents memory spikes when 2+ clients use one voice concurrently
       - Default limit = VOICE_MAX_CONCURRENCY (env, default 4)
    3. Prevents race conditions when multiple users use same voice simultaneously
    """
    def __init__(self, max_size: int = 2):
        self.cache: OrderedDict[str, PiperVoice] = OrderedDict()
        self.max_size = max_size
        self.cache_lock = asyncio.Lock()  # Lock for cache operations (get/put/evict)
        # Per-voice semaphores to CAP concurrency per model
        self.voice_semaphores: Dict[str, asyncio.Semaphore] = {}
        logger.info(f"Initialized VoiceCache with max_size={max_size} models (thread-safe)")
    
    async def get(self, key: str) -> Optional[PiperVoice]:
        """Get voice from cache, moving it to end (most recently used) - THREAD-SAFE"""
        async with self.cache_lock:
            if key in self.cache:
                # Move to end (mark as recently used)
                self.cache.move_to_end(key)
                logger.info(f"Voice cache HIT: {key} (cache size: {len(self.cache)})")
                return self.cache[key]
            logger.info(f"Voice cache MISS: {key}")
            return None
    
    async def put(self, key: str, value: PiperVoice):
        """Add voice to cache, evicting least recently used if cache is full - THREAD-SAFE"""
        async with self.cache_lock:
            if key in self.cache:
                # Already exists, just move to end
                self.cache.move_to_end(key)
                logger.info(f"Voice updated in cache: {key}")
            else:
                # Check if we need to evict
                if len(self.cache) >= self.max_size:
                    # Evict least recently used (first item)
                    evicted_key, evicted_voice = self.cache.popitem(last=False)
                    # Remove semaphore for evicted voice
                    if evicted_key in self.voice_semaphores:
                        del self.voice_semaphores[evicted_key]
                    # Explicitly delete the model to free memory
                    del evicted_voice
                    logger.warning(f"Voice EVICTED from cache (LRU): {evicted_key} - freed memory")
                
                self.cache[key] = value
                # Create semaphore for this voice if missing
                if key not in self.voice_semaphores:
                    self.voice_semaphores[key] = asyncio.Semaphore(VOICE_MAX_CONCURRENCY)
                logger.info(f"Voice LOADED into cache: {key} (cache size: {len(self.cache)}/{self.max_size})")
    
    async def get_voice_semaphore(self, key: str) -> asyncio.Semaphore:
        """Get semaphore for specific voice to limit concurrent synthesis - THREAD-SAFE"""
        async with self.cache_lock:
            if key not in self.voice_semaphores:
                self.voice_semaphores[key] = asyncio.Semaphore(VOICE_MAX_CONCURRENCY)
            return self.voice_semaphores[key]
    
    async def contains(self, key: str) -> bool:
        """Check if voice is in cache - THREAD-SAFE"""
        async with self.cache_lock:
            return key in self.cache
    
    async def clear(self):
        """Clear all voices from cache - THREAD-SAFE"""
        async with self.cache_lock:
            self.cache.clear()
            self.voice_semaphores.clear()
            logger.info("Voice cache cleared")

# ============================================================================
# AUTOMATIC RESOURCE DETECTION (для оптимизации под железо сервера)
# ============================================================================

def get_system_resources():
    """Определяет доступные ресурсы сервера для автоматической оптимизации
    
    Returns:
        dict: {
            'total_ram_gb': float,  # Общая RAM в GB
            'available_ram_gb': float,  # Доступная RAM в GB
            'cpu_count': int,  # Количество CPU cores
            'ram_usage_percent': float  # Процент использования RAM
        }
    """
    memory = psutil.virtual_memory()
    return {
        'total_ram_gb': round(memory.total / (1024**3), 2),
        'available_ram_gb': round(memory.available / (1024**3), 2),
        'cpu_count': multiprocessing.cpu_count(),
        'ram_usage_percent': memory.percent
    }

def calculate_optimal_parameters(resources: dict):
    """Автоматически вычисляет оптимальные параметры на основе доступных ресурсов
    
    Расчеты основаны на:
    - Piper model: ~50-100MB в памяти
    - Segment processing: ~10-20MB per segment в batch
    - ThreadPoolExecutor worker: ~10-20MB overhead
    - Target: минимум 10 одновременных пользователей
    
    Args:
        resources: dict с информацией о ресурсах
    
    Returns:
        dict: {
            'max_concurrent_jobs': int,  # Сколько пользователей одновременно
            'max_workers': int,  # ThreadPoolExecutor workers
            'batch_size_pro': int,  # Batch size для Pro
            'batch_size_free': int,  # Batch size для Free
            'voice_cache_size': int  # Сколько моделей в кэше
        }
    """
    available_ram = resources['available_ram_gb']
    cpu_count = resources['cpu_count']
    
    # Консервативная оценка: используем 60% доступной памяти для безопасности
    usable_ram = available_ram * 0.6
    
    # Расчет на основе памяти:
    # - VoiceCache: 2 модели × 100MB = 200MB
    # - Каждый concurrent job: ~200-300MB в пике (segments в памяти)
    # - ThreadPoolExecutor: workers × 15MB overhead
    
    # Оценка max_concurrent_jobs
    if usable_ram >= 4.0:  # 4+ GB доступно
        max_concurrent_jobs = 12
    elif usable_ram >= 3.0:  # 3-4 GB
        max_concurrent_jobs = 10
    elif usable_ram >= 2.0:  # 2-3 GB
        max_concurrent_jobs = 8
    elif usable_ram >= 1.5:  # 1.5-2 GB
        max_concurrent_jobs = 6
    else:  # < 1.5 GB
        max_concurrent_jobs = 4
    
    # Расчет max_workers (ThreadPoolExecutor)
    # Piper TTS - I/O bound, выигрывает от высокого количества workers
    # Оптимум: 6-8x CPU cores, но ограничен памятью
    ideal_workers = cpu_count * 8
    
    # Ограничение по памяти: 15MB per worker
    max_workers_by_ram = int((usable_ram * 1024 - 200) / 15)  # 200MB для VoiceCache
    max_workers = min(ideal_workers, max_workers_by_ram, 96)  # Cap at 96
    max_workers = max(max_workers, 16)  # Minimum 16 workers
    
    # Расчет batch_size
    # Больше batch = больше параллелизма, но больше памяти
    # Каждый segment в batch: ~15-20MB в памяти
    if usable_ram >= 4.0:
        batch_size_pro = 24
        batch_size_free = 16
    elif usable_ram >= 3.0:
        batch_size_pro = 20
        batch_size_free = 14
    elif usable_ram >= 2.0:
        batch_size_pro = 16
        batch_size_free = 12
    else:
        batch_size_pro = 12
        batch_size_free = 8
    
    # Voice cache size
    # Каждая модель: ~50-100MB
    if usable_ram >= 4.0:
        voice_cache_size = 3
    elif usable_ram >= 2.0:
        voice_cache_size = 2
    else:
        voice_cache_size = 1
    
    return {
        'max_concurrent_jobs': max_concurrent_jobs,
        'max_workers': max_workers,
        'batch_size_pro': batch_size_pro,
        'batch_size_free': batch_size_free,
        'voice_cache_size': voice_cache_size
    }

# Автоматически определяем ресурсы при старте
system_resources = get_system_resources()
optimal_params = calculate_optimal_parameters(system_resources)

logger.info("🖥️ SYSTEM RESOURCES DETECTED:")
logger.info(f"  - Total RAM: {system_resources['total_ram_gb']} GB")
logger.info(f"  - Available RAM: {system_resources['available_ram_gb']} GB")
logger.info(f"  - CPU Cores: {system_resources['cpu_count']}")
logger.info(f"  - RAM Usage: {system_resources['ram_usage_percent']}%")
logger.info("⚙️ OPTIMAL PARAMETERS CALCULATED:")
logger.info(f"  - Max Concurrent Jobs: {optimal_params['max_concurrent_jobs']} users")
logger.info(f"  - ThreadPoolExecutor Workers: {optimal_params['max_workers']}")
logger.info(f"  - Batch Size (Pro): {optimal_params['batch_size_pro']}")
logger.info(f"  - Batch Size (Free): {optimal_params['batch_size_free']}")
logger.info(f"  - Voice Cache Size: {optimal_params['voice_cache_size']} models")

# Initialize VoiceCache with optimal size
loaded_voices = VoiceCache(max_size=optimal_params['voice_cache_size'])
logger.info(f"✅ Initialized VoiceCache with size={optimal_params['voice_cache_size']} models")

# Thread pool executor for parallel audio synthesis (optimized for high concurrency)
# Piper TTS is I/O bound, benefits from high worker count (8x CPU cores)
# Each worker consumes ~10-20MB overhead
# АВТОМАТИЧЕСКИ определяется на основе доступных ресурсов
cpu_count = system_resources['cpu_count']
max_workers = optimal_params['max_workers']
executor = ThreadPoolExecutor(max_workers=max_workers)
logger.info(f"✅ Initialized ThreadPoolExecutor with {max_workers} workers (CPU count: {cpu_count})")

# ============================================================================
# QUEUE MANAGEMENT SYSTEM (Fair Share with Pro Priority)
# Optimized for 10+ concurrent users on 8GB RAM / 8 vCPU
# ============================================================================
from dataclasses import dataclass, field
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
    """Manages audio generation queue with fair share and priority
    Optimized for 10+ concurrent users with memory and CPU constraints"""
    def __init__(self, max_concurrent_jobs: int = 10):
        self.max_concurrent_jobs = max_concurrent_jobs
        self.active_jobs: Dict[str, QueueJob] = {}
        self.queue: List[QueueJob] = []
        self.lock = asyncio.Lock()
        self.user_active_jobs: Dict[str, int] = defaultdict(int)
        self.job_timeout_seconds: int = 3600  # 60 minutes max per job (increased from 15 min)
        
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
        """Dynamic resource allocation with memory-aware batch sizing
        
        АВТОМАТИЧЕСКИ адаптируется под доступные ресурсы сервера
        Использует предварительно рассчитанные optimal_params
        
        Strategy: Adjust batch_size based on concurrent load to prevent OOM
        Pro users get 1.5x boost for faster generation
        """
        active_jobs = list(self.active_jobs.values())
        total_active = len(active_jobs)
        
        # Base batch sizes from automatic resource detection
        if is_pro:
            base_batch = optimal_params['batch_size_pro']
        else:
            base_batch = optimal_params['batch_size_free']
        
        # Снижаем batch при высокой нагрузке для предотвращения OOM
        if total_active <= 1:
            multiplier = 1.0  # Single user: full batch
        elif total_active <= 3:
            multiplier = 0.85  # 2-3 users: 85%
        elif total_active <= 6:
            multiplier = 0.7   # 4-6 users: 70%
        else:
            multiplier = 0.5   # 7+ users: 50% для максимальной безопасности
        
        batch_size = max(6, int(base_batch * multiplier))  # Минимум 6
        
        return batch_size
    
    def is_high_load(self) -> bool:
        """Check if system is under high load (10+ active users)"""
        return len(self.active_jobs) >= 10
    
    def get_active_user_count(self) -> int:
        """Get count of active users"""
        return len(set(job.user_id for job in self.active_jobs.values()))

# Global queue manager - АВТОМАТИЧЕСКИ оптимизируется под доступные ресурсы
queue_manager = QueueManager(max_concurrent_jobs=optimal_params['max_concurrent_jobs'])

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
    # Optional: resume existing unfinished job
    job_id: Optional[str] = None

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

# NEW: Model for generation job state (for recovery after crashes)
class GenerationJob(BaseModel):
    """Tracks audio generation progress for crash recovery"""
    model_config = ConfigDict(extra="ignore")
    job_id: str
    user_id: str
    text: str
    voice: str
    rate: float
    language: str
    status: Literal["pending", "processing", "completed", "failed", "resumable"]
    total_segments: int
    completed_segments: int
    segment_files: List[str] = Field(default_factory=list)  # Paths to generated segments
    temp_dir: str  # Path to temp directory
    created_at: str
    updated_at: str
    error_message: Optional[str] = None

class GenerationJobResponse(BaseModel):
    """Response for generation job queries"""
    job_id: str
    status: str
    completed_segments: int
    total_segments: int
    progress_percent: int
    text_preview: str  # First 100 chars

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

# ============================================================================
# GENERATION JOB MANAGEMENT (For crash recovery and resume functionality)
# ============================================================================

async def create_generation_job(
    user_id: str,
    text: str,
    voice: str,
    rate: float,
    language: str,
    total_segments: int,
    temp_dir: str
) -> str:
    """Create a new generation job in database for crash recovery"""
    job_id = str(uuid.uuid4())
    job_doc = {
        "job_id": job_id,
        "user_id": user_id,
        "text": text,
        "voice": voice,
        "rate": rate,
        "language": language,
        "status": "pending",
        "total_segments": total_segments,
        "completed_segments": 0,
        "segment_files": [],
        "temp_dir": temp_dir,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "error_message": None
    }
    await db.generation_jobs.insert_one(job_doc)
    logger.info(f"Created generation job {job_id} with {total_segments} segments")
    return job_id

async def update_generation_job_progress(
    job_id: str,
    completed_segments: int,
    segment_files: List[str],
    status: str = "processing"
):
    """Update generation job progress after each batch"""
    await db.generation_jobs.update_one(
        {"job_id": job_id},
        {
            "$set": {
                "completed_segments": completed_segments,
                "segment_files": segment_files,
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    logger.info(f"Updated job {job_id}: {completed_segments} segments completed")

async def complete_generation_job(job_id: str, audio_id: str):
    """Mark generation job as completed"""
    await db.generation_jobs.update_one(
        {"job_id": job_id},
        {
            "$set": {
                "status": "completed",
                "audio_id": audio_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    logger.info(f"Completed generation job {job_id}")

async def fail_generation_job(job_id: str, error_message: str):
    """Mark generation job as failed"""
    await db.generation_jobs.update_one(
        {"job_id": job_id},
        {
            "$set": {
                "status": "failed",
                "error_message": error_message,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    logger.error(f"Failed generation job {job_id}: {error_message}")

async def get_pending_jobs(user_id: str) -> List[dict]:
    """Get all pending/processing/resumable jobs for a user"""
    cursor = db.generation_jobs.find({
        "user_id": user_id,
        "status": {"$in": ["pending", "processing", "resumable"]}
    }).sort("created_at", -1)
    return await cursor.to_list(length=10)

async def get_generation_job(job_id: str) -> Optional[dict]:
    """Get specific generation job by ID"""
    return await db.generation_jobs.find_one({"job_id": job_id})

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

async def get_or_load_voice(voice_key: str, model_path: Path, config_path: Path) -> PiperVoice:
    """Get a cached voice or load it with LRU eviction - THREAD-SAFE
    
    FIXES:
    - Now async to work with VoiceCache locks
    - Prevents race conditions when multiple users load same model simultaneously
    """
    voice = await loaded_voices.get(voice_key)
    if voice is None:
        logger.info(f"Loading voice from disk: {voice_key}")
        # Load voice in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        voice = await loop.run_in_executor(None, PiperVoice.load, str(model_path), str(config_path))
        await loaded_voices.put(voice_key, voice)
    return voice

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

@api_router.get("/system/resources")
async def get_system_resources_info():
    """Получить информацию о ресурсах сервера и текущей нагрузке
    
    Публичный endpoint для мониторинга - НЕ требует авторизации
    """
    try:
        # Текущие ресурсы
        current_resources = get_system_resources()
        
        # Информация о настройках
        active_jobs_count = len(queue_manager.active_jobs)
        active_users_count = queue_manager.get_active_user_count()
        
        return {
            "system": {
                "total_ram_gb": current_resources['total_ram_gb'],
                "available_ram_gb": current_resources['available_ram_gb'],
                "ram_usage_percent": current_resources['ram_usage_percent'],
                "cpu_count": current_resources['cpu_count']
            },
            "configured_limits": {
                "max_concurrent_jobs": optimal_params['max_concurrent_jobs'],
                "max_workers": optimal_params['max_workers'],
                "batch_size_pro": optimal_params['batch_size_pro'],
                "batch_size_free": optimal_params['batch_size_free'],
                "voice_cache_size": optimal_params['voice_cache_size']
            },
            "current_load": {
                "active_jobs": active_jobs_count,
                "active_users": active_users_count,
                "is_high_load": queue_manager.is_high_load(),
                "capacity_percent": round((active_jobs_count / optimal_params['max_concurrent_jobs']) * 100, 1)
            },
            "recommendations": {
                "can_handle_more": active_jobs_count < optimal_params['max_concurrent_jobs'],
                "estimated_max_users": optimal_params['max_concurrent_jobs']
            }
        }
    except Exception as e:
        logger.error(f"Error getting system resources: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

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
                # Short text - add intermediate progress updates
                yield f"data: {json.dumps({'type': 'progress', 'progress': 10, 'message': f'Подготовка запроса ({target_words} слов)...'})}\n\n"
                await asyncio.sleep(0.3)  # Small delay for UI update
                
                yield f"data: {json.dumps({'type': 'progress', 'progress': 20, 'message': 'Генерация началась...'})}\n\n"
                await asyncio.sleep(0.2)
                
                yield f"data: {json.dumps({'type': 'progress', 'progress': 40, 'message': 'LLM обрабатывает запрос...'})}\n\n"
                
                generated_text = await generate_text_chunk(
                    prompt, 
                    target_words, 
                    language, 
                    is_complete=True
                )
                
                yield f"data: {json.dumps({'type': 'progress', 'progress': 85, 'message': 'Текст получен, финализация...'})}\n\n"
                await asyncio.sleep(0.2)
                
                yield f"data: {json.dumps({'type': 'progress', 'progress': 95, 'message': 'Сохранение результата...'})}\n\n"
                await asyncio.sleep(0.1)
                
                yield f"data: {json.dumps({'type': 'progress', 'progress': 100, 'message': 'Текст готов!'})}\n\n"
            else:
                # Long text with chunks
                num_chunks = (target_words + chunk_size - 1) // chunk_size
                chunks = []
                
                yield f"data: {json.dumps({'type': 'info', 'message': f'Генерация {num_chunks} частей по ~{chunk_size} слов', 'progress': 5})}\n\n"
                await asyncio.sleep(0.2)
                
                for i in range(num_chunks):
                    remaining_words = target_words - sum(len(chunk.split()) for chunk in chunks)
                    chunk_words = min(chunk_size, remaining_words)
                    
                    if chunk_words <= 0:
                        break
                    
                    is_first = (i == 0)
                    is_last = (i == num_chunks - 1)
                    
                    # Progress update before generating chunk
                    progress_before = int(5 + (i / num_chunks) * 85)  # 5-90% for generation
                    yield f"data: {json.dumps({'type': 'progress', 'progress': progress_before, 'message': f'Генерация части {i+1}/{num_chunks}...'})}\n\n"
                    
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
                    
                    # Progress update after chunk is generated
                    progress_after = int(5 + ((i + 1) / num_chunks) * 85)
                    current_word_count = sum(len(chunk.split()) for chunk in chunks)
                    yield f"data: {json.dumps({'type': 'progress', 'progress': progress_after, 'message': f'Готово {i+1}/{num_chunks} частей ({current_word_count} слов)'})}\n\n"
                
                yield f"data: {json.dumps({'type': 'progress', 'progress': 92, 'message': 'Объединение частей...'})}\n\n"
                generated_text = " ".join(chunks)
                await asyncio.sleep(0.2)
                
                yield f"data: {json.dumps({'type': 'progress', 'progress': 97, 'message': 'Сохранение результата...'})}\n\n"
                await asyncio.sleep(0.1)
            
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
def split_text_into_segments(text: str, max_segment_length: int = 1000) -> list:
    """
    Split text into segments by sentences while trying to keep segment lengths reasonable
    Optimized at 1000 chars (up from 600) for better memory efficiency with 10+ concurrent users
    Larger segments = fewer total segments = less memory overhead during concatenation
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


# Streaming-safe concatenation to avoid loading all segments in memory
# Writes directly to output WAV by appending frames with consistent params
# Falls back to pydub if parameters mismatch
async def concat_wav_files_streaming(segment_files: List[Path], out_path: Path) -> None:
    if not segment_files:
        raise ValueError("No segment files to concatenate")
    try:
        import contextlib
        with contextlib.ExitStack() as stack:
            first = stack.enter_context(wave.open(str(segment_files[0]), 'rb'))
            params = first.getparams()
            with wave.open(str(out_path), 'wb') as out_wav:
                out_wav.setparams(params)
                # write first
                out_wav.writeframes(first.readframes(first.getnframes()))
                # append others
                for seg in segment_files[1:]:
                    wf = stack.enter_context(wave.open(str(seg), 'rb'))
                    if wf.getparams() != params:
                        # Fallback to pydub if params mismatch
                        from pydub import AudioSegment
                        audio = AudioSegment.from_wav(str(segment_files[0]))
                        for rest in segment_files[1:]:
                            audio += AudioSegment.from_wav(str(rest))
                        audio.export(str(out_path), format="wav")
                        return
                    out_wav.writeframes(wf.readframes(wf.getnframes()))
    except Exception:
        # Fallback on any error
        final_audio = AudioSegment.empty()
        for seg in segment_files:
            final_audio += AudioSegment.from_wav(str(seg))
        final_audio.export(str(out_path), format="wav")


# Helper function to synthesize a single audio segment (optimized - no voice loading)
async def synthesize_audio_segment_fast(
    text: str,
    voice: PiperVoice,
    voice_key: str,  # NEW: for per-voice locking
    rate: float,
    segment_idx: int,
    temp_dir: Path
) -> Path:
    """Synthesize audio for a single text segment using pre-loaded voice
    
    THREAD-SAFE: Uses per-voice lock to prevent concurrent synthesis on same model
    Multiple users can use same voice safely without race conditions
    """
    try:
        # Generate audio file path
        segment_file = temp_dir / f"segment_{segment_idx:04d}.wav"
        
        # Skip if already generated (for resume functionality)
        if segment_file.exists():
            logger.info(f"Segment {segment_idx} already exists, skipping")
            return segment_file
        
        # Synthesize using optimized thread pool (ThreadPoolExecutor handles parallelism)
        def synthesize():
            syn_config = SynthesisConfig(
                length_scale=1.0 / rate,
                noise_scale=0.667,
                noise_w_scale=0.8
            )
            
            with wave.open(str(segment_file), 'wb') as wav_out:
                voice.synthesize_wav(text, wav_out, syn_config=syn_config)
        
        # Run in thread pool - executor manages parallelism, Piper is thread-safe for inference
        # Additionally, cap concurrency per-voice to VOICE_MAX_CONCURRENCY using semaphore
        semaphore = await loaded_voices.get_voice_semaphore(voice_key)
        async with semaphore:
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
        voice = await get_or_load_voice(request.voice, model_path, config_path)
        
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
                    voice_key=request.voice,  # NEW: for per-voice locking
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

# SSE endpoint for audio synthesis with progress tracking (OPTIMIZED with Queue & ETA)
@api_router.post("/audio/synthesize-with-progress")
async def synthesize_audio_with_progress(
    request: AudioSynthesizeRequest,
    current_user: User = Depends(get_current_user)
):
    """Synthesize audio with real-time progress updates via SSE (requires auth)
    Features: Queue management, ETA, speed tracking, fair share, Pro priority
    Uses POST method to support large texts (up to 1 hour audio) that exceed URL length limits"""
    
    async def generate_progress():
        # If request carries a job_id to resume, attempt to load and continue
        resume_from_job = None
        if request.job_id:
            try:
                resume_from_job = await get_generation_job(request.job_id)
            except Exception:
                resume_from_job = None
        job_id = str(uuid.uuid4())
        generation_job_id = None  # NEW: Track generation job for recovery
        generation_start_time = None
        
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
            
            # Get user subscription tier
            subscription = await get_subscription_status(current_user.id)
            is_pro = subscription.tier == "pro"
            
            # Split text early to get segment count for queue
            segments = split_text_into_segments(request.text)
            total_segments = len(segments)
            
            # NEW: Create or reuse generation job for crash recovery
            if resume_from_job and resume_from_job.get("status") in ["pending", "processing", "resumable"]:
                generation_job_id = resume_from_job["job_id"]
                # Reuse existing temp_dir if present
                try:
                    prev_temp = Path(resume_from_job.get("temp_dir", str(temp_dir)))
                    if prev_temp.exists():
                        temp_dir = prev_temp
                except Exception:
                    pass
                logger.info(f"Resuming existing generation job {generation_job_id}")
            else:
                generation_job_id = await create_generation_job(
                    user_id=current_user.id,
                    text=request.text,
                    voice=request.voice,
                    rate=request.rate,
                    language=request.language,
                    total_segments=total_segments,
                    temp_dir=str(temp_dir)
                )
                logger.info(f"Created generation job {generation_job_id} for audio {audio_id}")
            
            # Estimate audio duration for ETA calculation
            estimated_audio_duration = estimate_duration(request.text, request.rate)
            estimated_audio_minutes = estimated_audio_duration / 60
            # Determine already completed segments when resuming
            already_done = 0
            try:
                if resume_from_job and resume_from_job.get("segment_files"):
                    already_done = len([p for p in resume_from_job["segment_files"] if Path(p).exists()])
            except Exception:
                already_done = 0

            
            # Create queue job
            queue_job = QueueJob(
                job_id=job_id,
                user_id=current_user.id,
                is_pro=is_pro,
                segments_count=total_segments
            )
            
            # Add to queue
            queue_position = await queue_manager.add_job(queue_job)
            
            # Check for high load and notify user
            is_high_load = queue_manager.is_high_load()
            active_user_count = queue_manager.get_active_user_count()
            
            if is_high_load:
                high_load_msg = f'⚠️ Высокая нагрузка ({active_user_count}+ пользователей). Генерация может занять больше времени.'
                yield f"data: {json.dumps({'type': 'high_load', 'message': high_load_msg, 'active_users': active_user_count})}\n\n"
            
            if queue_position > 1:
                yield f"data: {json.dumps({'type': 'queue', 'message': f'В очереди (позиция {queue_position})', 'progress': 0, 'queue_position': queue_position})}\n\n"

            # Wait for our turn
            while not await queue_manager.can_start_job(queue_job):
                await asyncio.sleep(1)
                queue_position = await queue_manager.get_queue_position(job_id)
                if queue_position and queue_position > 0:
                    yield f"data: {json.dumps({'type': 'queue', 'message': f'В очереди (позиция {queue_position})', 'progress': 0, 'queue_position': queue_position})}\n\n"
            
            # Start job
            await queue_manager.start_job(queue_job)

            generation_start_time = time.time()
            
            try:
                # Stage 1: Load voice model (0-5%)
                yield f"data: {json.dumps({'type': 'stage', 'stage': 'loading_model', 'message': 'Загрузка модели голоса...', 'progress': 0, 'total_segments': total_segments, 'estimated_audio_minutes': round(estimated_audio_minutes, 1)})}\n\n"
                
                voices_data = await fetch_available_voices()
                model_path, config_path = await download_voice_model(request.voice, voices_data)
                voice_obj = await get_or_load_voice(request.voice, model_path, config_path)
                
                yield f"data: {json.dumps({'type': 'progress', 'progress': 5, 'message': 'Модель загружена', 'stage': 'loading_model'})}\n\n"
                
                # Stage 2: Generate audio segments (5-85%)
                yield f"data: {json.dumps({'type': 'stage', 'stage': 'generating_segments', 'message': f'Генерация {total_segments} сегментов...', 'progress': 5, 'total_segments': total_segments})}\n\n"
                
                # Get batch size based on user tier and current load
                batch_size = queue_manager.get_batch_size_for_user(is_pro)
                # Don't create more tasks than segments (memory optimization)
                batch_size = min(batch_size, total_segments)
                logger.info(f"Batch allocation for job {generation_job_id}: batch_size={batch_size}, is_pro={is_pro}, total_segments={total_segments}")
                completed_segments = 0
                all_segment_files = []
                
                segments_start_time = time.time()
                batches_completed = 0
                total_batches = (total_segments + batch_size - 1) // batch_size
                
                for batch_start in range(0, total_segments, batch_size):
                    batch_end = min(batch_start + batch_size, total_segments)
                    batch_segments = segments[batch_start:batch_end]
                    batch_segment_count = len(batch_segments)
                    
                    # Generate batch in parallel
                    tasks = []
                    for idx, segment in enumerate(batch_segments):
                        global_idx = batch_start + idx
                        # Skip work if file for this segment already exists (resume)
                        seg_path = temp_dir / f"segment_{global_idx:04d}.wav"
                        if seg_path.exists():
                            all_segment_files.append(seg_path)
                            continue
                        task = synthesize_audio_segment_fast(
                            text=segment,
                            voice=voice_obj,
                            voice_key=request.voice,  # NEW: for per-voice locking
                            rate=request.rate,
                            segment_idx=global_idx,
                            temp_dir=temp_dir
                        )
                        tasks.append(task)
                    
                    # Wait for batch to complete
                    batch_files = await asyncio.gather(*tasks) if tasks else []
                    all_segment_files.extend(batch_files)
                    
                    completed_segments += batch_segment_count
                    batches_completed += 1
                    progress = int(5 + (completed_segments / total_segments) * 80)  # 5-85% for generation
                    
                    # NEW: Update generation job progress after each batch (for crash recovery)
                    segment_file_paths = [str(f) for f in all_segment_files]
                    await update_generation_job_progress(
                        job_id=generation_job_id,
                        completed_segments=completed_segments,
                        segment_files=segment_file_paths,
                        status="processing"
                    )
                    
                    # Calculate ETA and speed based on batch completion (more accurate)
                    elapsed = time.time() - segments_start_time
                    
                    # ALWAYS send progress update, with or without ETA
                    if batches_completed > 0 and elapsed > 0.1:  # Changed from > 0 to > 0.1 to avoid division issues
                        time_per_batch = elapsed / batches_completed
                        remaining_batches = total_batches - batches_completed
                        
                        # ETA for remaining batches + estimated combine time (5% of total)
                        batches_eta = time_per_batch * remaining_batches
                        combine_eta = elapsed * 0.05  # Combine typically takes ~5% of generation time
                        eta_seconds = batches_eta + combine_eta
                        
                        # Calculate generation speed (audio_minutes per second of real time)
                        audio_generated_minutes = (completed_segments / total_segments) * estimated_audio_minutes
                        speed = audio_generated_minutes / elapsed if elapsed > 0 else 0
                        
                        # Format ETA nicely
                        if eta_seconds >= 60:
                            eta_formatted = f"{int(eta_seconds // 60)}м {int(eta_seconds % 60)}с"
                        else:
                            eta_formatted = f"{int(eta_seconds)}с"
                        
                        yield f"data: {json.dumps({'type': 'progress', 'progress': progress, 'message': f'Генерация {completed_segments}/{total_segments} сегментов', 'stage': 'generating_segments', 'completed_segments': completed_segments, 'total_segments': total_segments, 'eta': eta_formatted, 'speed': round(speed, 1), 'elapsed': round(elapsed, 1)})}\n\n"
                    else:
                        # First batch or very fast - show basic progress
                        yield f"data: {json.dumps({'type': 'progress', 'progress': progress, 'message': f'Генерация {completed_segments}/{total_segments} сегментов', 'stage': 'generating_segments', 'completed_segments': completed_segments, 'total_segments': total_segments})}\n\n"
                
                # Stage 3: Combine audio segments (85-98%) with streaming to save memory
                yield f"data: {json.dumps({'type': 'stage', 'stage': 'combining', 'message': 'Объединение аудио...', 'progress': 85})}\n\n"
                
                # Stream concatenate directly to output WAV to avoid high RAM usage
                total_files = len(all_segment_files)
                final_file = audio_dir / f"{audio_id}.wav"
                try:
                    import contextlib
                    with contextlib.ExitStack() as stack:
                        files_sorted = sorted(all_segment_files)
                        first = stack.enter_context(wave.open(str(files_sorted[0]), 'rb'))
                        params = first.getparams()
                        with wave.open(str(final_file), 'wb') as out_wav:
                            out_wav.setparams(params)
                            out_wav.writeframes(first.readframes(first.getnframes()))
                            for idx, seg in enumerate(files_sorted[1:], 2):
                                wf = stack.enter_context(wave.open(str(seg), 'rb'))
                                if wf.getparams() != params:
                                    # fallback to pydub if params differ
                                    temp_audio = AudioSegment.from_wav(str(files_sorted[0]))
                                    for rest in files_sorted[1:]:
                                        temp_audio += AudioSegment.from_wav(str(rest))
                                    temp_audio.export(str(final_file), format="wav")
                                    break
                                out_wav.writeframes(wf.readframes(wf.getnframes()))
                                # Progress during combining (85-98%)
                                combine_progress = int(85 + (idx / total_files) * 13)
                                if idx % 5 == 0 or idx == total_files or idx == 1:
                                    yield f"data: {json.dumps({'type': 'progress', 'progress': combine_progress, 'message': f'Склейка {idx}/{total_files}', 'stage': 'combining'})}\n\n"
                except Exception:
                    # Fallback: pydub concat
                    temp_audio = AudioSegment.empty()
                    for seg in sorted(all_segment_files):
                        temp_audio += AudioSegment.from_wav(str(seg))
                    temp_audio.export(str(final_file), format="wav")
                
                # Stage 4: Save file (98-100%)
                yield f"data: {json.dumps({'type': 'stage', 'stage': 'saving', 'message': 'Сохранение файла...', 'progress': 98})}\n\n"
                
                # After saving, delete segment files to free disk
                for file in all_segment_files:
                    try:
                        Path(file).unlink()
                    except Exception:
                        pass
                
                # Get real audio duration
                audio_duration = get_audio_duration(final_file)
                
                # Clean up temp directory (files already deleted inline during combining)
                try:
                    if temp_dir.exists():
                        # Delete any remaining files
                        for file in temp_dir.glob("*.wav"):
                            try:
                                file.unlink()
                            except Exception:
                                pass
                        temp_dir.rmdir()
                except Exception as cleanup_error:
                    logger.warning(f"Temp cleanup warning: {cleanup_error}")
                
                # Calculate total generation time and final speed
                total_generation_time = time.time() - generation_start_time
                final_speed = (audio_duration / 60) / total_generation_time if total_generation_time > 0 else 0
                
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
                    "generation_time": total_generation_time,
                    "generation_speed": final_speed,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                
                await db.audio_generations.insert_one(audio_doc)
                
                # NEW: Mark generation job as completed
                if generation_job_id:
                    await complete_generation_job(generation_job_id, audio_id)
                
                # Send completion with stats
                yield f"data: {json.dumps({'type': 'complete', 'progress': 100, 'audio_id': audio_id, 'audio_url': f'/audio/download/{audio_id}', 'duration': audio_duration, 'generation_time': round(total_generation_time, 1), 'speed': round(final_speed, 2), 'message': f'Готово! ({round(audio_duration/60, 1)} мин за {round(total_generation_time, 1)}с, скорость {round(final_speed, 1)}x)'})}\n\n"
                
            finally:
                # Always finish job in queue and cleanup temp files
                await queue_manager.finish_job(job_id)
                
                # Cleanup temp directory if it still exists (in case of error)
                try:
                    if temp_dir.exists():
                        for file in temp_dir.glob("*.wav"):
                            try:
                                file.unlink()
                            except Exception:
                                pass
                        temp_dir.rmdir()
                except Exception as cleanup_error:
                    logger.warning(f"Final cleanup warning: {cleanup_error}")
            
        except Exception as e:
            logger.error(f"Error in SSE audio synthesis: {str(e)}", exc_info=True)
            
            # NEW: Mark generation job as failed
            if generation_job_id:
                await fail_generation_job(generation_job_id, str(e))
            
            # Cleanup on error
            try:
                if 'temp_dir' in locals() and temp_dir.exists():
                    for file in temp_dir.glob("*.wav"):
                        try:
                            file.unlink()
                        except Exception:
                            pass
                    try:
                        temp_dir.rmdir()
                    except Exception:
                        pass
            except Exception:
                pass
            
            if 'generation_start_time' in locals() and generation_start_time:
                await queue_manager.finish_job(job_id)
            
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

@api_router.get("/text/download/{audio_id}")
async def download_text(audio_id: str, current_user: User = Depends(get_current_user)):
    """Download generated text as .txt file"""
    try:
        # Fetch from database - verify user owns this generation
        audio_doc = await db.audio_generations.find_one({
            "id": audio_id,
            "user_id": current_user.id
        }, {"_id": 0})
        
        if not audio_doc:
            raise HTTPException(status_code=404, detail="Text not found or access denied")
        
        text_content = audio_doc.get("text", "")
        
        if not text_content:
            raise HTTPException(status_code=404, detail="Text content not available")
        
        # Return as downloadable .txt file
        return Response(
            content=text_content,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="text_{audio_id}.txt"',
                "Content-Type": "text/plain; charset=utf-8"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error downloading text: {str(e)}")

@api_router.post("/audio/cleanup/{audio_id}")
async def cleanup_audio_file(audio_id: str, current_user: User = Depends(get_current_user)):
    """Delete audio file from disk (user-initiated only)
    Files are stored permanently by default - only user can delete"""
    try:
        # Verify user owns this audio
        audio_doc = await db.audio_generations.find_one({
            "id": audio_id,
            "user_id": current_user.id
        }, {"_id": 0})
        
        if not audio_doc:
            raise HTTPException(status_code=404, detail="Audio not found or access denied")
        
        audio_path = Path(audio_doc["audio_path"])
        
        # Delete file if it exists
        deleted = False
        freed_bytes = 0
        if audio_path.exists():
            try:
                freed_bytes = audio_path.stat().st_size
                audio_path.unlink()
                deleted = True
                logger.info(f"User deleted audio file: {audio_id} ({audio_path.name}, {freed_bytes/1024/1024:.2f} MB)")
            except Exception as e:
                logger.warning(f"Could not delete audio file {audio_id}: {str(e)}")
        
        # Mark as cleaned in database
        await db.audio_generations.update_one(
            {"id": audio_id},
            {"$set": {"file_deleted": True, "deleted_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        freed_mb = freed_bytes / (1024 * 1024)
        return {
            "success": True, 
            "deleted": deleted, 
            "freed_mb": round(freed_mb, 2),
            "message": f"Audio file deleted ({freed_mb:.2f} MB freed)"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error cleaning up audio: {str(e)}")

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

# ============================================================================
# GENERATION JOB ENDPOINTS (For crash recovery)
# ============================================================================

@api_router.get("/jobs/pending", response_model=List[GenerationJobResponse])
async def get_pending_generation_jobs(current_user: User = Depends(get_current_user)):
    """Get pending/processing generation jobs for current user (for auto-resume after crash)"""
    try:
        jobs = await get_pending_jobs(current_user.id)
        
        response = []
        for job in jobs:
            progress_percent = int((job["completed_segments"] / job["total_segments"]) * 100) if job["total_segments"] > 0 else 0
            response.append(GenerationJobResponse(
                job_id=job["job_id"],
                status=job["status"],
                completed_segments=job["completed_segments"],
                total_segments=job["total_segments"],
                progress_percent=progress_percent,
                text_preview=job["text"][:100] + "..." if len(job["text"]) > 100 else job["text"]
            ))
        
        return response
        
    except Exception as e:
        logger.error(f"Error fetching pending jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching pending jobs: {str(e)}")

@api_router.get("/jobs/{job_id}", response_model=GenerationJob)
async def get_job_details(job_id: str, current_user: User = Depends(get_current_user)):
    """Get details of a specific generation job"""
    try:
        job = await get_generation_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Verify ownership
        if job["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this job")
        
        return GenerationJob(**job)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching job details: {str(e)}")

@api_router.post("/jobs/{job_id}/resume")
async def resume_generation_job(job_id: str, current_user: User = Depends(get_current_user)):
    """Resume a pending/failed generation job (triggers SSE audio generation)"""
    try:
        job = await get_generation_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Verify ownership
        if job["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this job")
        
        # Only resume if pending or failed
        if job["status"] not in ["pending", "failed", "processing"]:
            raise HTTPException(status_code=400, detail=f"Cannot resume job with status: {job['status']}")
        
        # Return job details - frontend will use these to call SSE endpoint
        return {
            "job_id": job_id,
            "message": "Job ready to resume",
            "text": job["text"],
            "voice": job["voice"],
            "rate": job["rate"],
            "language": job["language"],
            "completed_segments": job["completed_segments"],
            "total_segments": job["total_segments"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error resuming job: {str(e)}")

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# BACKGROUND TASK: REMOVED - Files are now stored permanently
# Users can manually delete files if needed via cleanup endpoint
# ============================================================================

@app.on_event("startup")
async def startup_job_recovery():
    """Job recovery on app startup - mark interrupted jobs as resumable"""
    
    # Mark interrupted generation jobs as resumable (not failed!)
    # This allows jobs to continue after server restart
    try:
        result = await db.generation_jobs.update_many(
            {"status": {"$in": ["pending", "processing"]}},
            {
                "$set": {
                    "status": "resumable",
                    "error_message": "Server restarted - job can be resumed",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        if result.modified_count > 0:
            logger.warning(f"Marked {result.modified_count} interrupted jobs as resumable (can be continued)")
    except Exception as e:
        logger.error(f"Error marking interrupted jobs as resumable: {str(e)}")
    
    logger.info("Job recovery complete. Permanent file storage enabled (no auto-cleanup)")

@app.on_event("shutdown")
async def shutdown_db_client():
    """Cleanup on shutdown"""
    client.close()