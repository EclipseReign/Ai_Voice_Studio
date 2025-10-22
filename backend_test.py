import requests
import sys
import json
import time
from datetime import datetime

class TextToSpeechAPITester:
    def __init__(self, base_url="https://speaktogen.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)

            success = response.status_code == expected_status
            
            result = {
                "test_name": name,
                "endpoint": endpoint,
                "method": method,
                "expected_status": expected_status,
                "actual_status": response.status_code,
                "success": success,
                "response_data": None,
                "error": None
            }
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    result["response_data"] = response.json()
                except:
                    result["response_data"] = response.text[:200]
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    result["error"] = error_data
                    print(f"   Error: {error_data}")
                except:
                    result["error"] = response.text[:200]
                    print(f"   Error: {response.text[:200]}")

            self.test_results.append(result)
            return success, result["response_data"] if success else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            result = {
                "test_name": name,
                "endpoint": endpoint,
                "method": method,
                "expected_status": expected_status,
                "actual_status": "ERROR",
                "success": False,
                "response_data": None,
                "error": str(e)
            }
            self.test_results.append(result)
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        success, response = self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200
        )
        return success

    def test_voices_endpoint(self):
        """Test voices endpoint"""
        success, response = self.run_test(
            "Get Available Voices",
            "GET",
            "voices",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} voices")
            if len(response) > 0:
                print(f"   Sample voice: {response[0].get('name', 'Unknown')}")
                return response[0].get('short_name')  # Return first voice for testing
        
        return None

    def test_text_generation(self):
        """Test text generation endpoint"""
        success, response = self.run_test(
            "Generate Text",
            "POST",
            "text/generate",
            200,
            data={
                "prompt": "The benefits of artificial intelligence in healthcare",
                "duration_minutes": 2,
                "language": "en-US"
            },
            timeout=60  # Text generation might take longer
        )
        
        if success and response:
            print(f"   Generated {response.get('word_count', 0)} words")
            print(f"   Text preview: {response.get('text', '')[:100]}...")
            return response.get('text')
        
        return None

    def test_audio_synthesis(self, text, voice):
        """Test audio synthesis endpoint"""
        if not text or not voice:
            print("⚠️  Skipping audio synthesis - missing text or voice")
            return None
            
        success, response = self.run_test(
            "Synthesize Audio",
            "POST",
            "audio/synthesize",
            200,
            data={
                "text": text[:500],  # Limit text length for testing
                "voice": voice,
                "rate": "+0%",
                "language": "en-US"
            },
            timeout=60  # Audio synthesis might take longer
        )
        
        if success and response:
            print(f"   Audio ID: {response.get('id')}")
            print(f"   Audio URL: {response.get('audio_url')}")
            return response.get('id')
        
        return None

    def test_audio_download(self, audio_id):
        """Test audio download endpoint"""
        if not audio_id:
            print("⚠️  Skipping audio download - missing audio ID")
            return False
            
        success, _ = self.run_test(
            "Download Audio",
            "GET",
            f"audio/download/{audio_id}",
            200,
            timeout=30
        )
        
        return success

    def test_history_endpoint(self):
        """Test history endpoint"""
        success, response = self.run_test(
            "Get Generation History",
            "GET",
            "history",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} history items")
        
        return success

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Text-to-Speech API Tests")
        print(f"   Base URL: {self.base_url}")
        print("=" * 60)
        
        # Test 1: Root endpoint
        self.test_root_endpoint()
        
        # Test 2: Get voices
        sample_voice = self.test_voices_endpoint()
        
        # Test 3: Generate text
        generated_text = self.test_text_generation()
        
        # Test 4: Synthesize audio
        audio_id = self.test_audio_synthesis(generated_text, sample_voice)
        
        # Test 5: Download audio
        if audio_id:
            # Wait a moment for audio processing
            time.sleep(2)
            self.test_audio_download(audio_id)
        
        # Test 6: Get history
        self.test_history_endpoint()
        
        # Print results
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed < self.tests_run:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   - {result['test_name']}: {result.get('error', 'Unknown error')}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = TextToSpeechAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_tests': tester.tests_run,
            'passed_tests': tester.tests_passed,
            'success_rate': f"{(tester.tests_passed/tester.tests_run)*100:.1f}%" if tester.tests_run > 0 else "0%",
            'test_results': tester.test_results
        }, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())