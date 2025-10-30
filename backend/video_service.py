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
import tempfile
import subprocess
import urllib.parse
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

POLLINATIONS_API_URL = "https://image.pollinations.ai/prompt"

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
    
    max_retries = 3
    retry_delay = 2
    import urllib.parse
    encoded_prompt = urllib.parse.quote(prompt)
    api_url = f"{POLLINATIONS_API_URL}/{encoded_prompt}?width={width}&height={height}&nologo=true&enhance=true"
    for attempt in range(max_retries):
        try:
            logger.info(f"Pollinations.ai attempt {attempt+1}/{max_retries} for: {prompt[:50]}...")
            async with session.get(api_url, timeout=60 as response:
                if response.status == 200:
                    image_data = await response.read()
                    logger.info(f\"✅ Pollinations.ai generated image successfully ({len(image_data)} bytes)\")
                    return image_data
                else:
                    err_text = await response.text()
                    logger.warning(f"Pollinations.ai attempt {attempt+1}/{max_retries} failed: {response.status} - {err_text[:100]}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue
        except asyncio.TimeoutError:
            logger.warning(f"Timeout on Pollinations.ai attempt {attempt+1}/{max_retries}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (attempt + 1))
                continue
        except Exception as e:
            logger.error(f"Error on Pollinations.ai attempt {attempt+1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (attempt + 1))
                continue
    raise Exception(f"Pollinations.ai image generation failed after {max_retries} attempts")

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
    image_paths = []
    
    async with aiohttp.ClientSession() as session:
        for i, prompt in enumerate(prompts):
            try:
                if progress_callback:
                    await progress_callback(
                        "image_generation",
                        i + 1,
                        len(prompts),
                        f"Генерация изображения {i + 1}/{len(prompts)}"
                    )
                
                logger.info(f"Generating image {i + 1}/{len(prompts)}: {prompt[:50]}...")
                
                # Generate image
                image_data = await generate_image_with_pollinations(prompt, width, height, session)
                
                # Save image
                image_path = os.path.join(output_dir, f"image_{i:04d}.png")
                with open(image_path, "wb") as f:
                    f.write(image_data)
                
                image_paths.append(image_path)
                logger.info(f"Saved image {i + 1} to {image_path}")
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error generating image {i + 1}: {e}")
                # Create a placeholder black image on error
                placeholder_path = os.path.join(output_dir, f"image_{i:04d}.png")
                create_placeholder_image(placeholder_path, width, height, f"Error: {str(e)[:50]}")
                image_paths.append(placeholder_path)
    
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


async def create_slideshow_video(
    image_paths: List[str],
    audio_path: str,
    output_path: str,
    audio_duration: float,
    resolution: Tuple[int, int],
    progress_callback=None
) -> str:
    """
    Create a slideshow video from images with audio using FFmpeg.
    Images will be displayed evenly across the audio duration with smooth transitions.
    
    Args:
        image_paths: List of image file paths
        audio_path: Path to audio file
        output_path: Path for output video
        audio_duration: Duration of audio in seconds
        resolution: Video resolution (width, height)
        progress_callback: Async function for progress updates
        
    Returns:
        Path to created video file
    """
    try:
        if progress_callback:
            await progress_callback(
                "video_creation",
                0,
                100,
                "Создание видео из изображений..."
            )
        
        # Calculate duration per image
        num_images = len(image_paths)
        duration_per_image = audio_duration / num_images
        
        logger.info(f"Creating slideshow: {num_images} images, {duration_per_image:.2f}s per image")
        
        # Create a concat file for FFmpeg
        concat_file = output_path + ".concat.txt"
        with open(concat_file, "w") as f:
            for img_path in image_paths:
                f.write(f"file '{img_path}'\n")
                f.write(f"duration {duration_per_image}\n")
            # Add last image again (FFmpeg concat demuxer requirement)
            f.write(f"file '{image_paths[-1]}'\n")
        
        # FFmpeg command with transitions and audio
        width, height = resolution
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-i", audio_path,
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            "-y",
            output_path
        ]
        
        logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
        
        # Run FFmpeg
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(f"FFmpeg error: {error_msg}")
            raise Exception(f"FFmpeg failed: {error_msg[:200]}")
        
        # Clean up concat file
        os.remove(concat_file)
        
        if progress_callback:
            await progress_callback(
                "video_creation",
                100,
                100,
                "Видео создано успешно!"
            )
        
        logger.info(f"Video created successfully: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error creating slideshow video: {e}")
        raise


async def create_video_with_images(
    text: str,
    audio_path: str,
    audio_duration: float,
    output_path: str,
    video_type: str,
    progress_callback=None
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
                image_paths,
                audio_path,
                output_path,
                audio_duration,
                resolution,
                progress_callback
            )
            
            return video_path
            
        finally:
            # Cleanup temp images
            try:
                import shutil
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory: {e}")
    
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
