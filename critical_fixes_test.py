#!/usr/bin/env python3
"""
Critical Fixes Testing for Text-to-Speech Service
Tests the specific issues mentioned in the review request:
1. Text generation for 1 minute should generate ~150 words (not 1531)
2. Audio synthesis should show real duration (not 0:00) and be downloadable  
3. Progress bars should reach 100% without getting stuck at 90%
"""

import requests
import json
import time
import sys
from pathlib import Path
import urllib.parse

class CriticalFixesTester:
    def __init__(self):
        # Use the frontend environment variable for backend URL
        self.base_url = "https://sub-status-display.preview.emergentagent.com/api"
        self.test_results = []
        
    def log_result(self, test_name, success, details=None, error=None):
        """Log test result"""
        result = {
            'test_name': test_name,
            'success': success,
            'details': details or {},
            'error': error,
            'timestamp': time.time()
        }
        self.test_results.append(result)
        
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {test_name}")
        if details:
            for key, value in details.items():
                print(f"   {key}: {value}")
        if error:
            print(f"   Error: {error}")
        print()
        
        return success

    def test_sse_endpoint(self, url, params, test_name, expected_events=None):
        """Test SSE endpoint with curl since Python SSE can be problematic"""
        print(f"🔍 Testing {test_name}...")
        print(f"   URL: {url}")
        print(f"   Params: {params}")
        
        # Build curl command for SSE
        param_string = "&".join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()])
        full_url = f"{url}?{param_string}"
        
        # Use curl with --no-buffer for SSE
        curl_cmd = f'curl -s --no-buffer "{full_url}"'
        
        try:
            import subprocess
            import signal
            
            # Start curl process
            process = subprocess.Popen(
                curl_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            events = []
            start_time = time.time()
            timeout = 300  # 5 minutes timeout
            
            print("   📡 SSE connection established, receiving events...")
            
            while True:
                # Check timeout
                if time.time() - start_time > timeout:
                    process.kill()
                    return self.log_result(test_name, False, error="Timeout after 5 minutes")
                
                # Read line with timeout
                try:
                    line = process.stdout.readline()
                    if not line:
                        # Process ended
                        break
                        
                    line = line.strip()
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])  # Remove "data: " prefix
                            events.append(data)
                            
                            event_type = data.get('type', 'unknown')
                            progress = data.get('progress', 0)
                            message = data.get('message', '')
                            
                            if event_type == 'info':
                                print(f"   📋 {progress}% - {message}")
                            elif event_type == 'progress':
                                print(f"   ⏳ {progress}% - {message}")
                            elif event_type == 'complete':
                                print(f"   ✅ {progress}% - Complete!")
                                # Process completed successfully
                                process.kill()
                                
                                total_time = time.time() - start_time
                                
                                # Analyze results
                                progress_values = [e.get('progress', 0) for e in events if 'progress' in e]
                                final_progress = data.get('progress', 0)
                                
                                details = {
                                    'total_time': f"{total_time:.2f}s",
                                    'events_received': len(events),
                                    'final_progress': f"{final_progress}%",
                                    'progress_sequence': f"{progress_values[:3]}...{progress_values[-3:] if len(progress_values) > 3 else ''}",
                                    'complete_event': data
                                }
                                
                                # Check if progress reached 100%
                                success = final_progress == 100
                                if not success:
                                    details['error'] = f"Progress did not reach 100% (got {final_progress}%)"
                                
                                return self.log_result(test_name, success, details), data
                                
                            elif event_type == 'error':
                                print(f"   ❌ Error: {message}")
                                process.kill()
                                return self.log_result(test_name, False, error=f"SSE error: {message}")
                                
                        except json.JSONDecodeError:
                            print(f"   ⚠️  Invalid JSON in SSE data: {line}")
                            continue
                            
                except Exception as e:
                    print(f"   ⚠️  Error reading SSE stream: {e}")
                    continue
            
            # If we get here, process ended without completion
            process.kill()
            return self.log_result(test_name, False, error="SSE stream ended without completion event")
            
        except Exception as e:
            return self.log_result(test_name, False, error=f"Failed to start SSE test: {e}")

    def test_critical_fix_1_text_generation_1_minute(self):
        """
        CRITICAL TEST A: Text generation for 1 minute should generate ~150 words (not 1531)
        This is the MOST IMPORTANT test as per the review request
        """
        print("🔥 CRITICAL TEST A: Text Generation (1 minute) - MOST IMPORTANT!")
        print("   Issue: For 1 minute, was generating 1531 words (10 minutes) instead of 150 words")
        print("   Fix: Switched frontend to SSE endpoint /api/text/generate-with-progress")
        
        url = f"{self.base_url}/text/generate-with-progress"
        params = {
            'prompt': 'История космоса',
            'duration_minutes': 1,
            'language': 'ru-RU'
        }
        
        success, complete_event = self.test_sse_endpoint(
            url, params, 
            "Text Generation (1 minute) - SSE Endpoint"
        )
        
        if success and complete_event:
            word_count = complete_event.get('word_count', 0)
            text = complete_event.get('text', '')
            estimated_duration = complete_event.get('estimated_duration', 0)
            
            # Critical check: word count should be ~150 words for 1 minute
            expected_words = 150
            word_count_ok = 120 <= word_count <= 200  # Allow some variance
            
            details = {
                'word_count': word_count,
                'expected_range': '120-200 words',
                'word_count_correct': word_count_ok,
                'estimated_duration': f"{estimated_duration:.1f}s",
                'text_preview': text[:200] + "..." if len(text) > 200 else text
            }
            
            if word_count_ok:
                return self.log_result(
                    "CRITICAL FIX 1: Word count for 1 minute", 
                    True, 
                    details
                ), complete_event
            else:
                details['error'] = f"Word count {word_count} not in expected range 120-200"
                return self.log_result(
                    "CRITICAL FIX 1: Word count for 1 minute", 
                    False, 
                    details
                ), complete_event
        
        return False, None

    def test_critical_fix_2_audio_generation_with_duration(self):
        """
        CRITICAL TEST B: Audio generation should show real duration (not 0:00) and progress should reach 100%
        """
        print("🔥 CRITICAL TEST B: Audio Generation with Real Duration")
        print("   Issue: Audio showed 0:00 duration and progress stuck at 90%")
        print("   Fix: Added get_audio_duration() and improved progress reporting")
        
        # Use short text for faster testing
        test_text = "Привет мир это тест системы синтеза речи"
        
        url = f"{self.base_url}/audio/synthesize-with-progress"
        params = {
            'text': test_text,
            'voice': 'ru_RU-irina-medium',
            'rate': 1.0,
            'language': 'ru-RU'
        }
        
        success, complete_event = self.test_sse_endpoint(
            url, params,
            "Audio Generation with Progress - SSE Endpoint"
        )
        
        if success and complete_event:
            audio_id = complete_event.get('audio_id')
            duration = complete_event.get('duration', 0)
            audio_url = complete_event.get('audio_url', '')
            
            # Critical checks
            has_audio_id = bool(audio_id)
            has_real_duration = duration > 0
            has_audio_url = bool(audio_url)
            
            details = {
                'audio_id': audio_id,
                'duration': f"{duration:.2f}s",
                'duration_positive': has_real_duration,
                'audio_url': audio_url,
                'text_length': len(test_text)
            }
            
            all_checks_passed = has_audio_id and has_real_duration and has_audio_url
            
            return self.log_result(
                "CRITICAL FIX 2: Audio duration and progress",
                all_checks_passed,
                details
            ), complete_event
        
        return False, None

    def test_critical_fix_3_audio_download(self, audio_id):
        """
        CRITICAL TEST C: Audio download should work properly
        """
        if not audio_id:
            return self.log_result(
                "CRITICAL FIX 3: Audio download",
                False,
                error="No audio_id provided"
            )
        
        print("🔥 CRITICAL TEST C: Audio Download")
        print(f"   Testing download of audio_id: {audio_id}")
        
        url = f"{self.base_url}/audio/download/{audio_id}"
        
        try:
            response = requests.get(url, timeout=30)
            
            success = response.status_code == 200
            content_length = len(response.content) if hasattr(response, 'content') else 0
            content_type = response.headers.get('content-type', '')
            
            details = {
                'status_code': response.status_code,
                'content_length': f"{content_length:,} bytes",
                'content_type': content_type,
                'file_size_ok': content_length > 1000  # Should be > 1KB for real audio
            }
            
            if success and content_length > 1000:
                return self.log_result(
                    "CRITICAL FIX 3: Audio download",
                    True,
                    details
                )
            else:
                details['error'] = f"Download failed or file too small ({content_length} bytes)"
                return self.log_result(
                    "CRITICAL FIX 3: Audio download",
                    False,
                    details
                )
                
        except Exception as e:
            return self.log_result(
                "CRITICAL FIX 3: Audio download",
                False,
                error=str(e)
            )

    def run_critical_tests(self):
        """Run all critical tests in sequence as specified in review request"""
        print("🚀 CRITICAL FIXES TESTING - Text-to-Speech Service")
        print("=" * 70)
        print("Testing fixes for:")
        print("1. ❌ For 1 minute generated 1531 words (10 minutes) instead of 150")
        print("2. ❌ Audio showed 0:00 and couldn't download")  
        print("3. ❌ Progress stuck at 90%")
        print("=" * 70)
        
        all_passed = True
        
        # TEST A: 1-minute text generation (MOST CRITICAL)
        print("\n" + "="*50)
        print("TEST A: 1-MINUTE TEXT GENERATION (MOST CRITICAL)")
        print("="*50)
        
        text_success, text_complete_event = self.test_critical_fix_1_text_generation_1_minute()
        if not text_success:
            all_passed = False
            print("❌ CRITICAL: 1-minute text generation failed!")
        else:
            print("✅ SUCCESS: 1-minute text generation working correctly!")
        
        # TEST B: Audio generation with duration
        print("\n" + "="*50)
        print("TEST B: AUDIO GENERATION WITH REAL DURATION")
        print("="*50)
        
        audio_success, audio_complete_event = self.test_critical_fix_2_audio_generation_with_duration()
        if not audio_success:
            all_passed = False
            print("❌ CRITICAL: Audio generation with duration failed!")
        else:
            print("✅ SUCCESS: Audio generation with real duration working!")
        
        # TEST C: Audio download
        print("\n" + "="*50)
        print("TEST C: AUDIO DOWNLOAD")
        print("="*50)
        
        audio_id = None
        if audio_complete_event:
            audio_id = audio_complete_event.get('audio_id')
        
        download_success = self.test_critical_fix_3_audio_download(audio_id)
        if not download_success:
            all_passed = False
            print("❌ CRITICAL: Audio download failed!")
        else:
            print("✅ SUCCESS: Audio download working correctly!")
        
        # FINAL SUMMARY
        print("\n" + "="*70)
        print("🎯 CRITICAL FIXES TEST SUMMARY")
        print("="*70)
        
        if all_passed:
            print("🎉 ALL CRITICAL FIXES WORKING CORRECTLY!")
            print("✅ Text generation: Generates correct word count for 1 minute")
            print("✅ Audio synthesis: Shows real duration, progress reaches 100%")
            print("✅ Audio download: Files download correctly")
            print("\n🚀 The user's reported issues have been successfully resolved!")
        else:
            print("❌ SOME CRITICAL ISSUES REMAIN:")
            if not text_success:
                print("❌ Text generation still has word count issues")
            if not audio_success:
                print("❌ Audio generation still has duration/progress issues")
            if not download_success:
                print("❌ Audio download still not working")
            print("\n⚠️  These issues need immediate attention!")
        
        return all_passed

def main():
    """Main test execution"""
    tester = CriticalFixesTester()
    
    try:
        success = tester.run_critical_tests()
        
        # Save results
        results_file = Path('/app/critical_fixes_test_results.json')
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'overall_success': success,
                'test_results': tester.test_results
            }, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Test execution failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())