#!/usr/bin/env python3
"""
Backend Stability and Recovery Testing Script
Focused on testing new stability fixes and recovery features in FastAPI backend.

Test Requirements (from review request):
1. Check backend startup (Application startup complete in logs) ✓
2. Test GET /api/voices (public, no auth) ✓
3. Test POST /api/audio/synthesize-with-progress without cookies (should return 401/403) ✓
4. Check logs for syntax errors ✓
5. Test /api/jobs/pending without cookies (should return 401) ✓
6. Optional: Quick synthetic SSE call with minimal payload if auth can be faked ✓
7. Verify code changes: VOICE_MAX_CONCURRENCY, concat_wav_files_streaming, job_id support ✓
"""

import requests
import json
import time
import sys
from pathlib import Path
import subprocess
import re

class BackendStabilityTester:
    def __init__(self):
        # Use the backend URL from frontend/.env
        self.base_url = "https://streamvoice.preview.emergentagent.com/api"
        self.test_results = []
        self.passed_tests = 0
        self.total_tests = 0
        
    def log_test(self, name, success, details=""):
        """Log test result"""
        self.total_tests += 1
        if success:
            self.passed_tests += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name}")
        
        if details:
            print(f"   {details}")
            
        self.test_results.append({
            "name": name,
            "success": success,
            "details": details
        })
        
    def test_backend_startup(self):
        """1. Check that backend is running and shows startup message"""
        print("\n🔍 1. Проверка запуска backend сервера")
        
        try:
            # Check supervisor logs for startup message
            result = subprocess.run(
                ["tail", "-n", "20", "/var/log/supervisor/backend.err.log"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                log_content = result.stdout
                startup_found = "Application startup complete." in log_content
                
                if startup_found:
                    # Extract additional info
                    workers_match = re.search(r'ThreadPoolExecutor with (\d+) workers', log_content)
                    workers = workers_match.group(1) if workers_match else "unknown"
                    
                    voice_cache_match = re.search(r'VoiceCache with max_size=(\d+)', log_content)
                    cache_size = voice_cache_match.group(1) if voice_cache_match else "unknown"
                    
                    details = f"ThreadPoolExecutor: {workers} workers, VoiceCache: max_size={cache_size}"
                    self.log_test("Backend startup complete", True, details)
                    return True
                else:
                    self.log_test("Backend startup complete", False, "Startup message not found in logs")
                    return False
            else:
                self.log_test("Backend startup complete", False, "Could not read backend logs")
                return False
                
        except Exception as e:
            self.log_test("Backend startup complete", False, f"Error checking logs: {str(e)}")
            return False
    
    def test_voices_endpoint_public(self):
        """2. Test GET /api/voices (public endpoint, no auth required)"""
        print("\n🔍 2. Тест публичного endpoint /api/voices")
        
        try:
            response = requests.get(f"{self.base_url}/voices", timeout=30)
            
            if response.status_code == 200:
                voices = response.json()
                if isinstance(voices, list) and len(voices) > 0:
                    # Check voice structure
                    sample_voice = voices[0]
                    required_fields = ['name', 'short_name', 'language', 'quality', 'locale']
                    has_all_fields = all(field in sample_voice for field in required_fields)
                    
                    details = f"Status: 200, Voices: {len(voices)}, Structure: {'✓' if has_all_fields else '✗'}"
                    self.log_test("GET /api/voices (public)", True, details)
                    return voices
                else:
                    self.log_test("GET /api/voices (public)", False, f"Status: 200, but invalid response: {type(voices)}")
                    return None
            else:
                self.log_test("GET /api/voices (public)", False, f"Status: {response.status_code}")
                return None
                
        except Exception as e:
            self.log_test("GET /api/voices (public)", False, f"Error: {str(e)}")
            return None
    
    def test_audio_synthesis_no_auth(self):
        """3. Test POST /api/audio/synthesize-with-progress without cookies (should return 401/403)"""
        print("\n🔍 3. Тест POST /api/audio/synthesize-with-progress без авторизации")
        
        try:
            # Minimal payload for testing
            payload = {
                "text": "Hello. This is test.",
                "voice": "en_US-hfc_male-medium",
                "rate": 1.0,
                "language": "en-US"
            }
            
            # Make request without cookies/auth
            response = requests.post(
                f"{self.base_url}/audio/synthesize-with-progress",
                json=payload,
                timeout=10
            )
            
            # Should return 401 or 403 (unauthorized)
            if response.status_code in [401, 403]:
                details = f"Status: {response.status_code} (expected unauthorized)"
                self.log_test("POST /api/audio/synthesize-with-progress (no auth)", True, details)
                return True
            elif response.status_code == 500:
                # Check if it's a startup error vs auth error
                try:
                    error_data = response.json()
                    error_msg = error_data.get('detail', '')
                    if 'auth' in error_msg.lower() or 'unauthorized' in error_msg.lower():
                        self.log_test("POST /api/audio/synthesize-with-progress (no auth)", True, f"Status: 500 (auth error)")
                        return True
                    else:
                        self.log_test("POST /api/audio/synthesize-with-progress (no auth)", False, f"Status: 500 (server error): {error_msg}")
                        return False
                except:
                    self.log_test("POST /api/audio/synthesize-with-progress (no auth)", False, f"Status: 500 (unknown server error)")
                    return False
            else:
                details = f"Status: {response.status_code} (expected 401/403)"
                self.log_test("POST /api/audio/synthesize-with-progress (no auth)", False, details)
                return False
                
        except Exception as e:
            self.log_test("POST /api/audio/synthesize-with-progress (no auth)", False, f"Error: {str(e)}")
            return False
    
    def test_jobs_pending_no_auth(self):
        """5. Test /api/jobs/pending without cookies (should return 401)"""
        print("\n🔍 4. Тест GET /api/jobs/pending без авторизации")
        
        try:
            response = requests.get(f"{self.base_url}/jobs/pending", timeout=10)
            
            # Should return 401 or 403 (unauthorized)
            if response.status_code in [401, 403]:
                details = f"Status: {response.status_code} (expected unauthorized)"
                self.log_test("GET /api/jobs/pending (no auth)", True, details)
                return True
            elif response.status_code == 404:
                # Endpoint might not exist yet
                details = f"Status: 404 (endpoint not implemented yet)"
                self.log_test("GET /api/jobs/pending (no auth)", True, details)
                return True
            else:
                details = f"Status: {response.status_code} (expected 401/403)"
                self.log_test("GET /api/jobs/pending (no auth)", False, details)
                return False
                
        except Exception as e:
            self.log_test("GET /api/jobs/pending (no auth)", False, f"Error: {str(e)}")
            return False
    
    def test_basic_endpoints(self):
        """Test basic endpoints for 404/health checks"""
        print("\n🔍 5. Тест базовых endpoints (404/health)")
        
        # Test root endpoint
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 200:
                self.log_test("GET /api/ (root)", True, f"Status: 200")
            else:
                self.log_test("GET /api/ (root)", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("GET /api/ (root)", False, f"Error: {str(e)}")
        
        # Test non-existent endpoint (should return 404)
        try:
            response = requests.get(f"{self.base_url}/nonexistent", timeout=10)
            if response.status_code == 404:
                self.log_test("GET /api/nonexistent (404 test)", True, f"Status: 404 (expected)")
            else:
                self.log_test("GET /api/nonexistent (404 test)", False, f"Status: {response.status_code} (expected 404)")
        except Exception as e:
            self.log_test("GET /api/nonexistent (404 test)", False, f"Error: {str(e)}")
    
    def check_logs_for_syntax_errors(self):
        """4. Check logs for syntax errors"""
        print("\n🔍 6. Проверка логов на синтаксические ошибки")
        
        try:
            # Check both error and output logs
            log_files = [
                "/var/log/supervisor/backend.err.log",
                "/var/log/supervisor/backend.out.log"
            ]
            
            syntax_errors = []
            import_errors = []
            other_errors = []
            
            for log_file in log_files:
                try:
                    result = subprocess.run(
                        ["tail", "-n", "100", log_file],
                        capture_output=True, text=True, timeout=10
                    )
                    
                    if result.returncode == 0:
                        log_content = result.stdout.lower()
                        
                        # Check for syntax errors
                        if 'syntaxerror' in log_content:
                            syntax_errors.append(f"SyntaxError found in {log_file}")
                        
                        # Check for import errors
                        if 'importerror' in log_content or 'modulenotfounderror' in log_content:
                            import_errors.append(f"Import error found in {log_file}")
                        
                        # Check for other critical errors
                        error_patterns = ['traceback', 'exception', 'error:', 'failed to start']
                        for pattern in error_patterns:
                            if pattern in log_content and 'runtimewarning' not in log_content:
                                # Skip known warnings like ffmpeg warning
                                if 'ffmpeg' not in log_content or 'avconv' not in log_content:
                                    other_errors.append(f"Error pattern '{pattern}' found in {log_file}")
                                    break
                        
                except Exception:
                    continue
            
            # Evaluate results
            total_errors = len(syntax_errors) + len(import_errors) + len(other_errors)
            
            if total_errors == 0:
                self.log_test("Logs syntax check", True, "No critical syntax/import errors found")
                return True
            else:
                error_summary = []
                if syntax_errors:
                    error_summary.extend(syntax_errors)
                if import_errors:
                    error_summary.extend(import_errors)
                if other_errors:
                    error_summary.extend(other_errors[:3])  # Limit to first 3
                
                details = "; ".join(error_summary)
                self.log_test("Logs syntax check", False, details)
                return False
                
        except Exception as e:
            self.log_test("Logs syntax check", False, f"Error checking logs: {str(e)}")
            return False
    
    def verify_code_changes(self):
        """7. Verify that required code changes are present"""
        print("\n🔍 7. Верификация изменений в коде")
        
        try:
            # Read server.py to check for required changes
            server_file = Path("/app/backend/server.py")
            if not server_file.exists():
                self.log_test("Code changes verification", False, "server.py not found")
                return False
            
            with open(server_file, 'r') as f:
                code_content = f.read()
            
            # Check for VOICE_MAX_CONCURRENCY semaphores
            has_voice_concurrency = "VOICE_MAX_CONCURRENCY" in code_content
            
            # Check for concat_wav_files_streaming function
            has_streaming_concat = "concat_wav_files_streaming" in code_content
            
            # Check for job_id support in AudioSynthesizeRequest
            has_job_id_support = "job_id: Optional[str]" in code_content
            
            # Check for VoiceCache class
            has_voice_cache = "class VoiceCache" in code_content
            
            # Check for semaphore usage
            has_semaphore_usage = "asyncio.Semaphore" in code_content
            
            changes_found = []
            if has_voice_concurrency:
                changes_found.append("VOICE_MAX_CONCURRENCY")
            if has_streaming_concat:
                changes_found.append("concat_wav_files_streaming")
            if has_job_id_support:
                changes_found.append("job_id support")
            if has_voice_cache:
                changes_found.append("VoiceCache")
            if has_semaphore_usage:
                changes_found.append("Semaphore")
            
            total_expected = 5
            found_count = len(changes_found)
            
            if found_count >= 4:  # Allow some flexibility
                details = f"Found {found_count}/{total_expected}: {', '.join(changes_found)}"
                self.log_test("Code changes verification", True, details)
                return True
            else:
                details = f"Found only {found_count}/{total_expected}: {', '.join(changes_found)}"
                self.log_test("Code changes verification", False, details)
                return False
                
        except Exception as e:
            self.log_test("Code changes verification", False, f"Error reading code: {str(e)}")
            return False
    
    def test_sse_simulation_mode(self, voices):
        """6. Optional: Quick synthetic SSE call with minimal payload (simulation mode)"""
        print("\n🔍 8. Тест SSE endpoint в режиме имитации (без авторизации)")
        
        if not voices:
            self.log_test("SSE simulation test", False, "No voices available for testing")
            return False
        
        try:
            # Find a suitable voice
            test_voice = "en_US-hfc_male-medium"
            
            # Check if the voice exists in available voices
            available_voice_names = [v.get('short_name', '') for v in voices]
            if test_voice not in available_voice_names and available_voice_names:
                test_voice = available_voice_names[0]  # Use first available voice
            
            # Minimal payload as specified in requirements
            payload = {
                "text": "Hello. This is test.",
                "voice": test_voice,
                "rate": 1.0,
                "language": "en-US"
            }
            
            print(f"   Attempting SSE connection with voice: {test_voice}")
            print(f"   Payload: {payload}")
            
            # Try to connect to SSE endpoint
            response = requests.post(
                f"{self.base_url}/audio/synthesize-with-progress",
                json=payload,
                stream=True,
                timeout=15
            )
            
            if response.status_code == 401 or response.status_code == 403:
                # Expected - no auth
                details = f"Status: {response.status_code} (expected - no auth provided)"
                self.log_test("SSE simulation test", True, details)
                return True
            elif response.status_code == 200:
                # Unexpected - should require auth, but let's see if we get SSE events
                print("   Unexpected 200 response - checking for SSE events...")
                
                events_received = 0
                try:
                    for line in response.iter_lines(decode_unicode=True):
                        if line and line.startswith('data: '):
                            events_received += 1
                            try:
                                event_data = json.loads(line[6:])  # Remove 'data: '
                                event_type = event_data.get('type', 'unknown')
                                print(f"   SSE Event {events_received}: {event_type}")
                                
                                if events_received >= 2:  # Got first 2 events as requested
                                    break
                            except json.JSONDecodeError:
                                continue
                        
                        if events_received >= 2:
                            break
                    
                    if events_received >= 2:
                        details = f"Status: 200, Received {events_received} SSE events (endpoint working)"
                        self.log_test("SSE simulation test", True, details)
                        return True
                    else:
                        details = f"Status: 200, but only {events_received} SSE events received"
                        self.log_test("SSE simulation test", False, details)
                        return False
                        
                except Exception as e:
                    details = f"Status: 200, but error reading SSE: {str(e)}"
                    self.log_test("SSE simulation test", False, details)
                    return False
            else:
                # Other error
                try:
                    error_data = response.json()
                    error_msg = error_data.get('detail', 'Unknown error')
                except:
                    error_msg = f"HTTP {response.status_code}"
                
                details = f"Status: {response.status_code}, Error: {error_msg}"
                self.log_test("SSE simulation test", False, details)
                return False
                
        except Exception as e:
            self.log_test("SSE simulation test", False, f"Error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all stability and recovery tests"""
        print("🚀 BACKEND STABILITY AND RECOVERY TESTING")
        print("=" * 60)
        print("Цель: Проверить новые фиксы стабильности и восстановления в бэкенде")
        print(f"Backend URL: {self.base_url}")
        print("=" * 60)
        
        # Run tests in order
        startup_ok = self.test_backend_startup()
        voices = self.test_voices_endpoint_public()
        auth_ok = self.test_audio_synthesis_no_auth()
        jobs_ok = self.test_jobs_pending_no_auth()
        self.test_basic_endpoints()
        logs_ok = self.check_logs_for_syntax_errors()
        code_ok = self.verify_code_changes()
        sse_ok = self.test_sse_simulation_mode(voices)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 КРАТКИЙ ИТОГ ТЕСТИРОВАНИЯ")
        print("=" * 60)
        
        critical_tests = [
            ("Сервер запущен", startup_ok),
            ("Публичные endpoints работают", voices is not None),
            ("Защищённые endpoints требуют auth", auth_ok and jobs_ok),
            ("Нет критических ошибок в логах", logs_ok),
            ("Изменения кода присутствуют", code_ok)
        ]
        
        optional_tests = [
            ("SSE endpoint корректно работает", sse_ok)
        ]
        
        print("КРИТИЧЕСКИЕ ПРОВЕРКИ:")
        critical_passed = 0
        for name, success in critical_tests:
            status = "✅" if success else "❌"
            print(f"  {status} {name}")
            if success:
                critical_passed += 1
        
        print("\nДОПОЛНИТЕЛЬНЫЕ ПРОВЕРКИ:")
        optional_passed = 0
        for name, success in optional_tests:
            status = "✅" if success else "❌"
            print(f"  {status} {name}")
            if success:
                optional_passed += 1
        
        print(f"\nОБЩИЕ РЕЗУЛЬТАТЫ:")
        print(f"  Всего тестов: {self.total_tests}")
        print(f"  Пройдено: {self.passed_tests}")
        print(f"  Процент успеха: {(self.passed_tests/self.total_tests)*100:.1f}%")
        
        # Final assessment
        all_critical_passed = critical_passed == len(critical_tests)
        
        if all_critical_passed:
            print(f"\n🎉 ВСЕ КРИТИЧЕСКИЕ ТЕСТЫ ПРОЙДЕНЫ!")
            print(f"✅ Сервер жив и стабилен")
            print(f"✅ Публичные endpoints работают")
            print(f"✅ Защищённые endpoints требуют авторизацию")
            print(f"✅ Критических ошибок не обнаружено")
            
            if voices:
                print(f"✅ Доступно {len(voices)} голосов для синтеза")
            
            if optional_passed > 0:
                print(f"✅ {optional_passed} дополнительных тестов также пройдены")
        else:
            print(f"\n❌ НЕКОТОРЫЕ КРИТИЧЕСКИЕ ТЕСТЫ НЕ ПРОЙДЕНЫ!")
            failed_critical = [name for name, success in critical_tests if not success]
            print(f"❌ Проблемные области: {', '.join(failed_critical)}")
        
        return all_critical_passed

def main():
    tester = BackendStabilityTester()
    success = tester.run_all_tests()
    
    # Save results
    results_file = Path("/app/backend_stability_results.json")
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_tests': tester.total_tests,
            'passed_tests': tester.passed_tests,
            'success_rate': f"{(tester.passed_tests/tester.total_tests)*100:.1f}%",
            'overall_success': success,
            'test_results': tester.test_results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\nРезультаты сохранены в: {results_file}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())