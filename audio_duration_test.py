#!/usr/bin/env python3
"""
Test audio generation duration and download functionality
"""

import requests
import json
import time
import urllib.parse

def test_audio_generation_sse(text, voice="ru_RU-irina-medium"):
    """Test audio generation via SSE"""
    base_url = "https://backend-memory-fix.preview.emergentagent.com/api"
    url = f"{base_url}/audio/synthesize-with-progress"
    
    params = {
        'text': text,
        'voice': voice,
        'rate': 1.0,
        'language': 'ru-RU'
    }
    
    # Build curl command for SSE
    param_string = "&".join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()])
    full_url = f"{url}?{param_string}"
    curl_cmd = f'curl -s --no-buffer "{full_url}"'
    
    print(f"Testing audio generation for {len(text)} characters...")
    
    try:
        import subprocess
        process = subprocess.Popen(
            curl_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        start_time = time.time()
        progress_events = []
        
        while True:
            line = process.stdout.readline()
            if not line:
                break
                
            line = line.strip()
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    progress = data.get('progress', 0)
                    progress_events.append(progress)
                    
                    if data.get('type') == 'complete':
                        process.kill()
                        
                        audio_id = data.get('audio_id')
                        duration = data.get('duration', 0)
                        generation_time = time.time() - start_time
                        
                        # Check progress sequence
                        max_progress = max(progress_events) if progress_events else 0
                        progress_reached_100 = max_progress == 100
                        progress_stuck_at_90 = 90 in progress_events and max_progress < 100
                        
                        result = {
                            'audio_id': audio_id,
                            'duration': duration,
                            'generation_time': generation_time,
                            'progress_reached_100': progress_reached_100,
                            'progress_stuck_at_90': progress_stuck_at_90,
                            'max_progress': max_progress,
                            'text_length': len(text)
                        }
                        
                        print(f"  Audio ID: {audio_id}")
                        print(f"  Duration: {duration:.2f}s")
                        print(f"  Generation time: {generation_time:.2f}s")
                        print(f"  Progress reached 100%: {progress_reached_100}")
                        print(f"  Progress stuck at 90%: {progress_stuck_at_90}")
                        print()
                        
                        return result
                        
                except json.JSONDecodeError:
                    continue
        
        process.kill()
        return None
        
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_audio_download(audio_id):
    """Test audio download"""
    if not audio_id:
        return False
        
    base_url = "https://backend-memory-fix.preview.emergentagent.com/api"
    url = f"{base_url}/audio/download/{audio_id}"
    
    try:
        response = requests.get(url, timeout=30)
        
        success = response.status_code == 200
        content_length = len(response.content) if hasattr(response, 'content') else 0
        content_type = response.headers.get('content-type', '')
        
        print(f"  Download status: {response.status_code}")
        print(f"  File size: {content_length:,} bytes")
        print(f"  Content type: {content_type}")
        print(f"  Download successful: {success and content_length > 1000}")
        print()
        
        return success and content_length > 1000
        
    except Exception as e:
        print(f"  Download error: {e}")
        return False

def main():
    print("🔍 AUDIO GENERATION & DOWNLOAD TESTING")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        "Привет мир это короткий тест",
        "Это более длинный текст для тестирования системы синтеза речи. Мы проверяем как работает генерация аудио и показывается ли правильная длительность файла.",
        "Очень длинный текст для проверки системы. Искусственный интеллект развивается быстрыми темпами. Машинное обучение позволяет создавать удивительные приложения. Нейронные сети моделируют работу человеческого мозга. Глубокое обучение открывает новые возможности в различных областях науки и техники."
    ]
    
    results = []
    
    for i, text in enumerate(test_cases, 1):
        print(f"TEST {i}: {len(text)} characters")
        print("-" * 30)
        
        # Generate audio
        audio_result = test_audio_generation_sse(text)
        if audio_result:
            results.append(audio_result)
            
            # Test download
            print("Testing download...")
            download_success = test_audio_download(audio_result['audio_id'])
            audio_result['download_success'] = download_success
        
        time.sleep(2)  # Brief pause between tests
    
    # Summary
    print("📊 SUMMARY")
    print("=" * 50)
    
    all_duration_ok = True
    all_progress_ok = True
    all_download_ok = True
    
    for i, result in enumerate(results, 1):
        duration_ok = result['duration'] > 0
        progress_ok = result['progress_reached_100'] and not result['progress_stuck_at_90']
        download_ok = result.get('download_success', False)
        
        if not duration_ok:
            all_duration_ok = False
        if not progress_ok:
            all_progress_ok = False
        if not download_ok:
            all_download_ok = False
        
        print(f"Test {i}: Duration OK: {duration_ok}, Progress OK: {progress_ok}, Download OK: {download_ok}")
    
    print()
    print("🎯 CRITICAL FIXES STATUS:")
    print(f"✅ Audio shows real duration (not 0:00): {all_duration_ok}")
    print(f"✅ Progress reaches 100% (not stuck at 90%): {all_progress_ok}")
    print(f"✅ Audio download works: {all_download_ok}")
    
    if all_duration_ok and all_progress_ok and all_download_ok:
        print("\n🎉 ALL AUDIO FIXES WORKING CORRECTLY!")
    else:
        print("\n❌ SOME AUDIO ISSUES REMAIN")

if __name__ == "__main__":
    main()