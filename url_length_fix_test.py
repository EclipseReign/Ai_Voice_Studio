#!/usr/bin/env python3
"""
CRITICAL URL LENGTH FIX TESTING
===============================

This test specifically addresses the user's reported issue:
- Large texts (50 minutes) were not being synthesized
- Button would just reset without errors
- Problem was GET method URL length limit (~8000 chars) vs 50-minute text (~50,000 chars)
- Fix: Changed /api/audio/synthesize-with-progress from GET to POST with JSON body

Test Priority:
1. CRITICAL: Generate 50-minute text and test audio synthesis
2. REGRESSION: Test short texts (1-2 minutes) still work
3. MANUAL INPUT: Test large text input manually
"""

import requests
import json
import time
import sys
from datetime import datetime
from pathlib import Path

class URLLengthFixTester:
    def __init__(self, base_url="https://subvoice.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.session = requests.Session()
        # Add admin credentials for testing (from test_result.md)
        self.session.cookies.set('session_token', 'admin_session_token')
        self.test_results = []
        
    def log_result(self, test_name, success, details):
        """Log test result"""
        result = {
            'test_name': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        return success

    def test_voices_available(self):
        """Test that voices are available for synthesis"""
        print("\n🔍 Testing voices availability...")
        
        try:
            response = self.session.get(f"{self.base_url}/voices", timeout=30)
            
            if response.status_code == 200:
                voices = response.json()
                
                # Find Russian and English voices
                ru_voices = [v for v in voices if v.get('locale', '').startswith('ru-')]
                en_voices = [v for v in voices if v.get('locale', '').startswith('en-')]
                
                details = f"Found {len(voices)} total voices, {len(ru_voices)} Russian, {len(en_voices)} English"
                
                if ru_voices and en_voices:
                    self.ru_voice = ru_voices[0]['short_name']
                    self.en_voice = en_voices[0]['short_name']
                    return self.log_result("Voices Available", True, details)
                else:
                    return self.log_result("Voices Available", False, "Missing Russian or English voices")
            else:
                return self.log_result("Voices Available", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            return self.log_result("Voices Available", False, f"Error: {str(e)}")

    def generate_large_text(self, duration_minutes=50):
        """Generate large text for testing URL length limits"""
        print(f"\n🔍 Generating {duration_minutes}-minute text...")
        
        try:
            # Use POST method for text generation (should work)
            response = self.session.post(
                f"{self.base_url}/text/generate",
                json={
                    "prompt": "История развития искусственного интеллекта и его влияние на современное общество",
                    "duration_minutes": duration_minutes,
                    "language": "ru-RU"
                },
                timeout=600  # 10 minutes for large text generation
            )
            
            if response.status_code == 200:
                data = response.json()
                text = data.get('text', '')
                word_count = data.get('word_count', 0)
                
                # Calculate character count and URL length if it were GET
                char_count = len(text)
                estimated_url_length = len(f"{self.base_url}/audio/synthesize-with-progress?text={text}&voice=ru_RU-irina-medium&rate=1.0&language=ru-RU")
                
                details = f"Generated {word_count} words, {char_count} chars. Estimated URL length: {estimated_url_length} chars"
                
                # Check if this would exceed URL limits
                url_limit_exceeded = estimated_url_length > 8000
                
                if url_limit_exceeded:
                    details += f" (EXCEEDS 8000 char URL limit by {estimated_url_length - 8000} chars)"
                
                self.large_text = text
                self.large_text_chars = char_count
                
                return self.log_result(f"Generate {duration_minutes}-minute Text", True, details)
            else:
                return self.log_result(f"Generate {duration_minutes}-minute Text", False, f"HTTP {response.status_code}: {response.text[:200]}")
                
        except Exception as e:
            return self.log_result(f"Generate {duration_minutes}-minute Text", False, f"Error: {str(e)}")

    def generate_short_text(self, duration_minutes=2):
        """Generate short text for regression testing"""
        print(f"\n🔍 Generating {duration_minutes}-minute text (regression test)...")
        
        try:
            response = self.session.post(
                f"{self.base_url}/text/generate",
                json={
                    "prompt": "Преимущества возобновляемых источников энергии",
                    "duration_minutes": duration_minutes,
                    "language": "ru-RU"
                },
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                text = data.get('text', '')
                word_count = data.get('word_count', 0)
                char_count = len(text)
                
                details = f"Generated {word_count} words, {char_count} chars"
                
                self.short_text = text
                self.short_text_chars = char_count
                
                return self.log_result(f"Generate {duration_minutes}-minute Text", True, details)
            else:
                return self.log_result(f"Generate {duration_minutes}-minute Text", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            return self.log_result(f"Generate {duration_minutes}-minute Text", False, f"Error: {str(e)}")

    def test_audio_synthesis_post_method(self, text, test_name, voice=None):
        """Test audio synthesis using POST method (the fix)"""
        print(f"\n🔥 CRITICAL TEST: {test_name} - POST Method Audio Synthesis")
        print(f"   Text length: {len(text)} characters")
        
        if not voice:
            voice = getattr(self, 'ru_voice', 'ru_RU-irina-medium')
        
        try:
            # Test the FIXED POST endpoint
            start_time = time.time()
            
            response = self.session.post(
                f"{self.base_url}/audio/synthesize-with-progress",
                json={
                    "text": text,
                    "voice": voice,
                    "rate": 1.0,
                    "language": "ru-RU"
                },
                headers={'Content-Type': 'application/json'},
                timeout=600,  # 10 minutes for large audio
                stream=True  # For SSE
            )
            
            if response.status_code == 200:
                # Parse SSE events
                events = []
                final_result = None
                
                for line in response.iter_lines(decode_unicode=True):
                    if line.startswith('data: '):
                        try:
                            event_data = json.loads(line[6:])  # Remove 'data: ' prefix
                            events.append(event_data)
                            
                            if event_data.get('type') == 'complete':
                                final_result = event_data
                                break
                            elif event_data.get('type') == 'error':
                                raise Exception(f"SSE Error: {event_data.get('message')}")
                                
                        except json.JSONDecodeError:
                            continue
                
                synthesis_time = time.time() - start_time
                
                if final_result:
                    audio_id = final_result.get('audio_id')
                    duration = final_result.get('duration', 0)
                    
                    details = f"SUCCESS in {synthesis_time:.1f}s. Audio ID: {audio_id}, Duration: {duration:.1f}s, Events: {len(events)}"
                    
                    # Store for download test
                    if hasattr(self, 'audio_ids'):
                        self.audio_ids.append(audio_id)
                    else:
                        self.audio_ids = [audio_id]
                    
                    return self.log_result(f"{test_name} - POST Audio Synthesis", True, details)
                else:
                    return self.log_result(f"{test_name} - POST Audio Synthesis", False, f"No completion event after {synthesis_time:.1f}s")
            else:
                return self.log_result(f"{test_name} - POST Audio Synthesis", False, f"HTTP {response.status_code}: {response.text[:200]}")
                
        except Exception as e:
            return self.log_result(f"{test_name} - POST Audio Synthesis", False, f"Error: {str(e)}")

    def test_audio_synthesis_get_method_simulation(self, text, test_name):
        """Simulate what would happen with GET method (should fail for large texts)"""
        print(f"\n🔍 Simulating OLD GET method for {test_name}...")
        
        # Calculate what the URL would be
        voice = getattr(self, 'ru_voice', 'ru_RU-irina-medium')
        simulated_url = f"{self.base_url}/audio/synthesize-with-progress?text={text}&voice={voice}&rate=1.0&language=ru-RU"
        url_length = len(simulated_url)
        
        # Check if it would exceed typical URL limits
        browser_limit = 2048  # Conservative browser limit
        server_limit = 8192   # Typical server limit
        
        exceeds_browser = url_length > browser_limit
        exceeds_server = url_length > server_limit
        
        if exceeds_server:
            status = "WOULD FAIL (exceeds server limit)"
        elif exceeds_browser:
            status = "WOULD FAIL (exceeds browser limit)"
        else:
            status = "Would work"
        
        details = f"URL length: {url_length} chars. {status}. Browser limit: {browser_limit}, Server limit: {server_limit}"
        
        # This is expected to "fail" for large texts - that's why we needed the fix
        expected_failure = url_length > server_limit
        success = expected_failure if "Large" in test_name else not expected_failure
        
        return self.log_result(f"{test_name} - GET Method Simulation", success, details)

    def test_audio_download(self, audio_id):
        """Test downloading generated audio"""
        print(f"\n🔍 Testing audio download for {audio_id}...")
        
        try:
            response = self.session.get(f"{self.base_url}/audio/download/{audio_id}", timeout=30)
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                content_length = len(response.content)
                
                details = f"Downloaded {content_length} bytes, Content-Type: {content_type}"
                
                # Check if it's actually audio
                is_audio = 'audio' in content_type.lower() or content_length > 1000
                
                if is_audio:
                    return self.log_result("Audio Download", True, details)
                else:
                    return self.log_result("Audio Download", False, f"Not audio content: {details}")
            else:
                return self.log_result("Audio Download", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            return self.log_result("Audio Download", False, f"Error: {str(e)}")

    def test_manual_input_large_text(self):
        """Test manual input with large text (simulating user pasting large text)"""
        print("\n🔍 Testing manual input with large text...")
        
        # Create a large text manually (simulating user input)
        large_manual_text = """
        Искусственный интеллект представляет собой одну из самых значительных технологических революций нашего времени. Эта область компьютерной науки стремится создать машины, способные выполнять задачи, которые обычно требуют человеческого интеллекта. От простых алгоритмов до сложных нейронных сетей, ИИ охватывает широкий спектр технологий и методологий.
        
        История искусственного интеллекта началась в 1950-х годах, когда ученые впервые начали исследовать возможность создания мыслящих машин. Алан Тьюринг, один из пионеров в этой области, предложил знаменитый тест Тьюринга, который до сих пор используется как мера интеллекта машин. Тест предполагает, что машина может считаться интеллектуальной, если человек не может отличить ее ответы от ответов другого человека в процессе текстового общения.
        
        Машинное обучение стало ключевой областью ИИ, позволяющей компьютерам учиться и улучшать свою производительность без явного программирования каждого шага. Этот подход основан на анализе больших объемов данных и выявлении закономерностей, которые затем используются для принятия решений или предсказаний. Глубокое обучение, подраздел машинного обучения, использует искусственные нейронные сети с множественными слоями для моделирования и понимания сложных паттернов в данных.
        
        Применения искусственного интеллекта в современном мире поистине безграничны. В медицине ИИ помогает диагностировать заболевания, анализируя медицинские изображения с точностью, часто превышающей человеческую. В автомобильной промышленности автономные транспортные средства используют ИИ для навигации и принятия решений в реальном времени. В финансовой сфере алгоритмы ИИ обнаруживают мошеннические транзакции и управляют инвестиционными портфелями.
        
        Обработка естественного языка позволяет машинам понимать и генерировать человеческий язык, что открывает возможности для создания более интуитивных интерфейсов между человеком и компьютером. Системы распознавания речи, машинного перевода и генерации текста становятся все более совершенными, приближаясь к человеческому уровню понимания языка.
        
        Компьютерное зрение дает машинам способность "видеть" и интерпретировать визуальную информацию. Это технология лежит в основе многих современных приложений, от систем безопасности до медицинской диагностики. Алгоритмы компьютерного зрения могут распознавать объекты, лица, эмоции и даже предсказывать поведение на основе визуальных данных.
        
        Роботика интегрирует ИИ с физическими системами, создавая машины, способные взаимодействовать с реальным миром. Современные роботы используют ИИ для навигации, манипулирования объектами и выполнения сложных задач в различных средах, от заводских цехов до домашних хозяйств.
        
        Однако развитие ИИ также поднимает важные этические и социальные вопросы. Проблемы конфиденциальности данных, предвзятости алгоритмов, замещения рабочих мест и потенциального злоупотребления технологиями ИИ требуют серьезного внимания со стороны общества, правительств и технологических компаний.
        
        Будущее искусственного интеллекта обещает еще более революционные изменения. Исследователи работают над созданием общего искусственного интеллекта (AGI), который сможет выполнять любую интеллектуальную задачу, доступную человеку. Квантовые вычисления могут значительно ускорить обработку данных и обучение ИИ-систем.
        
        Важно отметить, что успешное развитие ИИ требует междисциплинарного подхода, объединяющего компьютерную науку, математику, психологию, философию и другие области знаний. Только через такое сотрудничество мы сможем создать ИИ-системы, которые будут не только мощными, но и безопасными, этичными и полезными для всего человечества.
        """ * 5  # Multiply to make it really large
        
        char_count = len(large_manual_text)
        
        # Test synthesis with this large manual text
        return self.test_audio_synthesis_post_method(large_manual_text, f"Manual Input Large Text ({char_count} chars)")

    def run_critical_tests(self):
        """Run the critical URL length fix tests"""
        print("🚀 CRITICAL URL LENGTH FIX TESTING")
        print("=" * 60)
        print("Testing the fix for large text audio synthesis issue")
        print("Problem: GET method URL length limit vs large text content")
        print("Solution: POST method with JSON body")
        print("=" * 60)
        
        all_passed = True
        
        # Step 1: Get voices
        if not self.test_voices_available():
            print("❌ Cannot proceed without voices")
            return False
        
        # Step 2: Generate large text (50 minutes)
        print("\n" + "="*50)
        print("STEP 1: GENERATE LARGE TEXT (50 MINUTES)")
        print("="*50)
        
        if not self.generate_large_text(50):
            print("❌ Cannot proceed without large text")
            return False
        
        # Step 3: Test URL length simulation (what would happen with GET)
        print("\n" + "="*50)
        print("STEP 2: SIMULATE OLD GET METHOD (SHOULD FAIL)")
        print("="*50)
        
        self.test_audio_synthesis_get_method_simulation(self.large_text, "Large Text")
        
        # Step 4: Test POST method with large text (THE CRITICAL FIX)
        print("\n" + "="*50)
        print("STEP 3: TEST NEW POST METHOD (SHOULD WORK)")
        print("="*50)
        
        large_synthesis_success = self.test_audio_synthesis_post_method(self.large_text, "Large Text (50 min)")
        if not large_synthesis_success:
            all_passed = False
        
        # Step 5: Regression test - short text
        print("\n" + "="*50)
        print("STEP 4: REGRESSION TEST - SHORT TEXT")
        print("="*50)
        
        if self.generate_short_text(2):
            self.test_audio_synthesis_get_method_simulation(self.short_text, "Short Text")
            short_synthesis_success = self.test_audio_synthesis_post_method(self.short_text, "Short Text (2 min)")
            if not short_synthesis_success:
                all_passed = False
        else:
            all_passed = False
        
        # Step 6: Manual input test
        print("\n" + "="*50)
        print("STEP 5: MANUAL INPUT LARGE TEXT TEST")
        print("="*50)
        
        manual_success = self.test_manual_input_large_text()
        if not manual_success:
            all_passed = False
        
        # Step 7: Test downloads
        print("\n" + "="*50)
        print("STEP 6: TEST AUDIO DOWNLOADS")
        print("="*50)
        
        if hasattr(self, 'audio_ids') and self.audio_ids:
            for audio_id in self.audio_ids[-2:]:  # Test last 2 audio files
                download_success = self.test_audio_download(audio_id)
                if not download_success:
                    all_passed = False
        
        # Final summary
        print("\n" + "="*60)
        print("🏁 CRITICAL TEST RESULTS SUMMARY")
        print("="*60)
        
        passed_tests = sum(1 for result in self.test_results if result['success'])
        total_tests = len(self.test_results)
        
        print(f"Tests passed: {passed_tests}/{total_tests}")
        print(f"Success rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Key findings
        print("\n🔍 KEY FINDINGS:")
        
        # Check if large text would fail with GET
        large_text_chars = getattr(self, 'large_text_chars', 0)
        if large_text_chars > 8000:
            print(f"✅ Large text ({large_text_chars} chars) WOULD FAIL with GET method (exceeds 8000 char limit)")
        
        # Check if POST method worked for large text
        large_post_success = any(r['success'] for r in self.test_results if 'Large Text (50 min)' in r['test_name'] and 'POST' in r['test_name'])
        if large_post_success:
            print("✅ POST method SUCCESSFULLY handles large text (FIX WORKING)")
        else:
            print("❌ POST method FAILED for large text (FIX NOT WORKING)")
        
        # Check regression
        short_post_success = any(r['success'] for r in self.test_results if 'Short Text (2 min)' in r['test_name'] and 'POST' in r['test_name'])
        if short_post_success:
            print("✅ Short text still works (NO REGRESSION)")
        else:
            print("❌ Short text broken (REGRESSION DETECTED)")
        
        if all_passed:
            print("\n🎉 ALL CRITICAL TESTS PASSED - URL LENGTH FIX IS WORKING!")
        else:
            print("\n⚠️  SOME TESTS FAILED - REVIEW NEEDED")
        
        return all_passed

def main():
    tester = URLLengthFixTester()
    success = tester.run_critical_tests()
    
    # Save results
    with open('/app/url_length_fix_test_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'overall_success': success,
            'test_results': tester.test_results
        }, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())