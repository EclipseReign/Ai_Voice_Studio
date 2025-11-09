"""
Video Generation Service
Handles all video generation logic including:
1. YouTube format with image slideshow
2. YouTube format with continuous video (Sora-like)
3. Shorts format for TikTok/Reels
"""

import os
import re
import json
import asyncio
import aiohttp
import shlex
import tempfile
import subprocess
import urllib.parse
from typing import List, Dict, Tuple, Optional, Any
import time
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Try to import faster-whisper for accurate word-level timestamps
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
    logger.info("✅ Faster-Whisper available for accurate subtitle synchronization")
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("⚠️ Faster-Whisper not available. Subtitles will use estimated timing.")

POLLINATIONS_API_URL = "https://image.pollinations.ai/prompt"

SUBTITLE_STYLES = {
    "tiktok": {
        "fontsize": 70,  # Larger for more impact
        "fontcolor": "yellow",  # Classic TikTok yellow
        "borderw": 8,  # Thick border for pop effect
        "bordercolor": "black",
        "bold": 1,
        "font": "Liberation Sans Narrow",  # Bold condensed font like TikTok
        "words_per_phrase": 2,  # 1-2 words at a time like TikTok
        "primary_color": "&H0000FFFF",  # Yellow (AABBGGRR format)
        "outline_color": "&H00000000",  # Black outline
        "shadow": 2,  # Add shadow for depth
        "use_pop_animation": True,  # Enable pop animation in ASS
    },
    "instagram": {
        "fontsize": 68,
        "fontcolor": "white",
        "borderw": 5,
        "bordercolor": "black",
        "bold": 1,
        "font": "Liberation Sans",  # Clean modern font
        "shadowcolor": "black@0.8",
        "shadowx": 3,
        "shadowy": 3,
        "words_per_phrase": 3,
        "primary_color": "&H00FFFFFF",  # White
        "outline_color": "&H00000000",  # Black outline
        "shadow": 4,  # Strong shadow for Instagram look
        "use_pop_animation": False,
    },
    "minimal": {
        "fontsize": 60,
        "fontcolor": "white",
        "borderw": 3,
        "bordercolor": "&H40000000",  # Semi-transparent black
        "font": "DejaVu Serif",  # Elegant serif font for aesthetic look
        "words_per_phrase": 4,
        "primary_color": "&H00FFFFFF",  # Pure white
        "outline_color": "&H40000000",  # Semi-transparent outline
        "shadow": 1,  # Subtle shadow
        "use_pop_animation": False,
    }
}

# Video settings by type
VIDEO_SETTINGS = {
    "youtube_images": {
        "aspect_ratio": "16:9",
        "resolution": (1280, 720),
        "images_per_minute": 6,  # Change image every 10 seconds
    },
    "youtube_continuous": {
        "aspect_ratio": "16:9",
        "resolution": (1280, 720),
        "clip_duration": 4,  # 4-second video clips
    },
    "shorts": {
        "aspect_ratio": "9:16",
        "resolution": (720, 1280),
        "images_per_minute": 10,  # Change image every 6 seconds (faster for shorts)
    }
}


