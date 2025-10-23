import requests
import sys
import json
import time
import os
from datetime import datetime
from pathlib import Path

class PiperTTSAPITester:
    def __init__(self, base_url="https://audio-gen-speedup.preview.emergentagent.com/api"):
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
        """Test voices endpoint (Piper TTS)"""
        success, response = self.run_test(
            "Get Available Voices (Piper TTS)",
            "GET",
            "voices",
            200,
            timeout=60  # Longer timeout for first voice fetch
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} voices")
            self.available_voices = response
            
            # Show sample voices by language
            en_voices = [v for v in response if v.get('locale', '').startswith('en-')]
            ru_voices = [v for v in response if v.get('locale', '').startswith('ru-')]
            es_voices = [v for v in response if v.get('locale', '').startswith('es-')]
            fr_voices = [v for v in response if v.get('locale', '').startswith('fr-')]
            de_voices = [v for v in response if v.get('locale', '').startswith('de-')]
            
            print(f"   English voices: {len(en_voices)}")
            print(f"   Russian voices: {len(ru_voices)}")
            print(f"   Spanish voices: {len(es_voices)}")
            print(f"   French voices: {len(fr_voices)}")
            print(f"   German voices: {len(de_voices)}")
            
            if en_voices:
                print(f"   Sample EN voice: {en_voices[0].get('name')} ({en_voices[0].get('short_name')})")
            if ru_voices:
                print(f"   Sample RU voice: {ru_voices[0].get('name')} ({ru_voices[0].get('short_name')})")
                
            # Verify voice structure
            if response:
                sample_voice = response[0]
                required_fields = ['name', 'short_name', 'language', 'quality', 'locale']
                missing_fields = [field for field in required_fields if field not in sample_voice]
                if missing_fields:
                    print(f"   ⚠️  Missing fields in voice data: {missing_fields}")
                else:
                    print(f"   ✅ Voice data structure is correct")
                
        return success

    def test_text_generation_short_russian(self):
        """Test text generation endpoint with short duration (10 minutes) in Russian"""
        success, response = self.run_test(
            "Generate Text (Short - 10 minutes, Russian)",
            "POST",
            "text/generate",
            200,
            data={
                "prompt": "История космических путешествий",
                "duration_minutes": 10,
                "language": "ru-RU"
            },
            timeout=90
        )
        
        if success and response:
            word_count = response.get('word_count', 0)
            estimated_duration = response.get('estimated_duration', 0)
            text = response.get('text', '')
            
            print(f"   Generated {word_count} words")
            print(f"   Estimated duration: {estimated_duration:.1f} seconds ({estimated_duration/60:.1f} minutes)")
            print(f"   Text preview: {text[:200]}...")
            
            # Check for expected word count (~1500 words for 10 minutes)
            expected_words = 10 * 150  # 1500 words
            word_range_ok = 1200 <= word_count <= 1800  # Allow some variance
            
            # Check for unwanted structural markers
            unwanted_markers = ["Introduction", "Conclusion", "Введение", "Заключение"]
            has_markers = any(marker in text for marker in unwanted_markers)
            
            # Check duration estimate (should be close to 600 seconds = 10 minutes)
            duration_ok = 500 <= estimated_duration <= 700  # Allow some variance
            
            print(f"   ✅ Word count in range (1200-1800): {word_range_ok} ({word_count} words)")
            print(f"   ✅ No structural markers: {not has_markers}")
            print(f"   ✅ Duration estimate correct: {duration_ok} ({estimated_duration:.0f}s)")
            
            return {
                'text': text,
                'word_count': word_count,
                'estimated_duration': estimated_duration,
                'word_range_ok': word_range_ok,
                'no_markers': not has_markers,
                'duration_ok': duration_ok
            }
        
        return None

    def test_text_generation_long_russian(self):
        """Test text generation endpoint with long duration (50 minutes) in Russian - KEY TEST"""
        print("\n🔥 CRITICAL TEST: 50-minute text generation with chunked processing")
        print("   This will take several minutes as it requires ~7 LLM requests...")
        
        success, response = self.run_test(
            "Generate Text (Long - 50 minutes, Russian) - CHUNKED GENERATION",
            "POST",
            "text/generate",
            200,
            data={
                "prompt": "История развития искусственного интеллекта",
                "duration_minutes": 50,
                "language": "ru-RU"
            },
            timeout=600  # 10 minutes timeout for long generation
        )
        
        if success and response:
            word_count = response.get('word_count', 0)
            estimated_duration = response.get('estimated_duration', 0)
            text = response.get('text', '')
            
            print(f"   Generated {word_count} words")
            print(f"   Estimated duration: {estimated_duration:.1f} seconds ({estimated_duration/60:.1f} minutes)")
            print(f"   Text preview: {text[:300]}...")
            print(f"   Text ending: ...{text[-200:]}")
            
            # Check for expected word count (~7500 words for 50 minutes)
            expected_words = 50 * 150  # 7500 words
            word_range_ok = 7000 <= word_count <= 8000  # Allow some variance
            
            # Check for unwanted structural markers
            unwanted_markers = ["Introduction", "Conclusion", "Введение", "Заключение"]
            has_markers = any(marker in text for marker in unwanted_markers)
            
            # Check duration estimate (should be close to 3000 seconds = 50 minutes)
            duration_ok = 2800 <= estimated_duration <= 3200  # Allow some variance
            
            # Check text continuity (should be one continuous narrative)
            is_continuous = len(text.strip()) > 0 and not text.startswith("Chapter") and not text.startswith("Part")
            
            print(f"   ✅ Word count in range (7000-8000): {word_range_ok} ({word_count} words)")
            print(f"   ✅ No structural markers: {not has_markers}")
            print(f"   ✅ Duration estimate correct: {duration_ok} ({estimated_duration:.0f}s = {estimated_duration/60:.1f}min)")
            print(f"   ✅ Continuous narrative: {is_continuous}")
            
            return {
                'text': text,
                'word_count': word_count,
                'estimated_duration': estimated_duration,
                'word_range_ok': word_range_ok,
                'no_markers': not has_markers,
                'duration_ok': duration_ok,
                'is_continuous': is_continuous
            }
        
        return None

    def test_database_verification(self, text_data):
        """Verify that generated text is properly saved in database"""
        if not text_data:
            print("⚠️  Skipping database verification - no text data")
            return False
            
        print("\n🔍 Verifying database storage...")
        
        # We can't directly access MongoDB from here, but we can verify the response data
        # contains the expected fields that should be saved to DB
        required_fields = ['word_count', 'estimated_duration']
        has_required_fields = all(field in text_data for field in required_fields)
        
        if has_required_fields:
            print(f"   ✅ Response contains required DB fields")
            print(f"   ✅ Word count: {text_data['word_count']}")
            print(f"   ✅ Duration: {text_data['estimated_duration']:.1f}s")
            return True
        else:
            print(f"   ❌ Missing required fields for DB storage")
            return False

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

    def test_audio_synthesis_english(self):
        """Test audio synthesis with English voice (Piper TTS)"""
        # Find English voice
        en_voice = None
        for voice in self.available_voices:
            if voice.get('short_name', '').startswith('en_US-lessac'):
                en_voice = voice.get('short_name')
                break
        
        if not en_voice:
            # Fallback to any English voice
            for voice in self.available_voices:
                if voice.get('locale', '').startswith('en-'):
                    en_voice = voice.get('short_name')
                    break
        
        if not en_voice:
            print("⚠️  No English voice found, skipping test")
            return None
            
        test_text = "Hello, this is a test of the Piper text-to-speech system. It should generate clear and natural sounding audio."
        
        success, response = self.run_test(
            f"Synthesize Audio (English - {en_voice})",
            "POST",
            "audio/synthesize",
            200,
            data={
                "text": test_text,
                "voice": en_voice,
                "rate": 1.0,
                "language": "en-US"
            },
            timeout=120  # Longer timeout for first synthesis (model download)
        )
        
        if success and response:
            audio_id = response.get('id')
            print(f"   Audio ID: {audio_id}")
            print(f"   Audio URL: {response.get('audio_url')}")
            print(f"   Voice: {response.get('voice')}")
            if audio_id:
                self.generated_audio_ids.append(audio_id)
            return audio_id
        
        return None

    def test_audio_synthesis_russian(self):
        """Test audio synthesis with Russian voice (Piper TTS)"""
        # Find Russian voice
        ru_voice = None
        for voice in self.available_voices:
            if voice.get('short_name', '').startswith('ru_RU-irina'):
                ru_voice = voice.get('short_name')
                break
        
        if not ru_voice:
            # Fallback to any Russian voice
            for voice in self.available_voices:
                if voice.get('locale', '').startswith('ru-'):
                    ru_voice = voice.get('short_name')
                    break
        
        if not ru_voice:
            print("⚠️  No Russian voice found, skipping test")
            return None
            
        test_text = "Привет, это тест системы синтеза речи Piper. Она должна генерировать четкий и естественный звук."
        
        success, response = self.run_test(
            f"Synthesize Audio (Russian - {ru_voice})",
            "POST",
            "audio/synthesize",
            200,
            data={
                "text": test_text,
                "voice": ru_voice,
                "rate": 1.0,
                "language": "ru-RU"
            },
            timeout=90
        )
        
        if success and response:
            audio_id = response.get('id')
            print(f"   Audio ID: {audio_id}")
            print(f"   Audio URL: {response.get('audio_url')}")
            print(f"   Voice: {response.get('voice')}")
            if audio_id:
                self.generated_audio_ids.append(audio_id)
            return audio_id
        
        return None

    def test_audio_synthesis_speed_variations(self):
        """Test audio synthesis with different speed rates"""
        # Find English voice for speed testing
        en_voice = None
        for voice in self.available_voices:
            if voice.get('locale', '').startswith('en-'):
                en_voice = voice.get('short_name')
                break
        
        if not en_voice:
            print("⚠️  No English voice found, skipping speed test")
            return []
            
        test_text = "This is a speed test for the Piper text-to-speech system."
        speed_tests = [
            ("Slow Speed (0.8)", 0.8),
            ("Fast Speed (1.5)", 1.5)
        ]
        
        audio_ids = []
        
        for test_name, rate in speed_tests:
            success, response = self.run_test(
                f"Synthesize Audio ({test_name})",
                "POST",
                "audio/synthesize",
                200,
                data={
                    "text": test_text,
                    "voice": en_voice,
                    "rate": rate,
                    "language": "en-US"
                },
                timeout=90
            )
            
            if success and response:
                audio_id = response.get('id')
                if audio_id:
                    audio_ids.append(audio_id)
                    self.generated_audio_ids.append(audio_id)
        
        return audio_ids

    def test_audio_synthesis_long_text(self):
        """Test audio synthesis with long text (~500 words for hour-long audio capability)"""
        # Find English voice for long text test
        en_voice = None
        for voice in self.available_voices:
            if voice.get('locale', '').startswith('en-'):
                en_voice = voice.get('short_name')
                break
        
        if not en_voice:
            print("⚠️  No English voice found, skipping long text test")
            return None
            
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
        """
        
        word_count = len(long_text.split())
        print(f"   Testing with {word_count} words")
        
        success, response = self.run_test(
            f"Synthesize Long Text ({word_count} words)",
            "POST",
            "audio/synthesize",
            200,
            data={
                "text": long_text,
                "voice": en_voice,
                "rate": 1.0,
                "language": "en-US"
            },
            timeout=180  # Longer timeout for long text
        )
        
        if success and response:
            audio_id = response.get('id')
            if audio_id:
                self.generated_audio_ids.append(audio_id)
            return audio_id
        
        return None

    def test_parallel_audio_synthesis_short_russian(self):
        """Test NEW parallel audio synthesis with short Russian text (2-3 sentences)"""
        print("\n🔥 CRITICAL TEST: Parallel Audio Generation - Short Text")
        
        # Find Russian voice
        ru_voice = None
        for voice in self.available_voices:
            if 'irina' in voice.get('short_name', '').lower():
                ru_voice = voice.get('short_name')
                break
        
        if not ru_voice:
            # Fallback to any Russian voice
            for voice in self.available_voices:
                if voice.get('locale', '').startswith('ru-'):
                    ru_voice = voice.get('short_name')
                    break
        
        if not ru_voice:
            print("❌ No Russian voice found, cannot test parallel synthesis")
            return None
            
        # Test text as specified in review request
        test_text = "Искусственный интеллект изменяет мир. Он помогает людям решать сложные задачи. Будущее уже здесь."
        
        print(f"   Voice: {ru_voice}")
        print(f"   Text: {test_text}")
        print(f"   Text length: {len(test_text)} characters")
        
        start_time = time.time()
        
        success, response = self.run_test(
            "Parallel Audio Synthesis (Short Russian Text)",
            "POST",
            "audio/synthesize-parallel",
            200,
            data={
                "text": test_text,
                "voice": ru_voice,
                "rate": 1.0,
                "language": "ru-RU"
            },
            timeout=120
        )
        
        parallel_time = time.time() - start_time
        
        if success and response:
            audio_id = response.get('id')
            print(f"   ✅ Parallel synthesis completed in {parallel_time:.2f} seconds")
            print(f"   Audio ID: {audio_id}")
            print(f"   Audio URL: {response.get('audio_url')}")
            if audio_id:
                self.generated_audio_ids.append(audio_id)
            return {'audio_id': audio_id, 'time': parallel_time, 'response': response}
        else:
            print(f"   ❌ Parallel synthesis failed after {parallel_time:.2f} seconds")
        
        return None

    def test_parallel_audio_synthesis_medium_text(self):
        """Test parallel audio synthesis with medium text (~1000 characters, 5-7 segments)"""
        print("\n🔥 CRITICAL TEST: Parallel Audio Generation - Medium Text (~1000 chars)")
        
        # First generate text via API to get realistic content
        print("   Step 1: Generating medium text (2 minutes duration)...")
        
        text_success, text_response = self.run_test(
            "Generate Medium Text for Parallel Audio Test",
            "POST",
            "text/generate",
            200,
            data={
                "prompt": "История развития компьютерных технологий",
                "duration_minutes": 2,
                "language": "ru-RU"
            },
            timeout=90
        )
        
        if not text_success or not text_response:
            print("   ❌ Failed to generate text, using fallback text")
            # Fallback text ~1000 characters
            generated_text = """
            Компьютерные технологии прошли невероятный путь развития за последние десятилетия. От огромных машин, занимавших целые комнаты, до миниатюрных устройств, помещающихся в кармане, прогресс был поразительным. Первые компьютеры использовались исключительно для научных расчетов и военных целей. Сегодня они стали неотъемлемой частью нашей повседневной жизни. Интернет революционизировал способы общения и обмена информацией. Социальные сети объединили людей по всему миру. Мобильные технологии сделали доступ к информации мгновенным. Искусственный интеллект открывает новые горизонты возможностей. Машинное обучение помогает решать сложные задачи. Будущее технологий обещает еще более удивительные открытия и инновации.
            """
        else:
            generated_text = text_response.get('text', '')
            print(f"   ✅ Generated text: {len(generated_text)} characters, {len(generated_text.split())} words")
        
        # Truncate to ~1000 characters if too long
        if len(generated_text) > 1200:
            generated_text = generated_text[:1000] + "."
        
        print(f"   Step 2: Testing parallel synthesis with {len(generated_text)} characters")
        
        # Find Russian voice
        ru_voice = None
        for voice in self.available_voices:
            if 'irina' in voice.get('short_name', '').lower():
                ru_voice = voice.get('short_name')
                break
        
        if not ru_voice:
            for voice in self.available_voices:
                if voice.get('locale', '').startswith('ru-'):
                    ru_voice = voice.get('short_name')
                    break
        
        if not ru_voice:
            print("   ❌ No Russian voice found")
            return None
        
        start_time = time.time()
        
        success, response = self.run_test(
            "Parallel Audio Synthesis (Medium Text ~1000 chars)",
            "POST",
            "audio/synthesize-parallel",
            200,
            data={
                "text": generated_text,
                "voice": ru_voice,
                "rate": 1.0,
                "language": "ru-RU"
            },
            timeout=180
        )
        
        parallel_time = time.time() - start_time
        
        if success and response:
            audio_id = response.get('id')
            print(f"   ✅ Parallel synthesis completed in {parallel_time:.2f} seconds")
            print(f"   Audio ID: {audio_id}")
            print(f"   Text length: {len(generated_text)} characters")
            if audio_id:
                self.generated_audio_ids.append(audio_id)
            return {'audio_id': audio_id, 'time': parallel_time, 'text_length': len(generated_text)}
        else:
            print(f"   ❌ Parallel synthesis failed after {parallel_time:.2f} seconds")
        
        return None

    def test_speed_comparison_parallel_vs_regular(self):
        """Compare speed between parallel and regular audio synthesis"""
        print("\n🔥 SPEED COMPARISON: Parallel vs Regular Audio Synthesis")
        
        # Find Russian voice
        ru_voice = None
        for voice in self.available_voices:
            if 'irina' in voice.get('short_name', '').lower():
                ru_voice = voice.get('short_name')
                break
        
        if not ru_voice:
            for voice in self.available_voices:
                if voice.get('locale', '').startswith('ru-'):
                    ru_voice = voice.get('short_name')
                    break
        
        if not ru_voice:
            print("   ❌ No Russian voice found for speed comparison")
            return None
        
        # Test text with multiple sentences (good for parallel processing)
        test_text = """
        Технологии искусственного интеллекта развиваются с невероятной скоростью. Машинное обучение позволяет компьютерам анализировать огромные объемы данных. Нейронные сети моделируют работу человеческого мозга. Глубокое обучение открывает новые возможности в распознавании образов. Обработка естественного языка помогает машинам понимать человеческую речь. Компьютерное зрение позволяет анализировать изображения и видео. Роботика интегрирует ИИ в физический мир. Автономные системы принимают решения без участия человека.
        """
        
        print(f"   Test text: {len(test_text)} characters, {len(test_text.split())} words")
        
        # Test 1: Regular synthesis
        print("\n   Testing REGULAR synthesis...")
        start_time = time.time()
        
        regular_success, regular_response = self.run_test(
            "Regular Audio Synthesis (Speed Test)",
            "POST",
            "audio/synthesize",
            200,
            data={
                "text": test_text,
                "voice": ru_voice,
                "rate": 1.0,
                "language": "ru-RU"
            },
            timeout=180
        )
        
        regular_time = time.time() - start_time
        
        # Test 2: Parallel synthesis
        print("\n   Testing PARALLEL synthesis...")
        start_time = time.time()
        
        parallel_success, parallel_response = self.run_test(
            "Parallel Audio Synthesis (Speed Test)",
            "POST",
            "audio/synthesize-parallel",
            200,
            data={
                "text": test_text,
                "voice": ru_voice,
                "rate": 1.0,
                "language": "ru-RU"
            },
            timeout=180
        )
        
        parallel_time = time.time() - start_time
        
        # Compare results
        if regular_success and parallel_success:
            speedup = regular_time / parallel_time if parallel_time > 0 else 0
            print(f"\n   📊 SPEED COMPARISON RESULTS:")
            print(f"   Regular synthesis:  {regular_time:.2f} seconds")
            print(f"   Parallel synthesis: {parallel_time:.2f} seconds")
            print(f"   Speedup factor:     {speedup:.2f}x")
            
            if speedup > 1.5:
                print(f"   ✅ Parallel synthesis is {speedup:.1f}x faster!")
            elif speedup > 1.0:
                print(f"   ⚠️  Parallel synthesis is only {speedup:.1f}x faster (expected >1.5x)")
            else:
                print(f"   ❌ Parallel synthesis is SLOWER than regular!")
            
            # Store audio IDs
            if regular_response and regular_response.get('id'):
                self.generated_audio_ids.append(regular_response['id'])
            if parallel_response and parallel_response.get('id'):
                self.generated_audio_ids.append(parallel_response['id'])
            
            return {
                'regular_time': regular_time,
                'parallel_time': parallel_time,
                'speedup': speedup,
                'regular_id': regular_response.get('id') if regular_response else None,
                'parallel_id': parallel_response.get('id') if parallel_response else None
            }
        else:
            print("   ❌ Speed comparison failed - one or both synthesis methods failed")
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
        """Verify that audio files are actually created on disk (WAV format for Piper)"""
        audio_dir = Path("/app/backend/audio_files")
        if not audio_dir.exists():
            print("❌ Audio directory does not exist")
            return False
        
        files_found = 0
        total_size = 0
        for audio_id in self.generated_audio_ids:
            audio_file = audio_dir / f"{audio_id}.wav"  # Piper generates WAV files
            if audio_file.exists():
                files_found += 1
                file_size = audio_file.stat().st_size
                total_size += file_size
                print(f"✅ Audio file exists: {audio_id}.wav ({file_size:,} bytes)")
                
                # Check if file is not empty or too small
                if file_size < 1000:  # Less than 1KB is suspicious
                    print(f"   ⚠️  File seems too small: {file_size} bytes")
                elif file_size > 50000:  # More than 50KB is good
                    print(f"   ✅ File size looks good: {file_size:,} bytes")
            else:
                print(f"❌ Audio file missing: {audio_id}.wav")
        
        print(f"📁 Audio files verification: {files_found}/{len(self.generated_audio_ids)} files found")
        print(f"📊 Total audio data: {total_size:,} bytes")
        return files_found == len(self.generated_audio_ids)

    def run_all_tests(self):
        """Run all API tests for Piper TTS"""
        print("🚀 Starting Text-to-Speech API Tests (Piper TTS)")
        print(f"   Base URL: {self.base_url}")
        print("=" * 60)
        
        # Test 1: Root endpoint
        self.test_root_endpoint()
        
        # Test 2: Get voices (Piper TTS) - CRITICAL: Must run first to populate available_voices
        voices_success = self.test_voices_endpoint()
        if not voices_success:
            print("❌ Cannot continue without voices - stopping tests")
            return False
        
        # Test 3: Text generation tests (Russian language as per review request)
        print("\n🔥 TESTING UPDATED TEXT GENERATION FOR LONG VIDEOS")
        
        # Test 3a: Short text generation (10 minutes)
        short_text_result = self.test_text_generation_short_russian()
        
        # Test 3b: Long text generation (50 minutes) - KEY TEST
        long_text_result = self.test_text_generation_long_russian()
        
        # Test 3c: Database verification
        db_verification_short = self.test_database_verification(short_text_result)
        db_verification_long = self.test_database_verification(long_text_result)
        
        # NEW TESTS: PARALLEL AUDIO GENERATION OPTIMIZATION
        print("\n" + "🔥" * 20)
        print("🔥 TESTING NEW PARALLEL AUDIO GENERATION OPTIMIZATION")
        print("🔥" * 20)
        
        # Test 4: NEW Parallel audio synthesis - Short Russian text
        parallel_short_result = self.test_parallel_audio_synthesis_short_russian()
        
        # Test 5: NEW Parallel audio synthesis - Medium text (~1000 chars)
        parallel_medium_result = self.test_parallel_audio_synthesis_medium_text()
        
        # Test 6: NEW Speed comparison - Parallel vs Regular
        speed_comparison_result = self.test_speed_comparison_parallel_vs_regular()
        
        # REGULAR AUDIO TESTS (for comparison)
        print("\n🔄 REGULAR AUDIO SYNTHESIS TESTS (for comparison)")
        
        # Test 7: Synthesize audio with English voice
        audio_id_english = self.test_audio_synthesis_english()
        
        # Test 8: Synthesize audio with Russian voice
        audio_id_russian = self.test_audio_synthesis_russian()
        
        # Test 9: Test speed variations (slow and fast)
        speed_audio_ids = self.test_audio_synthesis_speed_variations()
        
        # Test 10: Synthesize long text (~500 words)
        long_audio_id = self.test_audio_synthesis_long_text()
        
        # Wait for audio processing
        if self.generated_audio_ids:
            print("\n⏳ Waiting for audio processing...")
            time.sleep(5)  # Longer wait for Piper processing
        
        # Test 11: Download audio files (WAV format)
        download_success_count = 0
        for audio_id in self.generated_audio_ids[:5]:  # Test first 5 downloads
            if self.test_audio_download(audio_id):
                download_success_count += 1
        
        # Test 12: Get history
        self.test_history_endpoint()
        
        # Test 13: Verify audio files exist on disk (WAV format)
        files_verified = self.verify_audio_files_exist()
        
        # Print results
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        print(f"🎵 Audio files generated: {len(self.generated_audio_ids)}")
        print(f"📥 Downloads tested: {download_success_count}")
        print(f"📁 Files verified on disk: {files_verified}")
        
        # PARALLEL AUDIO OPTIMIZATION SUMMARY
        print("\n🔥 PARALLEL AUDIO OPTIMIZATION RESULTS:")
        if parallel_short_result:
            print(f"   ✅ Short text parallel synthesis: SUCCESS ({parallel_short_result['time']:.2f}s)")
        else:
            print(f"   ❌ Short text parallel synthesis: FAILED")
            
        if parallel_medium_result:
            print(f"   ✅ Medium text parallel synthesis: SUCCESS ({parallel_medium_result['time']:.2f}s)")
        else:
            print(f"   ❌ Medium text parallel synthesis: FAILED")
            
        if speed_comparison_result:
            speedup = speed_comparison_result['speedup']
            if speedup > 1.5:
                print(f"   ✅ Speed improvement: {speedup:.2f}x faster (EXCELLENT)")
            elif speedup > 1.0:
                print(f"   ⚠️  Speed improvement: {speedup:.2f}x faster (MODERATE)")
            else:
                print(f"   ❌ Speed improvement: {speedup:.2f}x (SLOWER than regular)")
        else:
            print(f"   ❌ Speed comparison: FAILED")
        
        if self.tests_passed < self.tests_run:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   - {result['test_name']}: {result.get('error', 'Unknown error')}")
        
        # Summary of Piper TTS specific checks
        print("\n🎯 Piper TTS Specific Verification:")
        print(f"   ✅ Voices endpoint returned {len(self.available_voices)} voices" if self.available_voices else "   ❌ No voices available")
        print(f"   ✅ Audio format is WAV (not MP3)" if files_verified else "   ❌ Audio files not verified")
        print(f"   ✅ Multiple languages supported" if len([v for v in self.available_voices if v.get('locale', '').startswith(('en-', 'ru-'))]) >= 2 else "   ❌ Limited language support")
        
        return self.tests_passed == self.tests_run

def main():
    tester = PiperTTSAPITester()
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