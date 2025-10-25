#!/usr/bin/env python3
"""
Analyze word count accuracy for different durations
"""

import requests
import json
import time
import urllib.parse

def test_text_generation_sse(duration_minutes, prompt="История космоса"):
    """Test text generation via SSE and return word count analysis"""
    base_url = "https://google-oauth-app.preview.emergentagent.com/api"
    url = f"{base_url}/text/generate-with-progress"
    
    params = {
        'prompt': prompt,
        'duration_minutes': duration_minutes,
        'language': 'ru-RU'
    }
    
    # Build curl command for SSE
    param_string = "&".join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()])
    full_url = f"{url}?{param_string}"
    curl_cmd = f'curl -s --no-buffer "{full_url}"'
    
    print(f"Testing {duration_minutes} minute(s) text generation...")
    
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
        
        while True:
            line = process.stdout.readline()
            if not line:
                break
                
            line = line.strip()
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    if data.get('type') == 'complete':
                        process.kill()
                        
                        word_count = data.get('word_count', 0)
                        expected_words = duration_minutes * 150
                        accuracy = (word_count / expected_words) * 100 if expected_words > 0 else 0
                        
                        result = {
                            'duration_minutes': duration_minutes,
                            'expected_words': expected_words,
                            'actual_words': word_count,
                            'accuracy_percent': accuracy,
                            'generation_time': time.time() - start_time,
                            'text_preview': data.get('text', '')[:200]
                        }
                        
                        print(f"  Expected: {expected_words} words")
                        print(f"  Actual: {word_count} words")
                        print(f"  Accuracy: {accuracy:.1f}%")
                        print(f"  Time: {result['generation_time']:.1f}s")
                        print()
                        
                        return result
                        
                except json.JSONDecodeError:
                    continue
        
        process.kill()
        return None
        
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    print("🔍 WORD COUNT ACCURACY ANALYSIS")
    print("=" * 50)
    
    # Test different durations
    test_cases = [
        (1, "История космоса"),
        (2, "Развитие технологий"),
        (5, "Искусственный интеллект")
    ]
    
    results = []
    
    for duration, prompt in test_cases:
        result = test_text_generation_sse(duration, prompt)
        if result:
            results.append(result)
        time.sleep(2)  # Brief pause between tests
    
    # Analysis
    print("📊 SUMMARY")
    print("=" * 50)
    
    for result in results:
        duration = result['duration_minutes']
        accuracy = result['accuracy_percent']
        
        if 90 <= accuracy <= 110:
            status = "✅ GOOD"
        elif 80 <= accuracy <= 120:
            status = "⚠️  ACCEPTABLE"
        else:
            status = "❌ POOR"
        
        print(f"{duration} min: {result['actual_words']}/{result['expected_words']} words ({accuracy:.1f}%) {status}")
    
    # Check if 1-minute generation is the main issue
    one_min_result = next((r for r in results if r['duration_minutes'] == 1), None)
    if one_min_result and one_min_result['accuracy_percent'] > 120:
        print("\n🔥 CRITICAL ISSUE CONFIRMED:")
        print(f"1-minute generation produces {one_min_result['accuracy_percent']:.1f}% of expected words")
        print("This explains why user reported 1531 words for 1 minute (should be ~150)")

if __name__ == "__main__":
    main()