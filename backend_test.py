import requests
import sys
import json
import time
import os
from datetime import datetime
from pathlib import Path

class EdgeTTSAPITester:
    def __init__(self, base_url="https://promptspeak.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.generated_audio_ids = []
        self.available_voices = []

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}" if endpoint else self.base_url
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
                    result["response_data"] = response.text[:200] if hasattr(response, 'text') else "Binary data"
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    result["error"] = error_data
                    print(f"   Error: {error_data}")
                except:
                    result["error"] = response.text[:200] if hasattr(response, 'text') else "Unknown error"
                    print(f"   Error: {result['error']}")

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
        """Test voices endpoint (edge-tts)"""
        success, response = self.run_test(
            "Get Available Voices (edge-tts)",
            "GET",
            "voices",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} voices")
            self.available_voices = response
            
            # Show sample voices by language
            en_voices = [v for v in response if v.get('locale', '').startswith('en-')]
            ru_voices = [v for v in response if v.get('locale', '').startswith('ru-')]
            es_voices = [v for v in response if v.get('locale', '').startswith('es-')]
            
            print(f"   English voices: {len(en_voices)}")
            print(f"   Russian voices: {len(ru_voices)}")
            print(f"   Spanish voices: {len(es_voices)}")
            
            if en_voices:
                print(f"   Sample EN voice: {en_voices[0].get('name')} ({en_voices[0].get('short_name')})")
            if ru_voices:
                print(f"   Sample RU voice: {ru_voices[0].get('name')} ({ru_voices[0].get('short_name')})")
                
        return success

    def test_text_generation_short(self):
        """Test text generation endpoint with short duration"""
        success, response = self.run_test(
            "Generate Text (Short - 2 minutes)",
            "POST",
            "text/generate",
            200,
            data={
                "prompt": "The benefits of renewable energy in modern society",
                "duration_minutes": 2,
                "language": "en"
            },
            timeout=60
        )
        
        if success and response:
            print(f"   Generated {response.get('word_count', 0)} words")
            print(f"   Estimated duration: {response.get('estimated_duration', 0):.1f} seconds")
            print(f"   Text preview: {response.get('text', '')[:100]}...")
            return response.get('text')
        
        return None

    def test_text_generation_long(self):
        """Test text generation endpoint with longer duration"""
        success, response = self.run_test(
            "Generate Text (Long - 10 minutes)",
            "POST",
            "text/generate",
            200,
            data={
                "prompt": "A comprehensive guide to artificial intelligence and machine learning",
                "duration_minutes": 10,
                "language": "en"
            },
            timeout=90
        )
        
        if success and response:
            print(f"   Generated {response.get('word_count', 0)} words")
            print(f"   Estimated duration: {response.get('estimated_duration', 0):.1f} seconds")
            print(f"   Text preview: {response.get('text', '')[:100]}...")
            return response.get('text')
        
        return None

    def test_audio_synthesis_normal(self, text, language="en"):
        """Test audio synthesis with normal speed"""
        if not text:
            print("⚠️  Skipping audio synthesis - missing text")
            return None
            
        success, response = self.run_test(
            "Synthesize Audio (Normal Speed)",
            "POST",
            "audio/synthesize",
            200,
            data={
                "text": text[:800],  # Reasonable length for testing
                "language": language,
                "slow": False
            },
            timeout=60
        )
        
        if success and response:
            audio_id = response.get('id')
            print(f"   Audio ID: {audio_id}")
            print(f"   Audio URL: {response.get('audio_url')}")
            print(f"   Language: {response.get('language')}")
            if audio_id:
                self.generated_audio_ids.append(audio_id)
            return audio_id
        
        return None

    def test_audio_synthesis_slow(self, text, language="en"):
        """Test audio synthesis with slow speed"""
        if not text:
            print("⚠️  Skipping audio synthesis - missing text")
            return None
            
        success, response = self.run_test(
            "Synthesize Audio (Slow Speed)",
            "POST",
            "audio/synthesize",
            200,
            data={
                "text": text[:500],  # Shorter text for slow speech
                "language": language,
                "slow": True
            },
            timeout=60
        )
        
        if success and response:
            audio_id = response.get('id')
            print(f"   Audio ID: {audio_id}")
            print(f"   Audio URL: {response.get('audio_url')}")
            print(f"   Language: {response.get('language')}")
            if audio_id:
                self.generated_audio_ids.append(audio_id)
            return audio_id
        
        return None

    def test_audio_synthesis_different_languages(self, text):
        """Test audio synthesis with different languages"""
        languages_to_test = ["es", "ru", "fr"]
        audio_ids = []
        
        for lang in languages_to_test:
            success, response = self.run_test(
                f"Synthesize Audio ({lang.upper()})",
                "POST",
                "audio/synthesize",
                200,
                data={
                    "text": "Hello, this is a test message in different languages.",
                    "language": lang,
                    "slow": False
                },
                timeout=60
            )
            
            if success and response:
                audio_id = response.get('id')
                if audio_id:
                    audio_ids.append(audio_id)
                    self.generated_audio_ids.append(audio_id)
        
        return audio_ids

    def test_audio_synthesis_long_text(self):
        """Test audio synthesis with long text (2000+ words)"""
        long_text = """
        Artificial intelligence represents one of the most significant technological advances of our time. 
        It encompasses a broad range of technologies and methodologies that enable machines to perform tasks 
        that typically require human intelligence. From machine learning algorithms that can recognize patterns 
        in vast datasets to natural language processing systems that can understand and generate human language, 
        AI is transforming virtually every aspect of our lives.
        
        The history of artificial intelligence dates back to the 1950s when computer scientists first began 
        exploring the possibility of creating machines that could think and learn like humans. Early pioneers 
        like Alan Turing, John McCarthy, and Marvin Minsky laid the groundwork for what would become a 
        revolutionary field of study. Turing's famous test, proposed in 1950, suggested that a machine 
        could be considered intelligent if it could engage in conversations with humans without being 
        detected as a machine.
        
        Machine learning, a subset of AI, has become particularly prominent in recent years. This approach 
        involves training algorithms on large amounts of data so they can make predictions or decisions 
        without being explicitly programmed for every possible scenario. Deep learning, which uses neural 
        networks with multiple layers, has proven especially effective for tasks like image recognition, 
        speech processing, and natural language understanding.
        
        The applications of AI are virtually limitless. In healthcare, AI systems can analyze medical images 
        to detect diseases earlier and more accurately than human doctors in some cases. In transportation, 
        autonomous vehicles use AI to navigate roads safely. In finance, AI algorithms can detect fraudulent 
        transactions and make investment decisions. In entertainment, AI can recommend movies, music, and 
        books based on individual preferences.
        
        However, the rapid advancement of AI also raises important ethical and societal questions. Concerns 
        about job displacement, privacy, bias in AI systems, and the potential for misuse of AI technology 
        are all valid and require careful consideration. As AI becomes more powerful and ubiquitous, it's 
        crucial that we develop appropriate governance frameworks and ethical guidelines to ensure that 
        AI benefits humanity as a whole.
        
        Looking to the future, AI is expected to continue evolving at a rapid pace. Researchers are working 
        on developing artificial general intelligence (AGI), which would be capable of performing any 
        intellectual task that a human can do. While this goal remains elusive, the progress being made 
        in narrow AI applications continues to be remarkable and transformative.
        """ * 3  # Repeat to make it longer
        
        success, response = self.run_test(
            "Synthesize Long Text (2000+ words)",
            "POST",
            "audio/synthesize",
            200,
            data={
                "text": long_text,
                "language": "en",
                "slow": False
            },
            timeout=120  # Longer timeout for long text
        )
        
        if success and response:
            audio_id = response.get('id')
            if audio_id:
                self.generated_audio_ids.append(audio_id)
            return audio_id
        
        return None

    def test_audio_download(self, audio_id):
        """Test audio download endpoint"""
        if not audio_id:
            print("⚠️  Skipping audio download - missing audio ID")
            return False
            
        success, _ = self.run_test(
            f"Download Audio ({audio_id[:8]}...)",
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
            if len(response) > 0:
                print(f"   Latest item language: {response[0].get('language', 'Unknown')}")
        
        return success

    def verify_audio_files_exist(self):
        """Verify that audio files are actually created on disk"""
        audio_dir = Path("/app/backend/audio_files")
        if not audio_dir.exists():
            print("❌ Audio directory does not exist")
            return False
        
        files_found = 0
        for audio_id in self.generated_audio_ids:
            audio_file = audio_dir / f"{audio_id}.mp3"
            if audio_file.exists():
                files_found += 1
                file_size = audio_file.stat().st_size
                print(f"✅ Audio file exists: {audio_id}.mp3 ({file_size} bytes)")
            else:
                print(f"❌ Audio file missing: {audio_id}.mp3")
        
        print(f"📁 Audio files verification: {files_found}/{len(self.generated_audio_ids)} files found")
        return files_found == len(self.generated_audio_ids)

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Text-to-Speech API Tests (gTTS)")
        print(f"   Base URL: {self.base_url}")
        print("=" * 60)
        
        # Test 1: Root endpoint
        self.test_root_endpoint()
        
        # Test 2: Get languages (gTTS)
        sample_language = self.test_languages_endpoint()
        
        # Test 3: Generate text (short duration)
        generated_text_short = self.test_text_generation_short()
        
        # Test 4: Generate text (long duration)
        generated_text_long = self.test_text_generation_long()
        
        # Test 5: Synthesize audio (normal speed)
        audio_id_normal = self.test_audio_synthesis_normal(generated_text_short, sample_language)
        
        # Test 6: Synthesize audio (slow speed)
        audio_id_slow = self.test_audio_synthesis_slow(generated_text_short, sample_language)
        
        # Test 7: Synthesize audio in different languages
        multi_lang_audio_ids = self.test_audio_synthesis_different_languages(generated_text_short)
        
        # Test 8: Synthesize long text
        long_audio_id = self.test_audio_synthesis_long_text()
        
        # Wait for audio processing
        if self.generated_audio_ids:
            print("\n⏳ Waiting for audio processing...")
            time.sleep(3)
        
        # Test 9: Download audio files
        for audio_id in self.generated_audio_ids[:3]:  # Test first 3 downloads
            self.test_audio_download(audio_id)
        
        # Test 10: Get history
        self.test_history_endpoint()
        
        # Test 11: Verify audio files exist on disk
        self.verify_audio_files_exist()
        
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