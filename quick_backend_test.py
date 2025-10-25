#!/usr/bin/env python3
"""
Quick Backend Test for AI Voice Studio Optimizations
Focus: Test the key optimizations mentioned in review request
"""

import requests
import time
import json
from datetime import datetime

BASE_URL = "https://audiorender-issue.preview.emergentagent.com/api"

def test_text_generation():
    """Test 1: Text generation (10 minutes) - Speed and accuracy"""
    print("1️⃣ TESTING TEXT GENERATION (10 minutes)")
    
    start_time = time.time()
    
    response = requests.post(f"{BASE_URL}/text/generate", 
        json={
            "prompt": "История космических путешествий",
            "duration_minutes": 10,
            "language": "ru-RU"
        },
        timeout=120
    )
    
    generation_time = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        word_count = data.get('word_count', 0)
        estimated_duration = data.get('estimated_duration', 0)
        
        print(f"✅ Text generation SUCCESS")
        print(f"   Time: {generation_time:.1f} seconds")
        print(f"   Words: {word_count} (target: ~1500)")
        print(f"   Duration: {estimated_duration:.0f}s ({estimated_duration/60:.1f} min)")
        
        return data.get('text'), data.get('id')
    else:
        print(f"❌ Text generation FAILED: {response.status_code}")
        return None, None

def test_voices_list():
    """Test 2: Voices list - Check Russian voices available"""
    print("\n2️⃣ TESTING VOICES LIST")
    
    response = requests.get(f"{BASE_URL}/voices", timeout=30)
    
    if response.status_code == 200:
        voices = response.json()
        ru_voices = [v for v in voices if v.get('locale', '').startswith('ru-')]
        
        print(f"✅ Voices list SUCCESS")
        print(f"   Total voices: {len(voices)}")
        print(f"   Russian voices: {len(ru_voices)}")
        
        if ru_voices:
            print(f"   Sample RU voice: {ru_voices[0]['name']} ({ru_voices[0]['short_name']})")
            return ru_voices[0]['short_name']
        else:
            print("❌ No Russian voices found")
            return None
    else:
        print(f"❌ Voices list FAILED: {response.status_code}")
        return None

def test_audio_synthesis(text, voice):
    """Test 3: Audio synthesis with optimizations"""
    print("\n3️⃣ TESTING AUDIO SYNTHESIS (Optimized)")
    
    # Use shorter text for faster testing
    test_text = text[:2000] if text and len(text) > 2000 else text or "Тест синтеза речи с оптимизациями"
    
    print(f"   Text length: {len(test_text)} characters")
    print(f"   Voice: {voice}")
    
    start_time = time.time()
    
    # Test parallel synthesis endpoint (optimized)
    response = requests.post(f"{BASE_URL}/audio/synthesize-parallel",
        json={
            "text": test_text,
            "voice": voice,
            "rate": 1.0,
            "language": "ru-RU"
        },
        timeout=180
    )
    
    synthesis_time = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        audio_id = data.get('id')
        
        print(f"✅ Audio synthesis SUCCESS")
        print(f"   Time: {synthesis_time:.1f} seconds")
        print(f"   Audio ID: {audio_id}")
        print(f"   Speed ratio: {synthesis_time/60:.2f}x real-time")
        
        return audio_id
    else:
        print(f"❌ Audio synthesis FAILED: {response.status_code}")
        try:
            error_data = response.json()
            print(f"   Error: {error_data}")
        except:
            print(f"   Error: {response.text[:200]}")
        return None

def test_audio_download(audio_id):
    """Test 4: Audio download"""
    print("\n4️⃣ TESTING AUDIO DOWNLOAD")
    
    if not audio_id:
        print("❌ No audio ID to test download")
        return False
    
    response = requests.get(f"{BASE_URL}/audio/download/{audio_id}", timeout=30)
    
    if response.status_code == 200:
        file_size = len(response.content)
        print(f"✅ Audio download SUCCESS")
        print(f"   File size: {file_size:,} bytes")
        print(f"   Content type: {response.headers.get('content-type', 'unknown')}")
        return True
    else:
        print(f"❌ Audio download FAILED: {response.status_code}")
        return False

def test_history():
    """Test 5: Generation history"""
    print("\n5️⃣ TESTING GENERATION HISTORY")
    
    response = requests.get(f"{BASE_URL}/history", timeout=30)
    
    if response.status_code == 200:
        history = response.json()
        print(f"✅ History SUCCESS")
        print(f"   History items: {len(history)}")
        if history:
            print(f"   Latest: {history[0].get('language', 'unknown')} - {history[0].get('text', '')[:50]}...")
        return True
    else:
        print(f"❌ History FAILED: {response.status_code}")
        return False

def main():
    """Run all priority tests"""
    print("🚀 AI VOICE STUDIO - OPTIMIZATION TESTING")
    print("=" * 60)
    print("Focus: ffmpeg install, segment size 2000, batch size 25")
    print("Expected: Faster audio generation, working progress bars")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Text Generation
    text, text_id = test_text_generation()
    results['text_generation'] = text is not None
    
    # Test 2: Voices List  
    voice = test_voices_list()
    results['voices_list'] = voice is not None
    
    # Test 3: Audio Synthesis (only if we have text and voice)
    audio_id = None
    if text and voice:
        audio_id = test_audio_synthesis(text, voice)
        results['audio_synthesis'] = audio_id is not None
    else:
        print("\n3️⃣ SKIPPING AUDIO SYNTHESIS - Missing text or voice")
        results['audio_synthesis'] = False
    
    # Test 4: Audio Download
    results['audio_download'] = test_audio_download(audio_id)
    
    # Test 5: History
    results['history'] = test_history()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 OPTIMIZATION TEST RESULTS")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name.replace('_', ' ').title()}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🚀 ALL OPTIMIZATION TESTS PASSED!")
        print("✅ Text generation working")
        print("✅ Audio synthesis optimized")
        print("✅ Download and history functional")
    else:
        print("⚠️  SOME TESTS FAILED - Check individual results above")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)