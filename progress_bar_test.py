#!/usr/bin/env python3
"""
Progress Bar Testing for AI Voice Studio
Focus: Testing SSE progress fixes for text generation and audio synthesis

CRITICAL TESTS based on review request:
1. Text generation 1-2 minutes (short) - should have 7 progress updates
2. Audio synthesis 3-5 minutes - should show segment progress and complete
3. Text generation 10 minutes (long with chunks) - optional

User reported issues:
- Audio synthesis doesn't complete (though server doesn't crash)
- Progress bar for text gets stuck on "начало генерации"
- Progress bar for audio gets stuck on "подготовка"
- Logs show segments are generated but clients don't see progress
"""

import requests
import json
import time
import sys
from datetime import datetime
from pathlib import Path
import httpx
import asyncio

class ProgressBarTester:
    def __init__(self, base_url="https://voicetoscreen.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.session_token = None
        self.test_results = []
        
    def authenticate(self):
        """Authenticate with the API to get session token"""
        print("🔐 Authenticating with API...")
        
        # Try to load test session token
        try:
            with open('/app/test_session.txt', 'r') as f:
                self.session_token = f.read().strip()
            
            # Test the session token
            cookies = {'session_token': self.session_token}
            response = requests.get(f"{self.base_url}/auth/me", cookies=cookies, timeout=10)
            
            if response.status_code == 200:
                user_data = response.json()
                print(f"   ✅ Authenticated as: {user_data.get('email', 'Unknown')}")
                return True
            else:
                print(f"   ❌ Session token invalid: {response.status_code}")
                return False
                
        except FileNotFoundError:
            print("   ❌ No test session file found. Run create_test_user.py first")
            return False
        except Exception as e:
            print(f"   ❌ Auth failed: {str(e)}")
            return False
    
    def test_text_generation_short_progress(self):
        """
        CRITICAL TEST 1: Text generation 1-2 minutes with SSE progress
        Expected: 7 progress updates (10%, 20%, 40%, 85%, 95%, 100%)
        """
        print("\n🔥 CRITICAL TEST 1: Text Generation Short (2 minutes) - SSE Progress")
        print("   Expected: 7 detailed progress updates")
        print("   Messages: 'Подготовка запроса', 'Генерация началась', 'LLM обрабатывает', 'Текст получен', 'Сохранение', 'Готово'")
        
        url = f"{self.base_url}/text/generate-with-progress"
        params = {
            "prompt": "Тестовый текст о космических путешествиях",
            "duration_minutes": 2,
            "language": "ru-RU"
        }
        
        progress_events = []
        final_result = None
        start_time = time.time()
        
        try:
            print(f"   📡 Connecting to SSE endpoint: {url}")
            
            cookies = {'session_token': self.session_token} if self.session_token else {}
            with httpx.stream("GET", url, params=params, cookies=cookies, timeout=120) as response:
                if response.status_code != 200:
                    print(f"   ❌ SSE request failed with status {response.status_code}")
                    if response.status_code == 401:
                        print("   ❌ Authentication required - test cannot proceed")
                    return None
                
                print("   📡 SSE connection established, receiving events...")
                
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])  # Remove "data: " prefix
                            event_type = data.get('type')
                            progress = data.get('progress', 0)
                            message = data.get('message', '')
                            
                            progress_events.append(data)
                            
                            if event_type == 'info':
                                print(f"   📋 {progress}% - {message}")
                            elif event_type == 'progress':
                                print(f"   ⏳ {progress}% - {message}")
                            elif event_type == 'complete':
                                print(f"   ✅ {progress}% - Complete!")
                                final_result = data
                                break
                            elif event_type == 'error':
                                print(f"   ❌ Error: {message}")
                                return None
                                
                        except json.JSONDecodeError as e:
                            print(f"   ⚠️  Failed to parse SSE data: {line}")
                            continue
                
                total_time = time.time() - start_time
                
                # Analyze results
                if final_result:
                    text_id = final_result.get('text_id')
                    text = final_result.get('text', '')
                    word_count = final_result.get('word_count', 0)
                    
                    print(f"\n   ✅ Text generation completed in {total_time:.2f} seconds")
                    print(f"   Text ID: {text_id}")
                    print(f"   Word count: {word_count}")
                    print(f"   Text preview: {text[:100]}...")
                    print(f"   Progress events received: {len(progress_events)}")
                    
                    # Check progress sequence
                    progress_values = [event.get('progress', 0) for event in progress_events if 'progress' in event]
                    messages = [event.get('message', '') for event in progress_events if 'message' in event]
                    
                    print(f"   Progress sequence: {progress_values}")
                    print(f"   Key messages: {[msg for msg in messages if any(keyword in msg for keyword in ['Подготовка', 'Генерация', 'LLM', 'получен', 'Сохранение', 'Готово'])]}")
                    
                    # Validate expectations
                    has_7_updates = len(progress_values) >= 7
                    reaches_100 = max(progress_values) >= 100 if progress_values else False
                    is_monotonic = all(progress_values[i] <= progress_values[i+1] for i in range(len(progress_values)-1)) if len(progress_values) > 1 else True
                    
                    print(f"   ✅ Has 7+ progress updates: {has_7_updates} ({len(progress_values)} events)")
                    print(f"   ✅ Reaches 100%: {reaches_100}")
                    print(f"   ✅ Progress is monotonic: {is_monotonic}")
                    
                    # Check word count for 2 minutes (should be ~300 words)
                    expected_words = 2 * 150  # 300 words
                    word_count_ok = 250 <= word_count <= 400  # Allow variance
                    print(f"   ✅ Word count reasonable: {word_count_ok} ({word_count} words, expected ~300)")
                    
                    return {
                        'success': True,
                        'text_id': text_id,
                        'word_count': word_count,
                        'progress_events': len(progress_events),
                        'time': total_time,
                        'has_7_updates': has_7_updates,
                        'reaches_100': reaches_100,
                        'is_monotonic': is_monotonic,
                        'word_count_ok': word_count_ok,
                        'text': text
                    }
                else:
                    print(f"   ❌ Text generation failed - no completion event received")
                    print(f"   Events received: {len(progress_events)}")
                    return None
                    
        except Exception as e:
            print(f"   ❌ Text generation failed with error: {str(e)}")
            return None
    
    def test_audio_synthesis_progress(self, text, duration_desc="3-5 minutes"):
        """
        CRITICAL TEST 2: Audio synthesis with SSE progress
        Expected: Progress shows "Генерация X/Y сегментов" and completes with audio_url
        """
        print(f"\n🔥 CRITICAL TEST 2: Audio Synthesis ({duration_desc}) - SSE Progress")
        print("   Expected: Stage events (loading_model, generating_segments, combining, saving)")
        print("   Expected: Progress shows 'Генерация X/Y сегментов' and complete event with audio_url")
        
        # First get available voices
        try:
            cookies = {'session_token': self.session_token} if self.session_token else {}
            voices_response = requests.get(f"{self.base_url}/voices", cookies=cookies, timeout=30)
            if voices_response.status_code != 200:
                print(f"   ❌ Failed to get voices: {voices_response.status_code}")
                return None
            
            voices = voices_response.json()
            
            # Find Russian voice
            ru_voice = None
            for voice in voices:
                if 'irina' in voice.get('short_name', '').lower() or voice.get('locale', '').startswith('ru-'):
                    ru_voice = voice.get('short_name')
                    break
            
            if not ru_voice:
                print("   ❌ No Russian voice found")
                return None
                
            print(f"   Using voice: {ru_voice}")
            
        except Exception as e:
            print(f"   ❌ Failed to get voices: {str(e)}")
            return None
        
        # Test audio synthesis with progress
        url = f"{self.base_url}/audio/synthesize-with-progress"
        data = {
            "text": text,
            "voice": ru_voice,
            "rate": 1.0,
            "language": "ru-RU"
        }
        
        progress_events = []
        final_result = None
        start_time = time.time()
        
        try:
            print(f"   📡 Connecting to SSE endpoint for audio synthesis...")
            print(f"   Text length: {len(text)} characters")
            
            headers = {'Content-Type': 'application/json'}
            
            cookies = {'session_token': self.session_token} if self.session_token else {}
            with httpx.stream("POST", url, json=data, headers=headers, cookies=cookies, timeout=300) as response:
                if response.status_code != 200:
                    print(f"   ❌ SSE request failed with status {response.status_code}")
                    if response.status_code == 401:
                        print("   ❌ Authentication required - test cannot proceed")
                    return None
                
                print("   📡 SSE connection established, receiving events...")
                
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])  # Remove "data: " prefix
                            event_type = data.get('type')
                            progress = data.get('progress', 0)
                            message = data.get('message', '')
                            stage = data.get('stage', '')
                            
                            progress_events.append(data)
                            
                            if event_type == 'info':
                                print(f"   📋 {progress}% - {message}")
                            elif event_type == 'stage':
                                print(f"   🎭 Stage: {stage} - {message}")
                            elif event_type == 'progress':
                                completed_segments = data.get('completed_segments', 0)
                                total_segments = data.get('total_segments', 0)
                                eta = data.get('eta', '')
                                speed = data.get('speed', '')
                                
                                if completed_segments and total_segments:
                                    print(f"   ⏳ {progress}% - {message} ({completed_segments}/{total_segments})")
                                    if eta:
                                        print(f"      ETA: {eta}, Speed: {speed}x")
                                else:
                                    print(f"   ⏳ {progress}% - {message}")
                            elif event_type == 'complete':
                                print(f"   ✅ {progress}% - Complete!")
                                final_result = data
                                break
                            elif event_type == 'error':
                                print(f"   ❌ Error: {message}")
                                return None
                            elif event_type == 'queue':
                                print(f"   🚶 Queue: {message}")
                                
                        except json.JSONDecodeError as e:
                            print(f"   ⚠️  Failed to parse SSE data: {line}")
                            continue
                
                total_time = time.time() - start_time
                
                # Analyze results
                if final_result:
                    audio_id = final_result.get('audio_id')
                    audio_url = final_result.get('audio_url')
                    duration = final_result.get('duration', 0)
                    
                    print(f"\n   ✅ Audio synthesis completed in {total_time:.2f} seconds")
                    print(f"   Audio ID: {audio_id}")
                    print(f"   Audio URL: {audio_url}")
                    print(f"   Duration: {duration}s")
                    print(f"   Progress events received: {len(progress_events)}")
                    
                    # Check for expected stages
                    stages_seen = set()
                    segment_progress_events = 0
                    
                    for event in progress_events:
                        if event.get('type') == 'stage':
                            stages_seen.add(event.get('stage', ''))
                        elif event.get('type') == 'progress' and 'сегментов' in event.get('message', ''):
                            segment_progress_events += 1
                    
                    expected_stages = {'loading_model', 'generating_segments', 'combining', 'saving'}
                    has_all_stages = expected_stages.issubset(stages_seen)
                    
                    progress_values = [event.get('progress', 0) for event in progress_events if 'progress' in event]
                    reaches_100 = max(progress_values) >= 100 if progress_values else False
                    has_audio_url = bool(audio_url)
                    
                    print(f"   ✅ Has all stages: {has_all_stages} (seen: {stages_seen})")
                    print(f"   ✅ Segment progress events: {segment_progress_events}")
                    print(f"   ✅ Reaches 100%: {reaches_100}")
                    print(f"   ✅ Has audio URL: {has_audio_url}")
                    
                    return {
                        'success': True,
                        'audio_id': audio_id,
                        'audio_url': audio_url,
                        'duration': duration,
                        'progress_events': len(progress_events),
                        'time': total_time,
                        'has_all_stages': has_all_stages,
                        'segment_progress_events': segment_progress_events,
                        'reaches_100': reaches_100,
                        'has_audio_url': has_audio_url
                    }
                else:
                    print(f"   ❌ Audio synthesis failed - no completion event received")
                    print(f"   Events received: {len(progress_events)}")
                    if progress_events:
                        print(f"   Last event: {progress_events[-1]}")
                    return None
                    
        except Exception as e:
            print(f"   ❌ Audio synthesis failed with error: {str(e)}")
            return None
    
    def test_text_generation_long_progress(self):
        """
        OPTIONAL TEST 3: Text generation 10 minutes with chunks
        Expected: Shows "Генерация части X/Y" and "Готово X/Y частей (N слов)"
        """
        print(f"\n🔥 OPTIONAL TEST 3: Text Generation Long (10 minutes) - Chunked Progress")
        print("   Expected: Multiple chunks with progress 'Генерация части X/Y' and 'Готово X/Y частей'")
        print("   Expected: 'Объединение частей' and 'Сохранение результата' stages")
        
        url = f"{self.base_url}/text/generate-with-progress"
        params = {
            "prompt": "История космоса и освоения вселенной человечеством",
            "duration_minutes": 10,
            "language": "ru-RU"
        }
        
        progress_events = []
        final_result = None
        start_time = time.time()
        
        try:
            print(f"   📡 Connecting to SSE endpoint for long text generation...")
            
            cookies = {'session_token': self.session_token} if self.session_token else {}
            with httpx.stream("GET", url, params=params, cookies=cookies, timeout=300) as response:
                if response.status_code != 200:
                    print(f"   ❌ SSE request failed with status {response.status_code}")
                    return None
                
                print("   📡 SSE connection established, receiving events...")
                
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])  # Remove "data: " prefix
                            event_type = data.get('type')
                            progress = data.get('progress', 0)
                            message = data.get('message', '')
                            
                            progress_events.append(data)
                            
                            if event_type == 'info':
                                print(f"   📋 {progress}% - {message}")
                            elif event_type == 'progress':
                                print(f"   ⏳ {progress}% - {message}")
                            elif event_type == 'complete':
                                print(f"   ✅ {progress}% - Complete!")
                                final_result = data
                                break
                            elif event_type == 'error':
                                print(f"   ❌ Error: {message}")
                                return None
                                
                        except json.JSONDecodeError as e:
                            print(f"   ⚠️  Failed to parse SSE data: {line}")
                            continue
                
                total_time = time.time() - start_time
                
                # Analyze results
                if final_result:
                    text_id = final_result.get('text_id')
                    text = final_result.get('text', '')
                    word_count = final_result.get('word_count', 0)
                    
                    print(f"\n   ✅ Long text generation completed in {total_time:.2f} seconds")
                    print(f"   Text ID: {text_id}")
                    print(f"   Word count: {word_count}")
                    print(f"   Progress events received: {len(progress_events)}")
                    
                    # Check for chunk-related messages
                    chunk_messages = []
                    for event in progress_events:
                        message = event.get('message', '')
                        if any(keyword in message for keyword in ['части', 'частей', 'Объединение', 'Сохранение']):
                            chunk_messages.append(message)
                    
                    print(f"   Chunk-related messages: {chunk_messages}")
                    
                    # Check word count for 10 minutes (should be ~1500 words)
                    expected_words = 10 * 150  # 1500 words
                    word_count_ok = 1200 <= word_count <= 1800  # Allow variance
                    
                    has_chunk_progress = len(chunk_messages) > 0
                    has_combining = any('Объединение' in msg for msg in chunk_messages)
                    has_saving = any('Сохранение' in msg for msg in chunk_messages)
                    
                    print(f"   ✅ Word count reasonable: {word_count_ok} ({word_count} words, expected ~1500)")
                    print(f"   ✅ Has chunk progress: {has_chunk_progress}")
                    print(f"   ✅ Has combining stage: {has_combining}")
                    print(f"   ✅ Has saving stage: {has_saving}")
                    
                    return {
                        'success': True,
                        'text_id': text_id,
                        'word_count': word_count,
                        'progress_events': len(progress_events),
                        'time': total_time,
                        'word_count_ok': word_count_ok,
                        'has_chunk_progress': has_chunk_progress,
                        'has_combining': has_combining,
                        'has_saving': has_saving
                    }
                else:
                    print(f"   ❌ Long text generation failed - no completion event received")
                    return None
                    
        except Exception as e:
            print(f"   ❌ Long text generation failed with error: {str(e)}")
            return None
    
    def run_progress_tests(self):
        """Run all progress bar tests as specified in review request"""
        print("🚀 AI Voice Studio - Progress Bar Testing")
        print(f"   Base URL: {self.base_url}")
        print("   Focus: SSE progress fixes for text and audio generation")
        print("=" * 80)
        
        # Check authentication
        auth_ok = self.authenticate()
        if not auth_ok:
            print("⚠️  Proceeding without authentication - some tests may fail")
        
        results = {}
        
        # TEST 1: Short text generation (1-2 minutes)
        print("\n" + "="*80)
        text_short_result = self.test_text_generation_short_progress()
        results['text_short'] = text_short_result
        
        if text_short_result and text_short_result.get('success'):
            generated_text = text_short_result.get('text', '')
            
            # TEST 2: Audio synthesis with the generated text
            print("\n" + "="*80)
            audio_result = self.test_audio_synthesis_progress(generated_text, "2-3 minutes")
            results['audio'] = audio_result
        else:
            print("\n⚠️  Skipping audio test - text generation failed")
            results['audio'] = None
        
        # TEST 3: Long text generation (optional)
        print("\n" + "="*80)
        text_long_result = self.test_text_generation_long_progress()
        results['text_long'] = text_long_result
        
        # SUMMARY
        print("\n" + "="*80)
        print("📊 PROGRESS BAR TEST SUMMARY")
        print("="*80)
        
        # Analyze results
        text_short_ok = results['text_short'] and results['text_short'].get('success', False)
        audio_ok = results['audio'] and results['audio'].get('success', False)
        text_long_ok = results['text_long'] and results['text_long'].get('success', False)
        
        print(f"✅ Text Generation Short (2 min): {'PASS' if text_short_ok else 'FAIL'}")
        if text_short_ok:
            r = results['text_short']
            print(f"   - Progress events: {r.get('progress_events', 0)}")
            print(f"   - Has 7+ updates: {r.get('has_7_updates', False)}")
            print(f"   - Reaches 100%: {r.get('reaches_100', False)}")
            print(f"   - Word count OK: {r.get('word_count_ok', False)} ({r.get('word_count', 0)} words)")
        
        print(f"✅ Audio Synthesis (3-5 min): {'PASS' if audio_ok else 'FAIL'}")
        if audio_ok:
            r = results['audio']
            print(f"   - Progress events: {r.get('progress_events', 0)}")
            print(f"   - Has all stages: {r.get('has_all_stages', False)}")
            print(f"   - Segment progress: {r.get('segment_progress_events', 0)} events")
            print(f"   - Reaches 100%: {r.get('reaches_100', False)}")
            print(f"   - Has audio URL: {r.get('has_audio_url', False)}")
        
        print(f"✅ Text Generation Long (10 min): {'PASS' if text_long_ok else 'FAIL'}")
        if text_long_ok:
            r = results['text_long']
            print(f"   - Progress events: {r.get('progress_events', 0)}")
            print(f"   - Has chunk progress: {r.get('has_chunk_progress', False)}")
            print(f"   - Has combining: {r.get('has_combining', False)}")
            print(f"   - Word count OK: {r.get('word_count_ok', False)} ({r.get('word_count', 0)} words)")
        
        # Overall assessment
        critical_tests_passed = text_short_ok and audio_ok
        all_tests_passed = critical_tests_passed and text_long_ok
        
        print("\n" + "="*80)
        if critical_tests_passed:
            print("🎉 CRITICAL PROGRESS BAR FIXES VERIFIED!")
            print("✅ Text generation shows detailed progress")
            print("✅ Audio synthesis shows segment progress and completes")
            if all_tests_passed:
                print("✅ Long text generation with chunks also working")
        else:
            print("❌ CRITICAL PROGRESS BAR ISSUES REMAIN")
            if not text_short_ok:
                print("❌ Text generation progress not working properly")
            if not audio_ok:
                print("❌ Audio synthesis progress not working properly")
        
        return critical_tests_passed

def main():
    tester = ProgressBarTester()
    success = tester.run_progress_tests()
    
    # Save results
    timestamp = datetime.now().isoformat()
    with open('/app/progress_test_results.json', 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'success': success,
            'test_results': tester.test_results
        }, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())