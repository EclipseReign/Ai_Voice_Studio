#!/usr/bin/env python3
"""
Focused LRU Cache Test for VoiceCache

This test specifically verifies the LRU cache behavior with detailed log analysis.
"""

import requests
import json
import time
import subprocess
from datetime import datetime

class LRUCacheTest:
    def __init__(self, base_url="https://voicetoscreen.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.test_voices = [
            "en_US-hfc_male-medium",      # Voice A
            "en_US-libritts_r-medium",    # Voice B  
            "ru_RU-irina-medium"          # Voice C
        ]
        self.test_text = "Testing LRU cache behavior with different voices."

    def get_backend_logs(self):
        """Get recent backend logs"""
        try:
            result = subprocess.run([
                "tail", "-n", "50", "/var/log/supervisor/backend.err.log"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return result.stdout.split('\n')
            return []
        except:
            return []

    def synthesize_audio(self, voice, user_id):
        """Synthesize audio with specific voice"""
        print(f"\n🎤 USER {user_id}: Synthesizing with {voice}")
        
        try:
            response = requests.post(
                f"{self.base_url}/audio/synthesize",
                json={
                    "text": self.test_text,
                    "voice": voice,
                    "rate": 1.0,
                    "language": "en-US"
                },
                headers={'Content-Type': 'application/json'},
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ SUCCESS: {result.get('id')}")
                return True
            else:
                print(f"   ❌ FAILED: Status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ EXCEPTION: {str(e)}")
            return False

    def analyze_cache_logs(self, logs):
        """Analyze logs for cache behavior"""
        cache_events = []
        
        for line in logs:
            if 'Voice cache' in line or 'Voice LOADED' in line or 'Voice EVICTED' in line:
                cache_events.append(line.strip())
        
        return cache_events

    def test_lru_behavior(self):
        """Test LRU cache behavior step by step"""
        print("🔥 LRU CACHE BEHAVIOR TEST")
        print("=" * 60)
        
        # Clear any existing logs by getting baseline
        baseline_logs = self.get_backend_logs()
        print(f"📋 Baseline: {len(baseline_logs)} log lines")
        
        # Step 1: Load first voice (should be MISS + LOADED)
        print(f"\n📍 STEP 1: Load Voice A ({self.test_voices[0]})")
        print("   Expected: MISS + LOADED (cache size: 1/2)")
        
        success1 = self.synthesize_audio(self.test_voices[0], "1")
        time.sleep(1)
        
        logs1 = self.get_backend_logs()
        cache_events1 = self.analyze_cache_logs(logs1)
        print(f"   Cache events: {len(cache_events1)}")
        for event in cache_events1[-3:]:  # Show last 3 events
            if self.test_voices[0] in event:
                print(f"   📝 {event}")
        
        # Step 2: Load second voice (should be MISS + LOADED)
        print(f"\n📍 STEP 2: Load Voice B ({self.test_voices[1]})")
        print("   Expected: MISS + LOADED (cache size: 2/2)")
        
        success2 = self.synthesize_audio(self.test_voices[1], "2")
        time.sleep(1)
        
        logs2 = self.get_backend_logs()
        cache_events2 = self.analyze_cache_logs(logs2)
        print(f"   Cache events: {len(cache_events2)}")
        for event in cache_events2[-3:]:  # Show last 3 events
            if self.test_voices[1] in event:
                print(f"   📝 {event}")
        
        # Step 3: Load third voice (should be MISS + EVICTED + LOADED)
        print(f"\n📍 STEP 3: Load Voice C ({self.test_voices[2]})")
        print("   Expected: MISS + EVICTED (Voice A) + LOADED (cache size: 2/2)")
        
        success3 = self.synthesize_audio(self.test_voices[2], "3")
        time.sleep(1)
        
        logs3 = self.get_backend_logs()
        cache_events3 = self.analyze_cache_logs(logs3)
        print(f"   Cache events: {len(cache_events3)}")
        for event in cache_events3[-5:]:  # Show last 5 events
            if self.test_voices[2] in event or 'EVICTED' in event:
                print(f"   📝 {event}")
        
        # Step 4: Reuse Voice B (should be HIT)
        print(f"\n📍 STEP 4: Reuse Voice B ({self.test_voices[1]})")
        print("   Expected: HIT (no loading)")
        
        success4 = self.synthesize_audio(self.test_voices[1], "4")
        time.sleep(1)
        
        logs4 = self.get_backend_logs()
        cache_events4 = self.analyze_cache_logs(logs4)
        print(f"   Cache events: {len(cache_events4)}")
        for event in cache_events4[-3:]:  # Show last 3 events
            if self.test_voices[1] in event and 'HIT' in event:
                print(f"   📝 {event}")
        
        # Step 5: Reuse Voice A (should be MISS + EVICTED + LOADED)
        print(f"\n📍 STEP 5: Reuse Voice A ({self.test_voices[0]})")
        print("   Expected: MISS + EVICTED (Voice C) + LOADED (cache size: 2/2)")
        
        success5 = self.synthesize_audio(self.test_voices[0], "5")
        time.sleep(1)
        
        logs5 = self.get_backend_logs()
        cache_events5 = self.analyze_cache_logs(logs5)
        print(f"   Cache events: {len(cache_events5)}")
        for event in cache_events5[-5:]:  # Show last 5 events
            if self.test_voices[0] in event or 'EVICTED' in event:
                print(f"   📝 {event}")
        
        # Analysis
        print("\n" + "=" * 60)
        print("📊 LRU CACHE ANALYSIS")
        print("=" * 60)
        
        all_success = all([success1, success2, success3, success4, success5])
        
        if all_success:
            print("✅ All synthesis operations succeeded")
        else:
            print("❌ Some synthesis operations failed")
            return False
        
        # Check for expected patterns in logs
        all_logs = self.get_backend_logs()
        
        # Count different event types
        miss_count = sum(1 for line in all_logs if 'Voice cache MISS:' in line)
        hit_count = sum(1 for line in all_logs if 'Voice cache HIT:' in line)
        loaded_count = sum(1 for line in all_logs if 'Voice LOADED into cache:' in line)
        evicted_count = sum(1 for line in all_logs if 'Voice EVICTED from cache' in line)
        
        print(f"📈 Cache Statistics:")
        print(f"   MISS events: {miss_count}")
        print(f"   HIT events: {hit_count}")
        print(f"   LOADED events: {loaded_count}")
        print(f"   EVICTED events: {evicted_count}")
        
        # Verify expected behavior
        expected_behavior = True
        
        if miss_count < 4:  # Should have at least 4 misses (A, B, C, A again)
            print("   ❌ Expected at least 4 MISS events")
            expected_behavior = False
        else:
            print("   ✅ Sufficient MISS events detected")
        
        if hit_count < 1:  # Should have at least 1 hit (B reuse)
            print("   ❌ Expected at least 1 HIT event")
            expected_behavior = False
        else:
            print("   ✅ Cache HIT events detected")
        
        if evicted_count < 2:  # Should have at least 2 evictions (A evicted by C, C evicted by A)
            print("   ❌ Expected at least 2 EVICTED events")
            expected_behavior = False
        else:
            print("   ✅ LRU eviction working properly")
        
        if loaded_count < 4:  # Should have at least 4 loads
            print("   ❌ Expected at least 4 LOADED events")
            expected_behavior = False
        else:
            print("   ✅ Voice loading working properly")
        
        # Final verdict
        print("\n" + "=" * 60)
        if expected_behavior and all_success:
            print("🎯 LRU CACHE TEST: ✅ PASSED")
            print("✅ VoiceCache LRU eviction working correctly")
            print("✅ Cache HIT/MISS behavior as expected")
            print("✅ Memory management through eviction working")
            print("✅ Server stable with multiple different voices")
        else:
            print("🎯 LRU CACHE TEST: ❌ FAILED")
            if not all_success:
                print("❌ Some audio synthesis operations failed")
            if not expected_behavior:
                print("❌ Cache behavior not as expected")
        
        return expected_behavior and all_success

def main():
    tester = LRUCacheTest()
    success = tester.test_lru_behavior()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())