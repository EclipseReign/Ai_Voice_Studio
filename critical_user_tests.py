#!/usr/bin/env python3
"""
Critical User Issue Tests - Testing fixes for reported problems

CRITICAL TESTS (mandatory):
1. Text generation for 1 minute should produce ~150 words (not 275+ as reported)
2. Audio generation and duration check should be ~60 seconds (not 240+ as reported)  
3. Audio download should work properly

Based on user feedback in test_result.md
"""

import requests
import json
import time
import sys
from urllib.parse import quote
import httpx

class CriticalUserTests:
    def __init__(self, base_url="https://voice-session-repair.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.results = []
        
    def log_result(self, test_name, success, details):
        """Log test result"""
        result = {
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': time.time()
        }
        self.results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            for key, value in details.items():
                print(f"    {key}: {value}")
        print()
        
    def test_1_text_generation_1_minute(self):
        """
        ТЕСТ #1: Генерация текста на 1 минуту
        Expected: ~150 words (140-160 acceptable)
        Problem: Previously generated 275+ words (1531 words reported by user)
        """
        print("🔥 КРИТИЧЕСКИЙ ТЕСТ #1: Генерация текста на 1 минуту")
        print("Проверяем исправление проблемы с количеством слов...")
        
        # Use SSE endpoint as specified in review request
        url = f"{self.base_url}/text/generate-with-progress"
        params = {
            'prompt': 'История космоса',
            'duration_minutes': 1,
            'language': 'ru-RU'
        }
        
        try:
            start_time = time.time()
            generated_text = None
            text_id = None
            word_count = 0
            
            with httpx.stream("GET", url, params=params, timeout=120) as response:
                if response.status_code != 200:
                    self.log_result("ТЕСТ #1: SSE Connection", False, {
                        'error': f'HTTP {response.status_code}',
                        'url': url
                    })
                    return None, None
                
                print("📡 SSE соединение установлено...")
                
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            event_type = data.get('type')
                            
                            if event_type == 'complete':
                                generated_text = data.get('text', '')
                                text_id = data.get('text_id')
                                word_count = data.get('word_count', 0)
                                break
                            elif event_type == 'error':
                                raise Exception(data.get('message', 'Unknown error'))
                                
                        except json.JSONDecodeError:
                            continue
            
            generation_time = time.time() - start_time
            
            if not generated_text or not text_id:
                self.log_result("ТЕСТ #1: Генерация текста", False, {
                    'error': 'Не получен текст или text_id',
                    'time': f'{generation_time:.1f}s'
                })
                return None, None
            
            # Check word count - CRITICAL CHECK
            target_words = 150
            acceptable_min = 140
            acceptable_max = 160
            word_count_ok = acceptable_min <= word_count <= acceptable_max
            
            # Check if it's the old problem (275+ words)
            old_problem = word_count >= 275
            
            details = {
                'word_count': word_count,
                'target': f'{target_words} слов',
                'acceptable_range': f'{acceptable_min}-{acceptable_max} слов',
                'generation_time': f'{generation_time:.1f}s',
                'text_id': text_id,
                'text_preview': generated_text[:100] + '...' if len(generated_text) > 100 else generated_text
            }
            
            if old_problem:
                details['CRITICAL_ERROR'] = f'Старая проблема НЕ исправлена! {word_count} слов >= 275'
            
            success = word_count_ok and not old_problem
            
            self.log_result("ТЕСТ #1: Генерация текста на 1 минуту", success, details)
            
            return generated_text, text_id
            
        except Exception as e:
            self.log_result("ТЕСТ #1: Генерация текста", False, {
                'error': str(e),
                'url': url
            })
            return None, None
    
    def test_2_audio_generation_and_duration(self, text, expected_duration_sec=60):
        """
        ТЕСТ #2: Генерация аудио и проверка длительности
        Expected: ~60 seconds for 1-minute text
        Problem: Previously generated 240+ seconds (4 minutes) as reported by user
        """
        if not text:
            self.log_result("ТЕСТ #2: Генерация аудио", False, {
                'error': 'Нет текста из предыдущего теста'
            })
            return None
            
        print("🔥 КРИТИЧЕСКИЙ ТЕСТ #2: Генерация аудио и проверка длительности")
        print("Проверяем исправление проблемы с длительностью аудио...")
        
        url = f"{self.base_url}/audio/synthesize-with-progress"
        params = {
            'text': text,
            'voice': 'ru_RU-irina-medium',
            'rate': 1.0,
            'language': 'ru-RU'
        }
        
        try:
            start_time = time.time()
            audio_id = None
            audio_duration = None
            progress_reached_100 = False
            
            with httpx.stream("GET", url, params=params, timeout=300) as response:
                if response.status_code != 200:
                    self.log_result("ТЕСТ #2: SSE Audio Connection", False, {
                        'error': f'HTTP {response.status_code}',
                        'url': url
                    })
                    return None
                
                print("📡 SSE аудио соединение установлено...")
                
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            event_type = data.get('type')
                            progress = data.get('progress', 0)
                            
                            if event_type == 'progress' and progress == 100:
                                progress_reached_100 = True
                            elif event_type == 'complete':
                                audio_id = data.get('audio_id')
                                audio_duration = data.get('duration', 0)
                                if progress == 100:
                                    progress_reached_100 = True
                                break
                            elif event_type == 'error':
                                raise Exception(data.get('message', 'Unknown error'))
                                
                        except json.JSONDecodeError:
                            continue
            
            synthesis_time = time.time() - start_time
            
            if not audio_id:
                self.log_result("ТЕСТ #2: Генерация аудио", False, {
                    'error': 'Не получен audio_id',
                    'synthesis_time': f'{synthesis_time:.1f}s'
                })
                return None
            
            # Check audio duration - CRITICAL CHECK
            acceptable_min = 50  # seconds
            acceptable_max = 70  # seconds
            duration_ok = acceptable_min <= audio_duration <= acceptable_max if audio_duration else False
            
            # Check if it's the old problem (240+ seconds = 4+ minutes)
            old_problem = audio_duration >= 240 if audio_duration else False
            
            details = {
                'audio_id': audio_id,
                'audio_duration': f'{audio_duration:.1f}s' if audio_duration else 'Unknown',
                'target_duration': f'{expected_duration_sec}s',
                'acceptable_range': f'{acceptable_min}-{acceptable_max}s',
                'synthesis_time': f'{synthesis_time:.1f}s',
                'progress_reached_100': progress_reached_100,
                'duration_valid': audio_duration > 0 if audio_duration else False
            }
            
            if old_problem:
                details['CRITICAL_ERROR'] = f'Старая проблема НЕ исправлена! {audio_duration:.1f}s >= 240s'
            
            success = (
                audio_duration is not None and 
                audio_duration > 0 and 
                duration_ok and 
                not old_problem and 
                progress_reached_100
            )
            
            self.log_result("ТЕСТ #2: Генерация аудио и длительность", success, details)
            
            return audio_id
            
        except Exception as e:
            self.log_result("ТЕСТ #2: Генерация аудио", False, {
                'error': str(e),
                'url': url
            })
            return None
    
    def test_3_audio_download(self, audio_id):
        """
        ТЕСТ #3: Скачивание аудио
        Expected: Status 200, Content-Type audio/wav, file size > 0
        """
        if not audio_id:
            self.log_result("ТЕСТ #3: Скачивание аудио", False, {
                'error': 'Нет audio_id из предыдущего теста'
            })
            return False
            
        print("🔥 КРИТИЧЕСКИЙ ТЕСТ #3: Скачивание аудио")
        print("Проверяем что аудио файл корректно скачивается...")
        
        url = f"{self.base_url}/audio/download/{audio_id}"
        
        try:
            response = requests.get(url, timeout=30)
            
            status_ok = response.status_code == 200
            content_type = response.headers.get('Content-Type', '')
            content_type_ok = 'audio/wav' in content_type
            file_size = len(response.content)
            file_size_ok = file_size > 0
            
            details = {
                'audio_id': audio_id,
                'status_code': response.status_code,
                'content_type': content_type,
                'file_size': f'{file_size:,} bytes',
                'url': url,
                'status_ok': status_ok,
                'content_type_ok': content_type_ok,
                'file_size_ok': file_size_ok
            }
            
            success = status_ok and content_type_ok and file_size_ok
            
            self.log_result("ТЕСТ #3: Скачивание аудио", success, details)
            
            return success
            
        except Exception as e:
            self.log_result("ТЕСТ #3: Скачивание аудио", False, {
                'error': str(e),
                'url': url
            })
            return False
    
    def test_additional_durations(self):
        """
        ДОПОЛНИТЕЛЬНЫЕ ТЕСТЫ: 2 минуты и 5 минут
        """
        print("🔍 ДОПОЛНИТЕЛЬНЫЕ ТЕСТЫ: Проверка других длительностей")
        
        test_cases = [
            (2, 300, "2 минуты"),  # 2 min = ~300 words = ~120 sec audio
            (5, 750, "5 минут")    # 5 min = ~750 words = ~300 sec audio
        ]
        
        for duration_min, expected_words, test_name in test_cases:
            print(f"\n📋 Тест {test_name}:")
            
            # Generate text
            url = f"{self.base_url}/text/generate-with-progress"
            params = {
                'prompt': f'История космоса и исследований ({test_name})',
                'duration_minutes': duration_min,
                'language': 'ru-RU'
            }
            
            try:
                generated_text = None
                word_count = 0
                
                with httpx.stream("GET", url, params=params, timeout=180) as response:
                    if response.status_code != 200:
                        print(f"   ❌ SSE ошибка: HTTP {response.status_code}")
                        continue
                    
                    for line in response.iter_lines():
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                if data.get('type') == 'complete':
                                    generated_text = data.get('text', '')
                                    word_count = data.get('word_count', 0)
                                    break
                            except json.JSONDecodeError:
                                continue
                
                if generated_text:
                    accuracy = (word_count / expected_words) * 100 if expected_words > 0 else 0
                    expected_audio_sec = duration_min * 60
                    
                    print(f"   📝 Слова: {word_count} (ожидалось ~{expected_words}, точность: {accuracy:.1f}%)")
                    
                    # Quick audio test
                    audio_url = f"{self.base_url}/audio/synthesize-with-progress"
                    audio_params = {
                        'text': generated_text[:500],  # Test with first 500 chars for speed
                        'voice': 'ru_RU-irina-medium',
                        'rate': 1.0,
                        'language': 'ru-RU'
                    }
                    
                    try:
                        with httpx.stream("GET", audio_url, params=audio_params, timeout=120) as audio_response:
                            if audio_response.status_code == 200:
                                for line in audio_response.iter_lines():
                                    if line.startswith("data: "):
                                        try:
                                            data = json.loads(line[6:])
                                            if data.get('type') == 'complete':
                                                duration = data.get('duration', 0)
                                                print(f"   🔊 Аудио (первые 500 символов): {duration:.1f}s")
                                                break
                                        except json.JSONDecodeError:
                                            continue
                    except Exception as e:
                        print(f"   ⚠️  Аудио тест не удался: {str(e)}")
                        
                else:
                    print(f"   ❌ Генерация текста не удалась")
                    
            except Exception as e:
                print(f"   ❌ Ошибка: {str(e)}")
    
    def run_critical_tests(self):
        """Run all critical tests in sequence"""
        print("🚀 КРИТИЧЕСКИЕ ТЕСТЫ ПО ОТЗЫВУ ПОЛЬЗОВАТЕЛЯ")
        print("=" * 60)
        print("Проблемы пользователя:")
        print("1. ❌ Для 1 минуты генерируется 1531 слово вместо 150")
        print("2. ❌ Аудио длится 4 минуты вместо 1 минуты") 
        print("3. ❌ Не может скачать аудио файл")
        print("=" * 60)
        
        # Test 1: Text generation for 1 minute
        generated_text, text_id = self.test_1_text_generation_1_minute()
        
        # Test 2: Audio generation and duration check
        audio_id = self.test_2_audio_generation_and_duration(generated_text)
        
        # Test 3: Audio download
        download_success = self.test_3_audio_download(audio_id)
        
        # Additional tests if time permits
        if generated_text and audio_id and download_success:
            print("\n" + "=" * 60)
            self.test_additional_durations()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 ИТОГОВЫЙ ОТЧЁТ")
        print("=" * 60)
        
        passed_tests = sum(1 for r in self.results if r['success'])
        total_tests = len(self.results)
        
        print(f"Пройдено тестов: {passed_tests}/{total_tests}")
        
        # Check if critical issues are resolved
        critical_results = self.results[:3]  # First 3 tests are critical
        all_critical_passed = all(r['success'] for r in critical_results)
        
        if all_critical_passed:
            print("✅ ВСЕ КРИТИЧЕСКИЕ ПРОБЛЕМЫ ИСПРАВЛЕНЫ!")
            print("✅ Генерация текста: правильное количество слов")
            print("✅ Генерация аудио: правильная длительность")
            print("✅ Скачивание аудио: работает корректно")
        else:
            print("❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ НЕ ПОЛНОСТЬЮ ИСПРАВЛЕНЫ:")
            for i, result in enumerate(critical_results, 1):
                status = "✅" if result['success'] else "❌"
                print(f"{status} Тест #{i}: {result['test']}")
        
        # Detailed results for each test
        print("\nДетальные результаты:")
        for i, result in enumerate(self.results, 1):
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"{i}. {status} {result['test']}")
            if not result['success'] and 'error' in result['details']:
                print(f"   Ошибка: {result['details']['error']}")
        
        return all_critical_passed

def main():
    """Main test execution"""
    tester = CriticalUserTests()
    success = tester.run_critical_tests()
    
    # Save results
    with open('/app/critical_test_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': time.time(),
            'success': success,
            'results': tester.results
        }, f, indent=2, ensure_ascii=False)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())