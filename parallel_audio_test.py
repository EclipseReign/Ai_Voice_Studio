#!/usr/bin/env python3
"""
Focused test for parallel audio generation optimization
Tests the new POST /api/audio/synthesize-parallel endpoint
"""

import requests
import time
import json
from pathlib import Path

class ParallelAudioTester:
    def __init__(self):
        self.base_url = "https://voice-scaling.preview.emergentagent.com/api"
        self.results = []
        
    def test_api_connection(self):
        """Test basic API connectivity"""
        print("🔍 Testing API connection...")
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 200:
                print("✅ API connection successful")
                return True
            else:
                print(f"❌ API returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ API connection failed: {e}")
            return False
    
    def get_russian_voice(self):
        """Get a Russian voice for testing"""
        print("🔍 Getting Russian voice...")
        try:
            response = requests.get(f"{self.base_url}/voices", timeout=30)
            if response.status_code == 200:
                voices = response.json()
                print(f"✅ Found {len(voices)} voices")
                
                # Look for Russian voice
                for voice in voices:
                    if voice.get('locale', '').startswith('ru-'):
                        print(f"✅ Using Russian voice: {voice['name']} ({voice['short_name']})")
                        return voice['short_name']
                
                print("❌ No Russian voice found")
                return None
            else:
                print(f"❌ Failed to get voices: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error getting voices: {e}")
            return None
    
    def test_parallel_short_text(self, voice):
        """Test 1: Short Russian text (2-3 sentences)"""
        print("\n🔥 TEST 1: Parallel Audio - Short Russian Text")
        
        text = "Искусственный интеллект изменяет мир. Он помогает людям решать сложные задачи. Будущее уже здесь."
        print(f"   Text: {text}")
        print(f"   Length: {len(text)} characters")
        
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.base_url}/audio/synthesize-parallel",
                json={
                    "text": text,
                    "voice": voice,
                    "rate": 1.0,
                    "language": "ru-RU"
                },
                timeout=60
            )
            
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS in {duration:.2f} seconds")
                print(f"   Audio ID: {data.get('id')}")
                print(f"   Audio URL: {data.get('audio_url')}")
                
                result = {
                    'test': 'parallel_short_text',
                    'success': True,
                    'duration': duration,
                    'audio_id': data.get('id'),
                    'text_length': len(text)
                }
                self.results.append(result)
                return result
            else:
                print(f"❌ FAILED: Status {response.status_code}")
                print(f"   Error: {response.text}")
                result = {
                    'test': 'parallel_short_text',
                    'success': False,
                    'error': f"Status {response.status_code}: {response.text}"
                }
                self.results.append(result)
                return result
                
        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ FAILED after {duration:.2f}s: {e}")
            result = {
                'test': 'parallel_short_text',
                'success': False,
                'error': str(e)
            }
            self.results.append(result)
            return result
    
    def generate_medium_text(self):
        """Generate medium text for testing"""
        print("\n🔍 Generating medium text (~1000 chars)...")
        
        try:
            response = requests.post(
                f"{self.base_url}/text/generate",
                json={
                    "prompt": "История развития компьютерных технологий",
                    "duration_minutes": 2,
                    "language": "ru-RU"
                },
                timeout=90
            )
            
            if response.status_code == 200:
                data = response.json()
                text = data.get('text', '')
                
                # Truncate to ~1000 characters if too long
                if len(text) > 1200:
                    text = text[:1000] + "."
                
                print(f"✅ Generated text: {len(text)} characters")
                return text
            else:
                print(f"❌ Text generation failed: {response.status_code}")
                # Fallback text
                return """
                Компьютерные технологии прошли невероятный путь развития за последние десятилетия. От огромных машин, занимавших целые комнаты, до миниатюрных устройств, помещающихся в кармане, прогресс был поразительным. Первые компьютеры использовались исключительно для научных расчетов и военных целей. Сегодня они стали неотъемлемой частью нашей повседневной жизни. Интернет революционизировал способы общения и обмена информацией. Социальные сети объединили людей по всему миру. Мобильные технологии сделали доступ к информации мгновенным. Искусственный интеллект открывает новые горизонты возможностей.
                """
        except Exception as e:
            print(f"❌ Error generating text: {e}")
            # Fallback text
            return """
            Компьютерные технологии прошли невероятный путь развития за последние десятилетия. От огромных машин, занимавших целые комнаты, до миниатюрных устройств, помещающихся в кармане, прогресс был поразительным. Первые компьютеры использовались исключительно для научных расчетов и военных целей. Сегодня они стали неотъемлемой частью нашей повседневной жизни. Интернет революционизировал способы общения и обмена информацией. Социальные сети объединили людей по всему миру. Мобильные технологии сделали доступ к информации мгновенным. Искусственный интеллект открывает новые горизонты возможностей.
            """
    
    def test_parallel_medium_text(self, voice):
        """Test 2: Medium text (~1000 characters, 5-7 segments)"""
        print("\n🔥 TEST 2: Parallel Audio - Medium Text (~1000 chars)")
        
        text = self.generate_medium_text().strip()
        print(f"   Text length: {len(text)} characters")
        print(f"   Text preview: {text[:100]}...")
        
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.base_url}/audio/synthesize-parallel",
                json={
                    "text": text,
                    "voice": voice,
                    "rate": 1.0,
                    "language": "ru-RU"
                },
                timeout=120
            )
            
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS in {duration:.2f} seconds")
                print(f"   Audio ID: {data.get('id')}")
                print(f"   Audio URL: {data.get('audio_url')}")
                
                result = {
                    'test': 'parallel_medium_text',
                    'success': True,
                    'duration': duration,
                    'audio_id': data.get('id'),
                    'text_length': len(text)
                }
                self.results.append(result)
                return result
            else:
                print(f"❌ FAILED: Status {response.status_code}")
                print(f"   Error: {response.text}")
                result = {
                    'test': 'parallel_medium_text',
                    'success': False,
                    'error': f"Status {response.status_code}: {response.text}"
                }
                self.results.append(result)
                return result
                
        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ FAILED after {duration:.2f}s: {e}")
            result = {
                'test': 'parallel_medium_text',
                'success': False,
                'error': str(e)
            }
            self.results.append(result)
            return result
    
    def test_speed_comparison(self, voice):
        """Test 3: Speed comparison between parallel and regular synthesis"""
        print("\n🔥 TEST 3: Speed Comparison - Parallel vs Regular")
        
        # Test text with multiple sentences (good for parallel processing)
        text = """
        Технологии искусственного интеллекта развиваются с невероятной скоростью. Машинное обучение позволяет компьютерам анализировать огромные объемы данных. Нейронные сети моделируют работу человеческого мозга. Глубокое обучение открывает новые возможности в распознавании образов. Обработка естественного языка помогает машинам понимать человеческую речь. Компьютерное зрение позволяет анализировать изображения и видео.
        """
        
        print(f"   Test text: {len(text)} characters")
        
        # Test regular synthesis
        print("\n   Testing REGULAR synthesis...")
        regular_start = time.time()
        
        try:
            regular_response = requests.post(
                f"{self.base_url}/audio/synthesize",
                json={
                    "text": text,
                    "voice": voice,
                    "rate": 1.0,
                    "language": "ru-RU"
                },
                timeout=120
            )
            regular_time = time.time() - regular_start
            regular_success = regular_response.status_code == 200
            
            if regular_success:
                print(f"   ✅ Regular synthesis: {regular_time:.2f} seconds")
            else:
                print(f"   ❌ Regular synthesis failed: {regular_response.status_code}")
                
        except Exception as e:
            regular_time = time.time() - regular_start
            regular_success = False
            print(f"   ❌ Regular synthesis error: {e}")
        
        # Test parallel synthesis
        print("\n   Testing PARALLEL synthesis...")
        parallel_start = time.time()
        
        try:
            parallel_response = requests.post(
                f"{self.base_url}/audio/synthesize-parallel",
                json={
                    "text": text,
                    "voice": voice,
                    "rate": 1.0,
                    "language": "ru-RU"
                },
                timeout=120
            )
            parallel_time = time.time() - parallel_start
            parallel_success = parallel_response.status_code == 200
            
            if parallel_success:
                print(f"   ✅ Parallel synthesis: {parallel_time:.2f} seconds")
            else:
                print(f"   ❌ Parallel synthesis failed: {parallel_response.status_code}")
                
        except Exception as e:
            parallel_time = time.time() - parallel_start
            parallel_success = False
            print(f"   ❌ Parallel synthesis error: {e}")
        
        # Compare results
        if regular_success and parallel_success:
            speedup = regular_time / parallel_time if parallel_time > 0 else 0
            print(f"\n   📊 SPEED COMPARISON RESULTS:")
            print(f"   Regular:  {regular_time:.2f}s")
            print(f"   Parallel: {parallel_time:.2f}s")
            print(f"   Speedup:  {speedup:.2f}x")
            
            if speedup > 1.5:
                print(f"   ✅ Parallel is {speedup:.1f}x faster - EXCELLENT!")
            elif speedup > 1.0:
                print(f"   ⚠️  Parallel is {speedup:.1f}x faster - MODERATE")
            else:
                print(f"   ❌ Parallel is SLOWER than regular!")
            
            result = {
                'test': 'speed_comparison',
                'success': True,
                'regular_time': regular_time,
                'parallel_time': parallel_time,
                'speedup': speedup
            }
        else:
            print(f"   ❌ Speed comparison failed")
            result = {
                'test': 'speed_comparison',
                'success': False,
                'regular_success': regular_success,
                'parallel_success': parallel_success
            }
        
        self.results.append(result)
        return result
    
    def test_audio_download(self, audio_id):
        """Test audio download"""
        if not audio_id:
            return False
            
        print(f"\n🔍 Testing audio download for {audio_id[:8]}...")
        
        try:
            response = requests.get(f"{self.base_url}/audio/download/{audio_id}", timeout=30)
            if response.status_code == 200:
                print(f"   ✅ Download successful: {len(response.content)} bytes")
                return True
            else:
                print(f"   ❌ Download failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Download error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all parallel audio generation tests"""
        print("🚀 PARALLEL AUDIO GENERATION OPTIMIZATION TESTS")
        print("=" * 60)
        
        # Test API connection
        if not self.test_api_connection():
            print("❌ Cannot connect to API - stopping tests")
            return False
        
        # Get Russian voice
        voice = self.get_russian_voice()
        if not voice:
            print("❌ Cannot get Russian voice - stopping tests")
            return False
        
        # Run tests
        test1_result = self.test_parallel_short_text(voice)
        test2_result = self.test_parallel_medium_text(voice)
        test3_result = self.test_speed_comparison(voice)
        
        # Test downloads
        download_count = 0
        for result in self.results:
            if result.get('success') and result.get('audio_id'):
                if self.test_audio_download(result['audio_id']):
                    download_count += 1
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 PARALLEL AUDIO OPTIMIZATION TEST RESULTS")
        print("=" * 60)
        
        successful_tests = sum(1 for r in self.results if r.get('success'))
        total_tests = len(self.results)
        
        print(f"Tests passed: {successful_tests}/{total_tests}")
        print(f"Downloads tested: {download_count}")
        
        for result in self.results:
            test_name = result['test']
            if result.get('success'):
                if test_name == 'speed_comparison':
                    speedup = result.get('speedup', 0)
                    print(f"✅ {test_name}: {speedup:.2f}x speedup")
                else:
                    duration = result.get('duration', 0)
                    print(f"✅ {test_name}: {duration:.2f}s")
            else:
                error = result.get('error', 'Unknown error')
                print(f"❌ {test_name}: {error}")
        
        # Critical assessment
        print("\n🔥 CRITICAL QUALITY ASSESSMENT:")
        
        if test1_result and test1_result.get('success'):
            print("✅ Short text parallel synthesis: WORKING")
        else:
            print("❌ Short text parallel synthesis: FAILED")
        
        if test2_result and test2_result.get('success'):
            print("✅ Medium text parallel synthesis: WORKING")
        else:
            print("❌ Medium text parallel synthesis: FAILED")
        
        if test3_result and test3_result.get('success'):
            speedup = test3_result.get('speedup', 0)
            if speedup > 1.5:
                print(f"✅ Speed optimization: EXCELLENT ({speedup:.1f}x faster)")
            elif speedup > 1.0:
                print(f"⚠️  Speed optimization: MODERATE ({speedup:.1f}x faster)")
            else:
                print(f"❌ Speed optimization: FAILED (slower than regular)")
        else:
            print("❌ Speed comparison: FAILED")
        
        # Save results
        with open('/app/parallel_audio_test_results.json', 'w') as f:
            json.dump({
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'results': self.results,
                'summary': {
                    'total_tests': total_tests,
                    'successful_tests': successful_tests,
                    'downloads_tested': download_count
                }
            }, f, indent=2)
        
        return successful_tests == total_tests

def main():
    tester = ParallelAudioTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())