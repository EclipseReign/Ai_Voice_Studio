from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone
import asyncio
import io
from emergentintegrations.llm.chat import LlmChat, UserMessage
import edge_tts
import tempfile

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

# Models
class Voice(BaseModel):
    name: str
    short_name: str
    gender: str
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
    rate: str = "+0%"  # Speed: -50% to +100%
    pitch: str = "+0Hz"  # Pitch adjustment (optional)
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
    language: str
    slow: Optional[bool] = False
    created_at: str

# Helper function to estimate speaking duration
def estimate_duration(text: str, rate: str = "+0%") -> float:
    """Estimate audio duration in seconds. Average: 150 words per minute"""
    words = len(text.split())
    
    # Parse rate
    rate_value = int(rate.replace('%', '').replace('+', ''))
    speed_multiplier = 1 + (rate_value / 100)
    
    # Base: 150 words per minute
    base_minutes = words / 150
    adjusted_minutes = base_minutes / speed_multiplier
    
    return adjusted_minutes * 60  # Convert to seconds

# Helper function to calculate target word count
def calculate_word_count(duration_minutes: int) -> int:
    """Calculate target word count for desired duration"""
    return duration_minutes * 150  # 150 words per minute

@api_router.get("/")
async def root():
    return {"message": "Text-to-Speech API"}

@api_router.get("/languages", response_model=List[Language])
async def get_languages():
    """Get available languages for gTTS"""
    try:
        # Common languages supported by gTTS
        languages = [
            Language(code="en", name="English", tld="com"),
            Language(code="es", name="Spanish", tld="es"),
            Language(code="fr", name="French", tld="fr"),
            Language(code="de", name="German", tld="de"),
            Language(code="it", name="Italian", tld="it"),
            Language(code="pt", name="Portuguese", tld="com.br"),
            Language(code="ru", name="Russian", tld="ru"),
            Language(code="zh-CN", name="Chinese (Simplified)", tld="com"),
            Language(code="ja", name="Japanese", tld="co.jp"),
            Language(code="ko", name="Korean", tld="co.kr"),
            Language(code="ar", name="Arabic", tld="com"),
            Language(code="hi", name="Hindi", tld="co.in"),
            Language(code="nl", name="Dutch", tld="nl"),
            Language(code="pl", name="Polish", tld="pl"),
            Language(code="tr", name="Turkish", tld="com.tr"),
        ]
        return languages
    except Exception as e:
        logger.error(f"Error fetching languages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching languages: {str(e)}")

@api_router.post("/text/generate", response_model=TextGenerateResponse)
async def generate_text(request: TextGenerateRequest):
    """Generate text based on prompt and duration using LLM"""
    try:
        # Calculate target word count
        target_words = calculate_word_count(request.duration_minutes)
        
        # Create LLM chat instance
        chat = LlmChat(
            api_key=os.environ.get('EMERGENT_LLM_KEY'),
            session_id=str(uuid.uuid4()),
            system_message=f"You are a professional content writer. Generate engaging, natural-sounding narration scripts."
        ).with_model("openai", "gpt-4o-mini")
        
        # Create prompt for text generation
        user_prompt = f"""Write a detailed narration script about: {request.prompt}

Requirements:
- Target length: approximately {target_words} words (for {request.duration_minutes} minute(s) of audio)
- Language: {request.language}
- Style: Natural, conversational narration suitable for audio
- Structure: Introduction, main content, conclusion
- Make it engaging and suitable for listening

Generate ONLY the narration text without any meta-commentary or formatting markers."""
        
        # Generate text
        user_message = UserMessage(text=user_prompt)
        response = await chat.send_message(user_message)
        
        generated_text = response.strip()
        word_count = len(generated_text.split())
        estimated_duration = estimate_duration(generated_text)
        
        # Save to database
        text_id = str(uuid.uuid4())
        generation_doc = {
            "id": text_id,
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

@api_router.post("/audio/synthesize", response_model=AudioSynthesizeResponse)
async def synthesize_audio(request: AudioSynthesizeRequest):
    """Synthesize audio from text using gTTS"""
    try:
        # Create unique ID
        audio_id = str(uuid.uuid4())
        
        # Create audio directory if it doesn't exist
        audio_dir = Path("/app/backend/audio_files")
        audio_dir.mkdir(exist_ok=True)
        
        # Generate audio file path
        audio_file = audio_dir / f"{audio_id}.mp3"
        
        # For long texts, gTTS might have limitations. Let's handle in chunks if needed
        # gTTS can handle up to ~5000 characters per request reliably
        text_length = len(request.text)
        logger.info(f"Generating audio for text of length: {text_length} characters")
        
        # Create gTTS instance
        # Note: gTTS uses language codes like 'en', 'es', 'fr', etc.
        # and tld parameter for accent variations
        tts = gTTS(
            text=request.text,
            lang=request.language,
            slow=request.slow
        )
        
        # Save audio to file (this runs synchronously)
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, tts.save, str(audio_file))
        
        logger.info(f"Audio file saved: {audio_file}")
        
        # Save to database
        audio_doc = {
            "id": audio_id,
            "text": request.text,
            "language": request.language,
            "slow": request.slow,
            "audio_path": str(audio_file),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.audio_generations.insert_one(audio_doc)
        
        return AudioSynthesizeResponse(
            id=audio_id,
            audio_url=f"/api/audio/download/{audio_id}",
            text=request.text[:100] + "..." if len(request.text) > 100 else request.text,
            language=request.language,
            created_at=audio_doc["created_at"]
        )
        
    except Exception as e:
        logger.error(f"Error synthesizing audio: {str(e)}")
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
        
        return FileResponse(
            path=audio_path,
            media_type="audio/mpeg",
            filename=f"generated_audio_{audio_id}.mp3"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error downloading audio: {str(e)}")

@api_router.get("/history", response_model=List[GenerationHistory])
async def get_history():
    """Get generation history"""
    try:
        # Fetch audio generations with most recent first
        audio_gens = await db.audio_generations.find(
            {}, {"_id": 0}
        ).sort("created_at", -1).limit(50).to_list(50)
        
        history = []
        for gen in audio_gens:
            history.append(GenerationHistory(
                id=gen["id"],
                text=gen["text"][:100] + "..." if len(gen["text"]) > 100 else gen["text"],
                audio_url=f"/api/audio/download/{gen['id']}",
                language=gen.get("language", "en"),
                slow=gen.get("slow", False),
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