def _sec_to_ass(ts: float) -> str:
    """Преобразует секунды в формат ASS: H:MM:SS.cs (сотые)"""
    if ts < 0:
        ts = 0.0
    h = int(ts // 3600)
    m = int((ts % 3600) // 60)
    s = int(ts % 60)
    cs = int(round((ts - int(ts)) * 100))
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def build_ass_from_words(
    timed_words: List[Dict[str, float]],
    *,
    resolution: Tuple[int, int] = (1080, 1920),
    words_per_phrase: int = 2,
    fontname: str = "DejaVu Sans",
    fontsize: int = 64,
    primary_color: str = "&H00FFFFFF",   # белый (AA BB GG RR, AA=00 прозрачность)
    outline_color: str = "&H00000000",   # чёрный
    outline: int = 4,
    shadow: int = 0,
    margin_v: int = 100,
    align: int = 2,  # 2 — центр снизу, 8 — центр по центру
    out_path: str | None = None,
    use_pop_animation: bool = False,
) -> str:
    """
    Группирует слова в фразы и пишет .ass; возвращает абсолютный путь к файлу.
    """
    w, h = resolution
    bold = 1 if "Sans" in fontname or "Liberation" in fontname else 0

    header = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {w}",
        f"PlayResY: {h}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        # BackColour и SecondaryColour тут не используются по сути
        f"Style: Default,{fontname},{fontsize},{primary_color},&H000000FF,{outline_color},&H64000000,"
        f"{bold},0,0,0,100,100,0,0,1,{outline},{shadow},{align},20,20,{margin_v},0",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    # Группируем слова в фразы
    phrases: list[tuple[float, float, str]] = []
    for i in range(0, len(timed_words), words_per_phrase):
        chunk = timed_words[i:i + words_per_phrase]
        if not chunk:
            continue
        text = " ".join(w["word"] for w in chunk)
        # Экраним проблемные для ASS символы
        text = text.replace("{", r"\{").replace("}", r"\}")
        text = " ".join(text.split())

        start = float(chunk[0]["start_time"])
        end = float(chunk[-1]["end_time"])
        if end <= start:
            end = start + 0.001

        phrases.append((start, end, text))

    # Create events with optional pop animation
    events = []
    for (s, e, t) in phrases:
        if use_pop_animation:
            # TikTok-style pop animation: scale from 80% to 110% then back to 100%
            duration_ms = int((e - s) * 1000)
            pop_time = min(200, duration_ms // 3)  # Animation duration in ms
            
            # Animation: scale up quickly then settle
            # 	(start,end,\fscX\fscY) - scale animation
            animation = (
                r"{	(0," + str(pop_time) + r",fscx110fscy110)"
                r"	(" + str(pop_time) + "," + str(pop_time * 2) + r",fscx100fscy100)}"
            )
            text_with_animation = f"{animation}{t}"
            events.append(f"Dialogue: 0,{_sec_to_ass(s)},{_sec_to_ass(e)},Default,,0,0,0,,{text_with_animation}")
        else:
            # Standard subtitles without animation
            events.append(f"Dialogue: 0,{_sec_to_ass(s)},{_sec_to_ass(e)},Default,,0,0,0,,{t}")

    if not out_path:
        tmpdir = tempfile.mkdtemp(prefix="ass_")
        out_path = os.path.join(tmpdir, "subs.ass")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(header + events) + "\n")

    return os.path.abspath(out_path)

async def get_accurate_word_timestamps(audio_path: str, text: str) -> List[Dict[str, any]]:
    """
    Get accurate word-level timestamps from audio file using Whisper.
    This ensures subtitles are perfectly synchronized with the actual speech.
    
    Args:
        audio_path: Path to audio file
        text: Original text (for reference and fallback)
        
    Returns:
        List of dicts with {word, start_time, end_time} with accurate timestamps
    """
    if not WHISPER_AVAILABLE:
        logger.warning("Whisper not available, using fallback timing estimation")
        # Fallback to old method
        import wave
        with wave.open(audio_path, 'rb') as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
            duration = frames / float(rate)
        return split_text_into_timed_words(text, duration, words_per_second=2.5)
    
    try:
        logger.info(f"🎯 Analyzing audio with Whisper for accurate word timestamps: {audio_path}")
        
        # Run Whisper in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        timed_words = await loop.run_in_executor(None, _get_timestamps_sync, audio_path, text)
        
        logger.info(f"✅ Got {len(timed_words)} accurate word timestamps from Whisper")
        return timed_words
        
    except Exception as e:
        logger.error(f"Error getting accurate timestamps with Whisper: {e}", exc_info=True)
        # Fallback to estimation
        import wave
        with wave.open(audio_path, 'rb') as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
            duration = frames / float(rate)
        logger.warning("Falling back to estimated timing")
        return split_text_into_timed_words(text, duration, words_per_second=2.5)


def _get_timestamps_sync(audio_path: str, original_text: str) -> List[Dict[str, any]]:
    """
    Synchronous function to get word timestamps using Whisper.
    Runs in thread pool executor.
    
    Args:
        audio_path: Path to audio file
        original_text: Original text for reference
        
    Returns:
        List of word timing dicts
    """
    # Load Whisper model (tiny for speed, can use base/small for better accuracy)
    # tiny: fastest, ~1GB RAM, good for word timing
    # base: slower but more accurate
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    
    logger.info("Transcribing audio with word-level timestamps...")
    
    # Transcribe with word timestamps
    segments, info = model.transcribe(
        audio_path,
        language=None,  # Auto-detect language
        word_timestamps=True,  # Enable word-level timestamps
        vad_filter=True,  # Voice activity detection to remove silence
        vad_parameters=dict(
            min_silence_duration_ms=500
        )
    )
    
    # Extract word-level timestamps
    timed_words = []
    for segment in segments:
        if hasattr(segment, 'words') and segment.words:
            for word_info in segment.words:
                # Clean word (remove punctuation for matching)
                word = word_info.word.strip()
                if word:  # Skip empty words
                    timed_words.append({
                        "word": word,
                        "start_time": word_info.start,
                        "end_time": word_info.end
                    })
    
    logger.info(f"Extracted {len(timed_words)} word timestamps from audio")
    
    # If we got no words (unlikely), fallback
    if not timed_words:
        logger.warning("No word timestamps extracted, using estimated timing")
        import wave
        with wave.open(audio_path, 'rb') as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
            duration = frames / float(rate)
        return split_text_into_timed_words(original_text, duration, words_per_second=2.5)
    
    return timed_words

def split_text_into_timed_words(text: str, audio_duration: float, words_per_second: float = 3.0) -> List[Dict[str, any]]:
    """
    Split text into words with timing information.
    Distributes words evenly across the audio duration.
    
    Args:
        text: The full text content
        audio_duration: Duration of audio in seconds
        
    Returns:
        List of dicts with {word, start_time, end_time}
    """
    # Clean and split text into words
    words = re.findall(r'\S+', text)  # Get all non-whitespace sequences
    
    if not words:
        return []
    
    # Calculate time per word (with small overlap for smoother transitions)
    time_per_word = 1.0 / words_per_second
    
    timed_words = []
    for i, word in enumerate(words):
        start_time = i * time_per_word
        end_time = (i + 1) * time_per_word
        if start_time >= audio_duration:
            break
        timed_words.append({
            "word": word,
            "start_time": start_time,
            "end_time": min(end_time, audio_duration)
        })
    
    logger.info(f"Split text into {len(timed_words)} timed words at {words_per_second} words/sec over {audio_duration:.1f}s (showing {len(timed_words)}/{len(words)} words)")
    return timed_words


def generate_subtitle_filter(
    timed_words: List[Dict[str, any]],
    style: str,
    position: str,
    resolution: Tuple[int, int]
) -> str:
    """
    Генерирует FFmpeg drawtext-фильтр для субтитров без параметра alpha.
    Появление/исчезновение контролируется через enable и анимацией позиции.
    """
    if not timed_words or style not in SUBTITLE_STYLES:
        return ""

    style_config = SUBTITLE_STYLES[style]
    width, height = resolution
    words_per_phrase = style_config.get("words_per_phrase", 2)

    # Базовая Y-позиция
    if position == "center":
        y_pos = "(h-text_h)/2"
    else:
        y_pos = "h-text_h-100"

    # Группируем слова в фразы
    phrases: List[Dict[str, float]] = []
    for i in range(0, len(timed_words), words_per_phrase):
        phrase_words = timed_words[i: i + words_per_phrase]
        if not phrase_words:
            continue

        phrase_text = " ".join([w["word"] for w in phrase_words])

        start_time = float(phrase_words[0]["start_time"])
        end_time = float(phrase_words[-1]["end_time"])
        if end_time <= start_time:
            end_time = start_time + 0.001

        phrases.append({"text": phrase_text, "start": start_time, "end": end_time})

    filters: List[str] = []

    for phrase in phrases:
        # Безопасная очистка текста для drawtext
        text = phrase["text"]
        text = text.replace("\\", "\\\\")          # экранируем обратный слеш
        text = text.replace("'", "")               # убираем одиночные кавычки
        text = text.replace("\r\n", " ").replace("\n", " ")  # переносы в пробел

        start = phrase["start"]
        end = phrase["end"]
        duration = max(end - start, 0.001)

        # Базовые параметры drawtext
        drawtext_params = [
            f"text='{text}'",
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            f"fontsize={style_config['fontsize']}",
            f"fontcolor={style_config['fontcolor']}",
            f"borderw={style_config.get('borderw', 0)}",
            f"bordercolor={style_config.get('bordercolor', 'black')}",
        ]

        if style_config.get("box"):
            drawtext_params.append(f"box={style_config['box']}")
            drawtext_params.append(f"boxcolor={style_config['boxcolor']}")
            drawtext_params.append(f"boxborderw={style_config['boxborderw']}")

        if style_config.get("shadowcolor"):
            drawtext_params.append(f"shadowcolor={style_config['shadowcolor']}")
            drawtext_params.append(f"shadowx={style_config['shadowx']}")
            drawtext_params.append(f"shadowy={style_config['shadowy']}")

        # Позиционирование + анимация
        if style == "tiktok":
            # Прыжок при появлении + лёгкое покачивание
            y_base = "(h-text_h)/2" if position == "center" else "h-text_h-100"
            bounce_duration = 0.2
            bounce_y = (
                f"if(lt(t-{start},{bounce_duration}),"
                f"-30*sin(PI*(t-{start})/{bounce_duration}),"
                f"5*sin(4*PI*(t-{start})))"
            )
            # ВАЖНО: значения x= и y= в кавычках (из-за запятых в if(...))
            drawtext_params.append("x='(w-text_w)/2'")
            drawtext_params.append(f"y='{y_base}+{bounce_y}'")

        elif style == "instagram":
            drawtext_params.append("x='(w-text_w)/2'")
            drawtext_params.append(f"y='{y_pos}+15*sin(6*PI*(t-{start})/{duration})'")

        else:  # minimal
            drawtext_params.append("x='(w-text_w)/2'")
            drawtext_params.append(f"y='{y_pos}'")

        # Показываем фразу только на её интервале
        drawtext_params.append(f"enable='between(t,{start},{end})'")

        filters.append("drawtext=" + ":".join(drawtext_params))

    if not filters:
        return ""

    combined = ",".join(filters)
    logger.info(
        f"Generated subtitle filter with {len(phrases)} phrases "
        f"({words_per_phrase} words each) in {style} style (no alpha)"
    )
    return combined

async def generate_image_prompts_from_text(text: str, num_prompts: int, video_type: str) -> List[str]:
    """
    Generate image prompts from text using AI or simple extraction.
    For now, uses simple sentence extraction and enhancement.
    
    Args:
        text: The full text content
        num_prompts: Number of prompts to generate
        video_type: Type of video being created
        
    Returns:
        List of image generation prompts
    """
    try:
        # Split text into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            # Fallback if no sentences found
            return [f"Beautiful scene related to: {text[:100]}" for _ in range(num_prompts)]
        
        # Select evenly distributed sentences
        step = max(1, len(sentences) // num_prompts)
        selected_sentences = []
        for i in range(0, len(sentences), step):
            if len(selected_sentences) >= num_prompts:
                break
            selected_sentences.append(sentences[i])
        # Fill up to num_prompts if needed
        while len(selected_sentences) < num_prompts:
            selected_sentences.append(sentences[len(selected_sentences) % len(sentences)])
        
        # Enhance sentences into image prompts
        enhanced_prompts = []
        for sentence in selected_sentences[:num_prompts]:
            # Take first 100 chars and add visual enhancement keywords
            base = sentence[:100]
            if video_type == "shorts":
                enhanced = f"{base}, vibrant colors, modern aesthetic, high quality, trending on social media"
            else:
                enhanced = f"{base}, cinematic lighting, high quality, detailed, professional photography"
            enhanced_prompts.append(enhanced)
        
        logger.info(f"Generated {len(enhanced_prompts)} image prompts from text")
        return enhanced_prompts
        
    except Exception as e:
        logger.error(f"Error generating image prompts: {e}")
        # Fallback prompts
        return [f"Scene {i+1}: {text[:100]}" for i in range(num_prompts)]



async def generate_image_with_pollinations(prompt: str, width: int, height: int, session: aiohttp.ClientSession) -> bytes:
    """Generate image using Hugging Face Inference API with model fallback and retries."""
    
    max_retries = 5  # Increased retries for unstable API
    base_retry_delay = 5  # Base delay for exponential backoff
    import urllib.parse
    encoded_prompt = urllib.parse.quote(prompt)
    api_url = f"{POLLINATIONS_API_URL}/{encoded_prompt}?width={width}&height={height}&nologo=true&enhance=true"
    for attempt in range(max_retries):
        try:
            # Exponential backoff: 5s, 10s, 20s, 40s, 80s
            if attempt > 0:
                delay = base_retry_delay * (2 ** (attempt - 1))
                logger.info(f"Waiting {delay}s before retry {attempt+1}/{max_retries}...")
                await asyncio.sleep(delay)
            logger.info(f"Pollinations.ai attempt {attempt+1}/{max_retries} for: {prompt[:50]}...")
            async with session.get(api_url, timeout=120) as response:
                if response.status == 200:
                    image_data = await response.read()
                    logger.info(f"✅ Pollinations.ai generated image successfully ({len(image_data)} bytes)")
                    return image_data
                else:
                    err_text = await response.text()
                    logger.warning(f"Pollinations.ai attempt {attempt+1}/{max_retries} failed: {response.status} - {err_text[:100]}")
                    continue
        except asyncio.TimeoutError:
            logger.warning(f"Timeout on Pollinations.ai attempt {attempt+1}/{max_retries}")
            continue
        except Exception as e:
            logger.error(f"Error on Pollinations.ai attempt {attempt+1}/{max_retries}: {e}")
            continue
    raise Exception(f"Pollinations.ai image generation failed after {max_retries} attempts")

async def generate_single_image(
    index: int,
    prompt: str,
    width: int,
    height: int,
    output_dir: str,
    session: aiohttp.ClientSession
) -> Tuple[int, str]:
    """
    Generate a single image with retry logic.
    
    Args:
        index: Image index for ordering
        prompt: Text prompt for image generation
        width: Image width
        height: Image height
        output_dir: Directory to save image
        session: aiohttp session for API calls
        
    Returns:
        Tuple of (index, image_path)
    """
    image_path = os.path.join(output_dir, f"image_{index:04d}.png")
    
    try:
        logger.info(f"Generating image {index + 1}: {prompt[:50]}...")
        
        # Generate image (already has 3 retry attempts built-in)
        image_data = await generate_image_with_pollinations(prompt, width, height, session)
        
        # Save image
        with open(image_path, "wb") as f:
            f.write(image_data)
        
        logger.info(f"✅ Saved image {index + 1} to {image_path}")
        return (index, image_path)
        
    except Exception as e:
        logger.error(f"❌ Error generating image {index + 1} after retries: {e}")
        # Create a placeholder black image on error
        create_placeholder_image(image_path, width, height, f"Error: {str(e)[:50]}")
        return (index, image_path)



async def generate_images_for_video(
    prompts: List[str],
    width: int,
    height: int,
    output_dir: str,
    progress_callback=None
) -> List[str]:
    """
    Generate multiple images from prompts.
    
    Args:
        prompts: List of text prompts
        width: Image width
        height: Image height
        output_dir: Directory to save images
        progress_callback: Async function to call with progress updates
        
    Returns:
        List of image file paths
    """
    os.makedirs(output_dir, exist_ok=True)
    BATCH_SIZE = 2  # Generate 5 images in parallel
    total_images = len(prompts)
    
    # Dictionary to store results with index as key (preserves order)
    results_dict = {}
    
    async with aiohttp.ClientSession() as session:
        for batch_start in range(0, total_images, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total_images)
            batch_size = batch_end - batch_start
            
            logger.info(f"🚀 Starting parallel batch {batch_start // BATCH_SIZE + 1}: images {batch_start + 1}-{batch_end} of {total_images}")
            
            # Create tasks for this batch
            tasks = []
            for i in range(batch_start, batch_end):
                task = generate_single_image(
                    index=i,
                    prompt=prompts[i],
                    width=width,
                    height=height,
                    output_dir=output_dir,
                    session=session
                )
                tasks.append(task)
            
            # Generate all images in this batch in parallel
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch task failed with exception: {result}")
                    continue
                
                index, image_path = result
                results_dict[index] = image_path
            
            # Progress callback after each batch
            if progress_callback:
                completed = len(results_dict)
                await progress_callback(
                    "image_generation",
                    completed,
                    total_images,
                    f"Сгенерировано {completed}/{total_images} изображений (батч {batch_start // BATCH_SIZE + 1})"
                )
                
            logger.info(f"✅ Batch {batch_start // BATCH_SIZE + 1} completed: {batch_size} images generated")
                
                # Small delay between batches to avoid overwhelming the API
            if batch_end < total_images:
                await asyncio.sleep(2)
    
    # Sort results by index to maintain correct order
    sorted_indices = sorted(results_dict.keys())
    image_paths = [results_dict[i] for i in sorted_indices]
    
    logger.info(f"🎉 All {len(image_paths)} images generated successfully in correct order")
    
    return image_paths


def create_placeholder_image(path: str, width: int, height: int, text: str):
    """Create a simple placeholder image when generation fails"""
    import cv2
    import numpy as np
    
    # Create black image
    img = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Add text
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size = cv2.getTextSize(text, font, 1, 2)[0]
    text_x = (width - text_size[0]) // 2
    text_y = (height + text_size[1]) // 2
    cv2.putText(img, text, (text_x, text_y), font, 1, (255, 255, 255), 2)
    
    cv2.imwrite(path, img)


def _ffprobe_duration(path: str) -> float:
    """Надёжно пробуем вытащить длительность аудио через ffprobe."""
    try:
        out = subprocess.check_output(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path
            ],
            text=True
        ).strip()
        dur = float(out)
        return dur if dur > 0 else 0.0
    except Exception:
        return 0.0


async def create_slideshow_video(
    image_paths: List[str],
    audio_path: str,
    resolution: Tuple[int, int],
    subtitle_text: Optional[str],
    subtitle_style: Optional[str],
    subtitle_position: str,
    output_path: str,
) -> str:
    """
    Сборка слайдшоу из изображений под аудио.
    Субтитры накладываются через libass (subtitles=...), чтобы идти непрерывно по таймингам речи.
    """
    if not image_paths:
        raise ValueError("image_paths is empty")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    width, height = resolution

    # 1) Длительность аудио -> длительность каждого слайда
    audio_duration = _ffprobe_duration(audio_path)
    if audio_duration <= 0:
        raise RuntimeError("Failed to probe audio duration with ffprobe")

    n = len(image_paths)
    duration_per_image = audio_duration / n
    logger.info(f"Creating slideshow: {n} images, {duration_per_image:.2f}s per image")

    # 2) Готовим concat-файл (демульсер читает duration для каждого кадра-изображения)
    concat_fd, concat_path = tempfile.mkstemp(suffix=".concat.txt")
    os.close(concat_fd)  # будем писать обычным open
    with open(concat_path, "w", encoding="utf-8") as f:
        for idx, p in enumerate(image_paths):
            # путь в одинарных кавычках, экранируем внутри
            p_escaped = p.replace("'", r"'\''")
            f.write(f"file '{p_escaped}'\n")
            if idx < n - 1:
                f.write(f"duration {duration_per_image:.6f}\n")
        # дублируем последний файл без duration (требование concat demuxer)
        last_p = image_paths[-1].replace("'", r"'\''")
        f.write(f"file '{last_p}'\n")

    # 3) Собираем видеофильтр: scale/pad -> fps=30 (ВНУТРИ графа) -> subtitles -> format
    video_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
        f"fps=30"
    )

    # 4) Если нужны субтитры — готовим .ass по word-таймингам и добавляем фильтр subtitles
    if subtitle_text and subtitle_style:
        logger.info(f"🎯 Analyzing audio with Whisper for accurate word timestamps: {audio_path}")
        timed_words = await get_accurate_word_timestamps(audio_path, subtitle_text)
        logger.info(f"✅ Got {len(timed_words)} accurate word timestamps from Whisper")

        style_conf = SUBTITLE_STYLES.get(subtitle_style, {})
        words_per_phrase = int(style_conf.get("words_per_phrase", 2))
        fontsize_ass = int(style_conf.get("fontsize", 60))
        fontname = style_conf.get("font", "DejaVu Sans")
        
        # Get colors from style config (ASS format: &HAABBGGRR)
        primary_color = style_conf.get("primary_color", "&H00FFFFFF")
        outline_color = style_conf.get("outline_color", "&H00000000")
        
        # Get shadow and animation settings
        shadow = int(style_conf.get("shadow", 0))
        use_pop_animation = style_conf.get("use_pop_animation", False)

        # позиция: 2 — низ по центру; 8 — центр
        align = 8 if subtitle_position == "center" else 2
        margin_v = 100 if subtitle_position == "bottom" else max(50, height // 2 - 50)

        # генерим .ass
        ass_dir = tempfile.mkdtemp(prefix="ass_")
        ass_path = os.path.join(ass_dir, "subs.ass")
        ass_path = build_ass_from_words(
            timed_words,
            resolution=resolution,
            words_per_phrase=words_per_phrase,
            fontname=fontname,
            fontsize=fontsize_ass,
            primary_color=primary_color,
            outline_color=outline_color,
            outline=int(style_conf.get("borderw", 4)),
            shadow=shadow,
            margin_v=margin_v,
            align=align,
            out_path=ass_path,
            use_pop_animation=use_pop_animation,
        )

        # добавляем libass на финальный поток
        video_filter = (
            f"{video_filter},subtitles='{ass_path}':"
            f"fontsdir='/usr/share/fonts/truetype/dejavu:/usr/share/fonts/truetype/liberation',"
            f"format=yuv420p"
        )
    else:
        # без субтитров — просто приводим к нужному формату в конце
        video_filter = f"{video_filter},format=yuv420p"

    # 5) Команда ffmpeg (НИКАКОГО -r/-fps_mode снаружи)
    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_path,
        "-i", audio_path,
        "-vf", video_filter,            # fps=30 и subtitles уже внутри графа
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        output_path,
    ]

    logger.info("Running FFmpeg command: " + " ".join(shlex.quote(c) for c in cmd))

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            logger.error("FFmpeg error: " + proc.stderr)
            raise Exception(f"FFmpeg failed: {proc.stderr[:1000]}")
    finally:
        # concat-файл временный, но пусть система тоже чистит по своим правилам
        try:
            os.remove(concat_path)
        except Exception:
            pass

    logger.info("✅ Slideshow video created: " + output_path)
    return output_path

async def create_video_with_images(
    text: str,
    audio_path: str,
    audio_duration: float,
    output_path: str,
    video_type: str,
    progress_callback=None,
    subtitle_enabled: bool = False,
    subtitle_style: str = "tiktok",
    subtitle_position: str = "center"
) -> str:
    """
    Main function to create video from text and audio using images.
    Used for youtube_images and shorts types.
    
    Args:
        text: The text content
        audio_path: Path to audio file
        audio_duration: Audio duration in seconds
        output_path: Path for output video
        video_type: Type of video (youtube_images or shorts)
        progress_callback: Async function for progress updates
        subtitle_enabled: Whether to add subtitles
        subtitle_style: Subtitle style (tiktok, instagram, minimal)
        subtitle_position: Subtitle position (center, bottom)
        
    Returns:
        Path to created video file
    """
    try:
        settings = VIDEO_SETTINGS[video_type]
        resolution = settings["resolution"]
        images_per_minute = settings["images_per_minute"]
        
        # Calculate number of images needed
        duration_minutes = audio_duration / 60
        num_images = max(3, int(duration_minutes * images_per_minute))  # At least 3 images
        
        logger.info(f"Creating {video_type} video: {num_images} images for {audio_duration:.1f}s audio")
        if subtitle_enabled:
            logger.info(f"Subtitles enabled: style={subtitle_style}, position={subtitle_position}")
        
        # Create temp directory for images
        temp_dir = tempfile.mkdtemp(prefix="video_images_")
        
        try:
            # Step 1: Generate prompts
            if progress_callback:
                await progress_callback(
                    "prompt_generation",
                    0,
                    100,
                    "Создание промптов для изображений..."
                )
            
            prompts = await generate_image_prompts_from_text(text, num_images, video_type)
            
            # Step 2: Generate images
            image_paths = await generate_images_for_video(
                prompts,
                resolution[0],
                resolution[1],
                temp_dir,
                progress_callback
            )
            
            # Step 3: Create video
            video_path = await create_slideshow_video(
                image_paths=image_paths,
                audio_path=audio_path,
                resolution=resolution,
                subtitle_text=(text if subtitle_enabled else None),
                subtitle_style=(subtitle_style if subtitle_enabled else None),
                subtitle_position=subtitle_position,
                output_path=output_path,
            )
            
            return video_path
            
        finally:
            # Cleanup temp images
            try:
                logger.info(f"Video generation complete. Temp directory {temp_dir} will be cleaned up automatically after 2 hours")
            except Exception as e:
                pass
    
    except Exception as e:
        logger.error(f"Error in create_video_with_images: {e}")
        raise


async def create_continuous_video(
    text: str,
    audio_path: str,
    audio_duration: float,
    output_path: str,
    progress_callback=None
) -> str:
    """
    Create continuous video (Sora-like) from text and audio.
    This is more complex and slower - uses text-to-video models.
    
    Note: This will be VERY slow on CPU without GPU.
    
    Args:
        text: The text content
        audio_path: Path to audio file
        audio_duration: Audio duration in seconds
        output_path: Path for output video
        progress_callback: Async function for progress updates
        
    Returns:
        Path to created video file
    """
    try:
        settings = VIDEO_SETTINGS["youtube_continuous"]
        resolution = settings["resolution"]
        clip_duration = settings["clip_duration"]
        
        # Calculate number of clips needed
        num_clips = max(1, int(audio_duration / clip_duration))
        
        logger.info(f"Creating continuous video: {num_clips} clips of {clip_duration}s each")
        
        if progress_callback:
            await progress_callback(
                "video_generation",
                0,
                100,
                f"⚠️ Генерация непрерывного видео (это займет много времени)..."
            )
        
        # For now, fallback to image-based approach as text-to-video is too slow on CPU
        # In production with GPU, you could use models like ModelScope or AnimateDiff
        logger.warning("Continuous video generation is not yet implemented. Falling back to image slideshow.")
        
        # Use image-based approach with more images for smoother video
        return await create_video_with_images(
            text,
            audio_path,
            audio_duration,
            output_path,
            "youtube_images",  # Use youtube_images settings
            progress_callback
        )
        
    except Exception as e:
        logger.error(f"Error in create_continuous_video: {e}")
        raise


def get_video_duration(video_path: str) -> float:
    """Get video duration using ffprobe"""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        return duration
    except Exception as e:
        logger.error(f"Error getting video duration: {e}")
        return 0.0

import time 
async def cleanup_old_video_temp_directories(max_age_hours: float = 2.0):
    """
    Clean up old video temp directories that are older than max_age_hours.
    This runs as a background task to prevent immediate cleanup during video generation.
    
    For video generation with many images (e.g., 278 images), generation can take
    80+ minutes, so we need to keep temp directories for a long time.
    
    Args:
        max_age_hours: Maximum age in hours before cleanup (default: 2 hours = 120 minutes)
    """
    try:
        import shutil
        max_age_seconds = max_age_hours * 3600
        current_time = time.time()
        
        # Check /tmp for video_images_* directories
        tmp_dir = Path("/tmp")
        cleaned_count = 0
        
        for temp_dir in tmp_dir.glob("video_images_*"):
            if not temp_dir.is_dir():
                continue
            
            try:
                # Get directory creation/modification time
                dir_mtime = temp_dir.stat().st_mtime
                age_seconds = current_time - dir_mtime
                
                # Only cleanup if older than max_age
                if age_seconds > max_age_seconds:
                    shutil.rmtree(temp_dir)
                    age_minutes = age_seconds / 60
                    logger.info(f"🧹 Cleaned up old temp directory: {temp_dir.name} (age: {age_minutes:.1f} minutes)")
                    cleaned_count += 1
                else:
                    age_minutes = age_seconds / 60
                    logger.debug(f"⏳ Keeping temp directory: {temp_dir.name} (age: {age_minutes:.1f} minutes, max: {max_age_hours*60:.1f} minutes)")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory {temp_dir.name}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"✅ Cleaned up {cleaned_count} old video temp directories")
        else:
            logger.debug(f"No old video temp directories to clean (max age: {max_age_hours} hours)")
            
    except Exception as e:
        logger.error(f"Error in cleanup_old_video_temp_directories: {e}")

async def start_video_cleanup_task(interval_minutes: int = 30, max_age_hours: float = 2.0):
    """
    Background task that periodically cleans up old video temp directories.
    
    Args:
        interval_minutes: How often to run cleanup (default: 30 minutes)
        max_age_hours: Maximum age before cleanup (default: 2 hours)
    """
    logger.info(f"🚀 Started video temp directory cleanup task (interval: {interval_minutes}min, max_age: {max_age_hours}h)")
    
    while True:
        try:
            await asyncio.sleep(interval_minutes * 60)
            await cleanup_old_video_temp_directories(max_age_hours)
        except asyncio.CancelledError:
            logger.info("Video cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in video cleanup task: {e}")
            # Continue running even if cleanup fails
            await asyncio.sleep(60)  # Wait 1 minute before retry
