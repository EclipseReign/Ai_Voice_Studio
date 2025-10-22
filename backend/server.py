from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
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
        
        # Get the best quality available
        qualities = list(voice_info['files'].keys())
        quality = qualities[0]  # Default to first (usually medium or high)
        
        # Get file paths
        model_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{voice_info['files'][quality]}"
        config_url = model_url.replace('.onnx', '.onnx.json')
        
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
                qualities = list(voice_info['files'].keys())
                quality = qualities[0] if qualities else 'medium'
                
                # Extract voice name from key (e.g., en_US-amy-low -> Amy)
                voice_name = voice_key.split('-')[1] if '-' in voice_key else voice_key
                voice_name = voice_name.capitalize()
                
                # Get full locale from voice_key (e.g., en_US)
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
            with wave.open(str(wav_file), 'wb') as wav_out:
                # Configure WAV file
                wav_out.setnchannels(1)  # Mono
                wav_out.setsampwidth(2)  # 16-bit
                wav_out.setframerate(voice.config.sample_rate)
                
                # Synthesize with speed adjustment
                for audio_bytes in voice.synthesize_stream_raw(
                    request.text,
                    length_scale=1.0 / request.rate  # Piper uses length_scale (inverse of rate)
                ):
                    wav_out.writeframes(audio_bytes)
        
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
            audio_url=f"/api/audio/download/{audio_id}",
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