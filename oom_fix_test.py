#!/usr/bin/env python3
"""
CRITICAL OOM FIX TESTING for Multiple Users with Different Voices

This test specifically targets the reported issue:
- Server crashes (Killed) when second user starts generating audio with different voice
- First user works fine, second user causes OOM kill
- Tests the VoiceCache LRU eviction fix

Test Scenarios:
1. User 1 generates with voice A (en_US-hfc_male-medium)
2. User 2 generates with voice B (en_US-libritts_r-medium) - CRITICAL TEST
3. User 3 generates with voice C (ru_RU-irina-medium) - LRU eviction test
4. Verify cache HIT when reusing voices
5. Check backend logs for proper LRU cache messages
"""

import requests
import json
import time
import threading
import sys
from datetime import datetime
from pathlib import Path
import subprocess
import concurrent.futures

class OOMFixTester:
    def __init__(self, base_url="https://backend-memory-fix.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.test_results = []
        self.backend_logs = []
        
        # Test voices for OOM scenario (different voices to trigger model loading)
        self.test_voices = [
            "en_US-hfc_male-medium",      # Voice A - User 1
            "en_US-libritts_r-medium",    # Voice B - User 2 (CRITICAL - this caused OOM)
            "ru_RU-irina-medium"          # Voice C - User 3 (LRU eviction test)
        ]
        
        # Short test text to minimize generation time and focus on voice loading
        self.test_text = "This is a test of the voice cache system. We are testing multiple users with different voices to ensure the server does not crash due to out of memory issues."
        
        print("🔧 OOM Fix Tester Initialized")
        print(f"   Base URL: {self.base_url}")
        print(f"   Test voices: {self.test_voices}")
        print(f"   Test text length: {len(self.test_text)} characters")

    def capture_backend_logs(self):
        """Capture backend logs to verify LRU cache behavior"""
        try:
            # Get recent backend logs from error log (where our logging goes)
            result = subprocess.run([
                "tail", "-n", "100", "/var/log/supervisor/backend.err.log"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                self.backend_logs = result.stdout.split('\n')
                print(f"📋 Captured {len(self.backend_logs)} log lines from backend.err.log")
            else:
                print(f"⚠️  Could not capture backend logs: {result.stderr}")
        except Exception as e:
            print(f"⚠️  Error capturing logs: {e}")

    def check_voice_cache_logs(self):
        """Check backend logs for VoiceCache LRU messages"""
        print("\n🔍 ANALYZING BACKEND LOGS FOR VOICE CACHE BEHAVIOR")
        
        cache_events = {
            'MISS': [],
            'LOADED': [],
            'EVICTED': [],
            'HIT': []
        }
        
        for line in self.backend_logs:
            if 'Voice cache' in line:
                if 'MISS:' in line:
                    voice = line.split('MISS: ')[1].split(' ')[0] if 'MISS: ' in line else 'unknown'
                    cache_events['MISS'].append(voice)
                elif 'LOADED into cache:' in line:
                    voice = line.split('LOADED into cache: ')[1].split(' ')[0] if 'LOADED into cache: ' in line else 'unknown'
                    cache_events['LOADED'].append(voice)
                elif 'EVICTED from cache' in line:
                    voice = line.split('EVICTED from cache (LRU): ')[1].split(' ')[0] if 'EVICTED from cache (LRU): ' in line else 'unknown'
                    cache_events['EVICTED'].append(voice)
                elif 'HIT:' in line:
                    voice = line.split('HIT: ')[1].split(' ')[0] if 'HIT: ' in line else 'unknown'
                    cache_events['HIT'].append(voice)
        
        print(f"   Cache MISS events: {len(cache_events['MISS'])} - {cache_events['MISS']}")
        print(f"   Cache LOADED events: {len(cache_events['LOADED'])} - {cache_events['LOADED']}")
        print(f"   Cache EVICTED events: {len(cache_events['EVICTED'])} - {cache_events['EVICTED']}")
        print(f"   Cache HIT events: {len(cache_events['HIT'])} - {cache_events['HIT']}")
        
        # Verify expected behavior
        expected_behavior = True
        
        # Should have at least 2 MISS events (for first 2 different voices)
        if len(cache_events['MISS']) < 2:
            print("   ❌ Expected at least 2 cache MISS events for different voices")
            expected_behavior = False
        else:
            print("   ✅ Cache MISS events detected for new voices")
        
        # Should have LOADED events matching MISS events
        if len(cache_events['LOADED']) < len(cache_events['MISS']):
            print("   ❌ LOADED events don't match MISS events")
            expected_behavior = False
        else:
            print("   ✅ Voice models loaded after cache misses")
        
        # If we tested 3+ voices, should have EVICTED events (LRU with max 2 models)
        if len(set(cache_events['LOADED'])) > 2 and len(cache_events['EVICTED']) == 0:
            print("   ❌ Expected EVICTED events when loading 3+ different voices (LRU max=2)")
            expected_behavior = False
        elif len(cache_events['EVICTED']) > 0:
            print("   ✅ LRU eviction working - old models evicted when cache full")
        
        return expected_behavior, cache_events

    def synthesize_audio_single_user(self, user_id, voice, text=None):
        """Synthesize audio for a single user with specific voice"""
        if text is None:
            text = self.test_text
            
        print(f"\n👤 USER {user_id}: Starting audio synthesis")
        print(f"   Voice: {voice}")
        print(f"   Text: {text[:50]}...")
        
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.base_url}/audio/synthesize",
                json={
                    "text": text,
                    "voice": voice,
                    "rate": 1.0,
                    "language": "en-US"
                },
                headers={'Content-Type': 'application/json'},
                timeout=120  # 2 minutes timeout
            )
            
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                audio_id = result.get('id')
                print(f"   ✅ USER {user_id}: SUCCESS in {elapsed_time:.2f}s")
                print(f"   Audio ID: {audio_id}")
                
                return {
                    'success': True,
                    'user_id': user_id,
                    'voice': voice,
                    'audio_id': audio_id,
                    'time': elapsed_time,
                    'status_code': response.status_code
                }
            else:
                print(f"   ❌ USER {user_id}: FAILED - Status {response.status_code}")
                print(f"   Error: {response.text[:200]}")
                
                return {
                    'success': False,
                    'user_id': user_id,
                    'voice': voice,
                    'audio_id': None,
                    'time': elapsed_time,
                    'status_code': response.status_code,
                    'error': response.text[:200]
                }
                
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"   ❌ USER {user_id}: EXCEPTION after {elapsed_time:.2f}s")
            print(f"   Error: {str(e)}")
            
            return {
                'success': False,
                'user_id': user_id,
                'voice': voice,
                'audio_id': None,
                'time': elapsed_time,
                'status_code': 'EXCEPTION',
                'error': str(e)
            }

    def test_sequential_different_voices(self):
        """Test sequential audio generation with different voices (reproduce OOM scenario)"""
        print("\n🔥 CRITICAL TEST: Sequential Different Voices (OOM Reproduction)")
        print("   This test reproduces the exact scenario that caused server crashes")
        print("   User 1: en_US-hfc_male-medium")
        print("   User 2: en_US-libritts_r-medium (this caused OOM kill)")
        print("   User 3: ru_RU-irina-medium (LRU eviction test)")
        
        results = []
        
        # Test each voice sequentially
        for i, voice in enumerate(self.test_voices, 1):
            print(f"\n--- Testing Voice {i}/{len(self.test_voices)} ---")
            
            # Capture logs before test
            self.capture_backend_logs()
            
            result = self.synthesize_audio_single_user(i, voice)
            results.append(result)
            
            # Check if server is still responsive after each test
            if not result['success']:
                print(f"❌ CRITICAL: Server failed on user {i} with voice {voice}")
                print("   This indicates the OOM fix is not working properly")
                break
            else:
                print(f"✅ Server survived user {i} with voice {voice}")
            
            # Small delay between users to simulate real usage
            time.sleep(2)
        
        # Capture final logs
        self.capture_backend_logs()
        
        # Analyze results
        successful_users = sum(1 for r in results if r['success'])
        total_users = len(results)
        
        print(f"\n📊 SEQUENTIAL TEST RESULTS:")
        print(f"   Successful users: {successful_users}/{total_users}")
        print(f"   Server survival rate: {(successful_users/total_users)*100:.1f}%")
        
        # Check if we reproduced the original bug (server should NOT crash now)
        if successful_users == total_users:
            print("   ✅ OOM FIX WORKING: All users completed successfully")
            print("   ✅ Server did not crash with multiple different voices")
        elif successful_users == 1:
            print("   ❌ OOM BUG STILL EXISTS: Only first user succeeded")
            print("   ❌ Server likely crashed on second user (original bug)")
        else:
            print(f"   ⚠️  PARTIAL SUCCESS: {successful_users} users succeeded")
        
        return results

    def test_parallel_different_voices(self):
        """Test parallel audio generation with different voices (stress test)"""
        print("\n🔥 STRESS TEST: Parallel Different Voices")
        print("   Testing multiple users simultaneously with different voices")
        print("   This is a more aggressive test than the original bug scenario")
        
        # Use ThreadPoolExecutor for true parallel execution
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all tasks simultaneously
            future_to_user = {}
            for i, voice in enumerate(self.test_voices, 1):
                future = executor.submit(self.synthesize_audio_single_user, i, voice)
                future_to_user[future] = (i, voice)
            
            print("   🚀 All users started simultaneously...")
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_user):
                user_id, voice = future_to_user[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result['success']:
                        print(f"   ✅ USER {user_id} ({voice}): Completed in {result['time']:.2f}s")
                    else:
                        print(f"   ❌ USER {user_id} ({voice}): Failed - {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    print(f"   ❌ USER {user_id} ({voice}): Exception - {str(e)}")
                    results.append({
                        'success': False,
                        'user_id': user_id,
                        'voice': voice,
                        'error': str(e)
                    })
        
        # Analyze parallel results
        successful_users = sum(1 for r in results if r['success'])
        total_users = len(results)
        
        print(f"\n📊 PARALLEL TEST RESULTS:")
        print(f"   Successful users: {successful_users}/{total_users}")
        print(f"   Parallel success rate: {(successful_users/total_users)*100:.1f}%")
        
        if successful_users == total_users:
            print("   ✅ PARALLEL SUCCESS: All users completed simultaneously")
            print("   ✅ Server handles concurrent different voices well")
        elif successful_users >= total_users * 0.7:  # 70% success rate
            print("   ⚠️  PARTIAL PARALLEL SUCCESS: Most users succeeded")
            print("   ⚠️  Some contention expected with parallel access")
        else:
            print("   ❌ PARALLEL FAILURE: Most users failed")
            print("   ❌ Server cannot handle concurrent different voices")
        
        return results

    def test_voice_reuse_cache_hit(self):
        """Test voice reuse to verify cache HIT behavior"""
        print("\n🔄 CACHE HIT TEST: Voice Reuse")
        print("   Testing that reusing the same voice results in cache HIT")
        
        # Use the first voice twice to test cache HIT
        voice = self.test_voices[0]
        
        print(f"   First use of {voice} (should be cache MISS + LOADED)")
        result1 = self.synthesize_audio_single_user("A", voice)
        
        time.sleep(1)  # Small delay
        
        print(f"   Second use of {voice} (should be cache HIT)")
        result2 = self.synthesize_audio_single_user("B", voice)
        
        # Capture logs to check for HIT
        self.capture_backend_logs()
        
        # Check if both succeeded
        both_success = result1['success'] and result2['success']
        
        if both_success:
            print("   ✅ Both voice reuse attempts succeeded")
            
            # Check if second attempt was faster (cache hit should be faster)
            if result2['time'] < result1['time']:
                print(f"   ✅ Second attempt faster ({result2['time']:.2f}s vs {result1['time']:.2f}s)")
                print("   ✅ Indicates cache HIT working")
            else:
                print(f"   ⚠️  Second attempt not faster ({result2['time']:.2f}s vs {result1['time']:.2f}s)")
                print("   ⚠️  May still be cache HIT, but no speed improvement detected")
        else:
            print("   ❌ Voice reuse test failed - one or both attempts failed")
        
        return both_success, result1, result2

    def check_server_health(self):
        """Check if server is still responsive"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 200:
                print("✅ Server health check: RESPONSIVE")
                return True
            else:
                print(f"⚠️  Server health check: Status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Server health check: FAILED - {str(e)}")
            return False

    def run_comprehensive_oom_tests(self):
        """Run all OOM-related tests"""
        print("🚀 COMPREHENSIVE OOM FIX TESTING")
        print("=" * 70)
        print("Testing the VoiceCache LRU eviction fix for multiple users")
        print("Original issue: Server killed when 2nd user uses different voice")
        print("=" * 70)
        
        # Initial server health check
        print("\n🏥 INITIAL SERVER HEALTH CHECK")
        if not self.check_server_health():
            print("❌ Server not responsive - cannot run tests")
            return False
        
        all_tests_passed = True
        
        # TEST 1: Sequential different voices (reproduce original bug scenario)
        print("\n" + "="*50)
        print("TEST 1: SEQUENTIAL DIFFERENT VOICES")
        print("="*50)
        
        sequential_results = self.test_sequential_different_voices()
        sequential_success = all(r['success'] for r in sequential_results)
        
        if not sequential_success:
            print("❌ CRITICAL: Sequential test failed - OOM fix not working")
            all_tests_passed = False
        
        # Check server health after sequential test
        if not self.check_server_health():
            print("❌ CRITICAL: Server became unresponsive after sequential test")
            return False
        
        # TEST 2: Voice cache behavior analysis
        print("\n" + "="*50)
        print("TEST 2: VOICE CACHE LOG ANALYSIS")
        print("="*50)
        
        cache_behavior_ok, cache_events = self.check_voice_cache_logs()
        if not cache_behavior_ok:
            print("❌ Voice cache behavior not as expected")
            all_tests_passed = False
        
        # TEST 3: Voice reuse (cache HIT test)
        print("\n" + "="*50)
        print("TEST 3: VOICE REUSE (CACHE HIT)")
        print("="*50)
        
        cache_hit_success, _, _ = self.test_voice_reuse_cache_hit()
        if not cache_hit_success:
            print("❌ Voice reuse test failed")
            all_tests_passed = False
        
        # TEST 4: Parallel stress test (if sequential passed)
        if sequential_success:
            print("\n" + "="*50)
            print("TEST 4: PARALLEL STRESS TEST")
            print("="*50)
            
            parallel_results = self.test_parallel_different_voices()
            parallel_success_rate = sum(1 for r in parallel_results if r['success']) / len(parallel_results)
            
            if parallel_success_rate < 0.7:  # 70% threshold for parallel
                print("⚠️  Parallel test below 70% success rate")
                # Don't fail overall test for parallel issues
        else:
            print("\n⚠️  Skipping parallel test due to sequential test failure")
        
        # Final server health check
        print("\n🏥 FINAL SERVER HEALTH CHECK")
        final_health = self.check_server_health()
        if not final_health:
            print("❌ CRITICAL: Server unresponsive after all tests")
            all_tests_passed = False
        
        # FINAL SUMMARY
        print("\n" + "="*70)
        print("🎯 OOM FIX TEST SUMMARY")
        print("="*70)
        
        if all_tests_passed and final_health:
            print("✅ ALL CRITICAL TESTS PASSED")
            print("✅ OOM fix is working correctly")
            print("✅ Server survives multiple users with different voices")
            print("✅ VoiceCache LRU eviction functioning properly")
            
            # Detailed success metrics
            successful_sequential = sum(1 for r in sequential_results if r['success'])
            print(f"✅ Sequential users: {successful_sequential}/{len(sequential_results)} succeeded")
            
            if 'parallel_results' in locals():
                successful_parallel = sum(1 for r in parallel_results if r['success'])
                print(f"✅ Parallel users: {successful_parallel}/{len(parallel_results)} succeeded")
            
            print("✅ Cache behavior: LRU eviction working")
            print("✅ Server health: Responsive throughout testing")
            
        else:
            print("❌ CRITICAL ISSUES DETECTED")
            
            if not sequential_success:
                print("❌ Sequential test failed - OOM bug may still exist")
            
            if not cache_behavior_ok:
                print("❌ Voice cache not behaving as expected")
            
            if not final_health:
                print("❌ Server became unresponsive")
            
            print("\n🚨 RECOMMENDED ACTIONS:")
            print("1. Check backend logs for OOM kills or memory issues")
            print("2. Verify VoiceCache implementation in server.py")
            print("3. Monitor memory usage during voice model loading")
            print("4. Consider reducing max_size in VoiceCache if needed")
        
        return all_tests_passed

def main():
    """Main test execution"""
    tester = OOMFixTester()
    
    print("Starting OOM Fix Testing...")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    success = tester.run_comprehensive_oom_tests()
    
    # Save results
    results_file = Path("/app/oom_fix_test_results.json")
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'overall_success': success,
            'test_voices': tester.test_voices,
            'backend_logs_captured': len(tester.backend_logs),
            'test_results': tester.test_results
        }, f, indent=2)
    
    print(f"\n📄 Results saved to: {results_file}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())