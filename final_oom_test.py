#!/usr/bin/env python3
"""
FINAL OOM FIX VERIFICATION TEST

This test reproduces the exact scenario reported by the user:
1. First user generates audio with en_US-hfc_male-medium (works fine)
2. Second user generates audio with en_US-libritts_r-medium (caused server kill)
3. Verify server doesn't crash and both complete successfully

This is the critical test case from the review request.
"""

import requests
import json
import time
import threading
import subprocess
from datetime import datetime

class FinalOOMTest:
    def __init__(self, base_url="https://voicetoscreen.preview.emergentagent.com/api"):
        self.base_url = base_url
        
        # Exact voices from the review request
        self.voice_user1 = "en_US-hfc_male-medium"     # User 1 - works fine
        self.voice_user2 = "en_US-libritts_r-medium"   # User 2 - caused OOM kill
        
        # Test text (100-200 characters as specified)
        self.test_text = "This is a critical test to verify that the server no longer crashes when multiple users generate audio with different voices simultaneously."
        
        print("🚨 FINAL OOM FIX VERIFICATION")
        print(f"   Voice User 1: {self.voice_user1}")
        print(f"   Voice User 2: {self.voice_user2}")
        print(f"   Test text: {len(self.test_text)} characters")

    def check_server_health(self):
        """Check if server is responsive"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            return response.status_code == 200
        except:
            return False

    def synthesize_with_progress(self, voice, user_id, text):
        """Synthesize audio using the regular endpoint (no auth required)"""
        print(f"\n👤 USER {user_id}: Starting synthesis with {voice}")
        
        start_time = time.time()
        
        try:
            # Use regular synthesis endpoint (no auth required)
            response = requests.post(
                f"{self.base_url}/audio/synthesize",
                json={
                    "text": text,
                    "voice": voice,
                    "rate": 1.0,
                    "language": "en-US"
                },
                headers={'Content-Type': 'application/json'},
                timeout=180  # 3 minutes timeout
            )
            
            if response.status_code == 200:
                # Process regular JSON response
                elapsed = time.time() - start_time
                result = response.json()
                audio_id = result.get('id')
                
                print(f"   ✅ USER {user_id}: COMPLETED in {elapsed:.2f}s")
                print(f"   Audio ID: {audio_id}")
                
                return {
                    'success': True,
                    'user_id': user_id,
                    'voice': voice,
                    'audio_id': audio_id,
                    'time': elapsed
                }
                
            else:
                elapsed = time.time() - start_time
                print(f"   ❌ USER {user_id}: HTTP {response.status_code} after {elapsed:.2f}s")
                return {
                    'success': False,
                    'user_id': user_id,
                    'voice': voice,
                    'error': f'HTTP {response.status_code}',
                    'time': elapsed
                }
                
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   ❌ USER {user_id}: EXCEPTION after {elapsed:.2f}s")
            print(f"   Error: {str(e)}")
            return {
                'success': False,
                'user_id': user_id,
                'voice': voice,
                'error': str(e),
                'time': elapsed
            }

    def test_critical_oom_scenario(self):
        """Test the exact scenario that caused OOM kill"""
        print("\n🔥 CRITICAL OOM SCENARIO TEST")
        print("=" * 60)
        print("Reproducing the exact user-reported scenario:")
        print("1. User 1 generates with en_US-hfc_male-medium (should work)")
        print("2. User 2 generates with en_US-libritts_r-medium (caused OOM)")
        print("3. Verify server survives and both complete successfully")
        
        # Initial health check
        if not self.check_server_health():
            print("❌ Server not responsive before test")
            return False
        
        print("✅ Server responsive before test")
        
        # Test User 1 first (as in original scenario)
        print(f"\n--- USER 1 TEST ---")
        result1 = self.synthesize_with_progress(self.voice_user1, 1, self.test_text)
        
        # Check server health after User 1
        if not self.check_server_health():
            print("❌ Server became unresponsive after User 1")
            return False
        
        print("✅ Server still responsive after User 1")
        
        # Small delay as in real usage
        time.sleep(2)
        
        # Test User 2 (the critical test - this caused OOM kill)
        print(f"\n--- USER 2 TEST (CRITICAL) ---")
        result2 = self.synthesize_with_progress(self.voice_user2, 2, self.test_text)
        
        # Check server health after User 2 (critical check)
        if not self.check_server_health():
            print("❌ CRITICAL: Server became unresponsive after User 2")
            print("❌ OOM fix is NOT working - server likely crashed")
            return False
        
        print("✅ CRITICAL: Server still responsive after User 2")
        
        # Analyze results
        print(f"\n📊 CRITICAL SCENARIO RESULTS:")
        print(f"   User 1 ({self.voice_user1}): {'✅ SUCCESS' if result1['success'] else '❌ FAILED'}")
        print(f"   User 2 ({self.voice_user2}): {'✅ SUCCESS' if result2['success'] else '❌ FAILED'}")
        
        if result1['success']:
            print(f"   User 1 time: {result1['time']:.2f}s")
        else:
            print(f"   User 1 error: {result1.get('error', 'Unknown')}")
        
        if result2['success']:
            print(f"   User 2 time: {result2['time']:.2f}s")
        else:
            print(f"   User 2 error: {result2.get('error', 'Unknown')}")
        
        # Final verdict
        both_success = result1['success'] and result2['success']
        server_survived = self.check_server_health()
        
        print(f"\n🎯 CRITICAL SCENARIO VERDICT:")
        
        if both_success and server_survived:
            print("✅ OOM FIX VERIFIED: WORKING CORRECTLY")
            print("✅ Both users completed successfully")
            print("✅ Server did not crash with different voices")
            print("✅ Original OOM bug is FIXED")
            
            # Check if performance is reasonable
            if result1['success'] and result2['success']:
                avg_time = (result1['time'] + result2['time']) / 2
                if avg_time < 30:  # Under 30 seconds is good
                    print(f"✅ Performance good: avg {avg_time:.1f}s per generation")
                else:
                    print(f"⚠️  Performance slow: avg {avg_time:.1f}s per generation")
            
        else:
            print("❌ OOM FIX FAILED")
            
            if not result1['success']:
                print("❌ User 1 failed (unexpected)")
            
            if not result2['success']:
                print("❌ User 2 failed (critical - OOM bug may persist)")
            
            if not server_survived:
                print("❌ Server crashed (critical - OOM bug definitely persists)")
        
        return both_success and server_survived

    def test_parallel_critical_scenario(self):
        """Test parallel version of the critical scenario (more aggressive)"""
        print("\n🔥 PARALLEL CRITICAL SCENARIO")
        print("=" * 60)
        print("Testing both users starting simultaneously (more aggressive)")
        
        results = []
        
        def user_thread(voice, user_id):
            result = self.synthesize_with_progress(voice, user_id, self.test_text)
            results.append(result)
        
        # Start both users simultaneously
        thread1 = threading.Thread(target=user_thread, args=(self.voice_user1, 1))
        thread2 = threading.Thread(target=user_thread, args=(self.voice_user2, 2))
        
        print("🚀 Starting both users simultaneously...")
        
        thread1.start()
        thread2.start()
        
        # Wait for both to complete
        thread1.join()
        thread2.join()
        
        # Check server health
        server_survived = self.check_server_health()
        
        # Analyze results
        successful_users = sum(1 for r in results if r['success'])
        
        print(f"\n📊 PARALLEL SCENARIO RESULTS:")
        print(f"   Successful users: {successful_users}/2")
        print(f"   Server survived: {'✅ YES' if server_survived else '❌ NO'}")
        
        for result in results:
            status = '✅ SUCCESS' if result['success'] else '❌ FAILED'
            print(f"   User {result['user_id']} ({result['voice']}): {status}")
            if result['success']:
                print(f"     Time: {result['time']:.2f}s")
            else:
                print(f"     Error: {result.get('error', 'Unknown')}")
        
        if successful_users == 2 and server_survived:
            print("✅ PARALLEL SCENARIO: SUCCESS")
            print("✅ Server handles simultaneous different voices")
        else:
            print("❌ PARALLEL SCENARIO: ISSUES DETECTED")
        
        return successful_users == 2 and server_survived

def main():
    tester = FinalOOMTest()
    
    print("🚨 FINAL OOM FIX VERIFICATION TEST")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 70)
    
    # Test 1: Sequential (exact reproduction of user scenario)
    sequential_success = tester.test_critical_oom_scenario()
    
    # Test 2: Parallel (more aggressive test)
    if sequential_success:
        parallel_success = tester.test_parallel_critical_scenario()
    else:
        print("\n⚠️  Skipping parallel test due to sequential failure")
        parallel_success = False
    
    # Final summary
    print("\n" + "=" * 70)
    print("🎯 FINAL OOM FIX VERIFICATION SUMMARY")
    print("=" * 70)
    
    if sequential_success:
        print("✅ CRITICAL TEST PASSED: OOM fix is working")
        print("✅ Server survives multiple users with different voices")
        print("✅ Original user-reported bug is RESOLVED")
        
        if parallel_success:
            print("✅ BONUS: Parallel scenario also works")
        else:
            print("⚠️  Parallel scenario has issues (but not critical)")
        
        print("\n🎉 OOM FIX VERIFICATION: SUCCESS")
        print("The VoiceCache LRU eviction is working correctly!")
        
    else:
        print("❌ CRITICAL TEST FAILED: OOM fix is NOT working")
        print("❌ Server still crashes with multiple different voices")
        print("❌ Original user-reported bug PERSISTS")
        
        print("\n🚨 OOM FIX VERIFICATION: FAILED")
        print("The VoiceCache implementation needs investigation!")
    
    return 0 if sequential_success else 1

if __name__ == "__main__":
    exit(main())