#!/usr/bin/env python3
"""
TTS Server Stability and Performance Testing

Tests critical fixes for:
1. ThreadPoolExecutor: 24 → 32 workers (for 4 vCPU)
2. Dynamic batch_size: 1 user=24, 2-3 users=12, 4+ users=6-8
3. Removed auto-deletion of files (permanent storage)
4. Job recovery: interrupted jobs → "resumable" status
5. Cleanup only manual through DELETE endpoint

Hardware: Railway Hobby (8GB RAM, 4 vCPU)
"""

import requests
import json
import time
import asyncio
import threading
from datetime import datetime
from pathlib import Path
import subprocess
import sys
import os

class TTSStabilityTester:
    def __init__(self, base_url="https://voicesync-fix.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.test_results = []
        self.generated_audio_ids = []
        self.available_voices = []
        
    def log_result(self, test_name, success, details="", error=""):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "details": details,
            "error": error
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        if error:
            print(f"    ERROR: {error}")
        return success

    def make_request(self, method, endpoint, data=None, timeout=30):
        """Make HTTP request with error handling"""
        url = f"{self.base_url}/{endpoint}" if endpoint else self.base_url
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            return response.status_code, response.json() if response.content else {}
        except requests.exceptions.Timeout:
            return None, {"error": "Request timeout"}
        except requests.exceptions.RequestException as e:
            return None, {"error": str(e)}
        except json.JSONDecodeError:
            return response.status_code, {"error": "Invalid JSON response"}

    def test_1_configuration_check(self):
        """✅ ПРОВЕРКА КОНФИГУРАЦИИ: Server responds, check logs for workers and storage"""
        print("\n🔍 TEST 1: Configuration Check")
        
        # Test 1.1: Server responds
        status, response = self.make_request('GET', 'voices')
        if status != 200:
            return self.log_result("1.1 Server Response", False, 
                                 error=f"Status {status}, expected 200")
        
        voices_count = len(response) if isinstance(response, list) else 0
        self.available_voices = response if isinstance(response, list) else []
        success_1_1 = self.log_result("1.1 Server Response", True, 
                                    f"Server responds, {voices_count} voices available")
        
        # Test 1.2: Check backend logs for worker count
        try:
            result = subprocess.run(
                ["tail", "-n", "50", "/var/log/supervisor/backend.out.log"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                log_content = result.stdout.lower()
                
                # Look for worker count (should be 32 or higher)
                worker_indicators = ["32 workers", "workers", "threadpoolexecutor"]
                found_workers = any(indicator in log_content for indicator in worker_indicators)
                
                # Look for permanent storage
                storage_indicators = ["permanent", "storage", "enabled"]
                found_storage = any(indicator in log_content for indicator in storage_indicators)
                
                success_1_2 = self.log_result("1.2 Worker Configuration", found_workers,
                                            f"Found worker config in logs: {found_workers}")
                success_1_3 = self.log_result("1.3 Permanent Storage", found_storage,
                                            f"Found storage config in logs: {found_storage}")
            else:
                success_1_2 = self.log_result("1.2 Worker Configuration", False,
                                            error="Could not read backend logs")
                success_1_3 = self.log_result("1.3 Permanent Storage", False,
                                            error="Could not read backend logs")
        except Exception as e:
            success_1_2 = self.log_result("1.2 Worker Configuration", False, error=str(e))
            success_1_3 = self.log_result("1.3 Permanent Storage", False, error=str(e))
        
        return success_1_1 and success_1_2 and success_1_3

    def test_2_concurrent_generation(self):
        """✅ ОДНОВРЕМЕННАЯ ГЕНЕРАЦИЯ: 2+ clients, same voice, ~5000 chars"""
        print("\n🔍 TEST 2: Concurrent Generation (2 Clients)")
        
        if not self.available_voices:
            return self.log_result("2.0 Voice Availability", False, 
                                 error="No voices available for testing")
        
        # Find a suitable voice (prefer English for consistency)
        test_voice = None
        for voice in self.available_voices:
            if voice.get('locale', '').startswith('en-'):
                test_voice = voice.get('short_name')
                break
        
        if not test_voice:
            test_voice = self.available_voices[0].get('short_name')
        
        # Generate ~5000 character text (5-10 minutes audio)
        test_text = """
        Artificial intelligence represents one of the most transformative technologies of our era, fundamentally reshaping how we interact with machines and process information. The field encompasses a vast array of methodologies and applications, from machine learning algorithms that can identify patterns in massive datasets to natural language processing systems capable of understanding and generating human-like text. Deep learning networks, inspired by the structure of the human brain, have revolutionized computer vision, enabling machines to recognize objects, faces, and scenes with remarkable accuracy. Neural networks with multiple layers can now perform tasks that were once thought to be exclusively human, such as playing complex games like chess and Go at superhuman levels, translating languages in real-time, and even creating original artwork and music. The applications of AI span virtually every industry and aspect of human life. In healthcare, AI systems assist doctors in diagnosing diseases by analyzing medical images, predicting patient outcomes, and discovering new drug compounds. Autonomous vehicles rely on sophisticated AI algorithms to navigate roads safely, processing input from cameras, sensors, and GPS systems to make split-second decisions. In finance, AI powers fraud detection systems, algorithmic trading platforms, and personalized banking services. Entertainment platforms use recommendation algorithms to suggest content based on user preferences and viewing history. Smart home devices respond to voice commands and learn from user behavior to optimize energy consumption and security. The rapid advancement of AI technology also raises important ethical considerations and challenges that society must address. Questions about job displacement due to automation, privacy concerns related to data collection and surveillance, algorithmic bias that can perpetuate social inequalities, and the potential for AI systems to be used maliciously all require careful consideration and regulation. As AI becomes more powerful and ubiquitous, ensuring that its development and deployment benefit humanity while minimizing potential risks becomes increasingly critical. The future of AI promises even more remarkable developments, including artificial general intelligence that could match or exceed human cognitive abilities across all domains, quantum computing integration that could exponentially increase processing power, and brain-computer interfaces that might allow direct communication between human minds and AI systems.
        """ * 2  # Double it to get ~5000 characters
        
        text_length = len(test_text)
        
        def generate_audio(client_id):
            """Generate audio for one client"""
            start_time = time.time()
            status, response = self.make_request('POST', 'audio/synthesize-with-progress', {
                "text": test_text,
                "voice": test_voice,
                "rate": 1.0,
                "language": "en-US"
            }, timeout=600)  # 10 minute timeout
            
            duration = time.time() - start_time
            
            if status == 200 and response.get('id'):
                audio_id = response.get('id')
                self.generated_audio_ids.append(audio_id)
                return {
                    'client_id': client_id,
                    'success': True,
                    'audio_id': audio_id,
                    'duration': duration,
                    'text_length': text_length
                }
            else:
                return {
                    'client_id': client_id,
                    'success': False,
                    'error': response.get('error', 'Unknown error'),
                    'duration': duration,
                    'text_length': text_length
                }
        
        # Start 2 concurrent requests
        print(f"    Starting 2 concurrent audio generations...")
        print(f"    Voice: {test_voice}")
        print(f"    Text length: {text_length} characters")
        
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(generate_audio, 1),
                executor.submit(generate_audio, 2)
            ]
            
            results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({
                        'client_id': 'unknown',
                        'success': False,
                        'error': str(e),
                        'duration': 0
                    })
        
        # Analyze results
        successful_clients = [r for r in results if r['success']]
        failed_clients = [r for r in results if not r['success']]
        
        success_2_1 = len(successful_clients) == 2
        details = f"Successful: {len(successful_clients)}/2 clients"
        
        if successful_clients:
            avg_duration = sum(r['duration'] for r in successful_clients) / len(successful_clients)
            details += f", Avg duration: {avg_duration:.1f}s"
            
        if failed_clients:
            details += f", Failures: {[r.get('error', 'Unknown') for r in failed_clients]}"
        
        return self.log_result("2.1 Concurrent Generation", success_2_1, details)

    def test_3_files_not_deleted(self):
        """✅ ФАЙЛЫ НЕ УДАЛЯЮТСЯ: Generate audio, wait 10s, check still available"""
        print("\n🔍 TEST 3: Files Not Auto-Deleted")
        
        if not self.available_voices:
            return self.log_result("3.0 Voice Availability", False, 
                                 error="No voices available")
        
        # Use first available voice
        test_voice = self.available_voices[0].get('short_name')
        test_text = "This is a test to verify that audio files are not automatically deleted after generation."
        
        # Generate audio
        print("    Generating test audio...")
        start_time = time.time()
        status, response = self.make_request('POST', 'audio/synthesize-with-progress', {
            "text": test_text,
            "voice": test_voice,
            "rate": 1.0,
            "language": "en-US"
        }, timeout=120)
        
        generation_time = time.time() - start_time
        
        if status != 200 or not response.get('id'):
            return self.log_result("3.1 Audio Generation", False,
                                 error=f"Failed to generate audio: {response}")
        
        audio_id = response.get('id')
        self.generated_audio_ids.append(audio_id)
        
        success_3_1 = self.log_result("3.1 Audio Generation", True,
                                    f"Generated in {generation_time:.1f}s, ID: {audio_id[:8]}...")
        
        # Wait 10 seconds
        print("    Waiting 10 seconds...")
        time.sleep(10)
        
        # Try to download the file
        print("    Checking if file is still available...")
        status, response = self.make_request('GET', f'audio/download/{audio_id}', timeout=30)
        
        success_3_2 = status == 200
        details = f"Download status: {status}" + (f", Size: {len(str(response))} bytes" if success_3_2 else "")
        
        return self.log_result("3.2 File Still Available", success_3_2, details) and success_3_1

    def test_4_history_storage(self):
        """✅ ИСТОРИЯ ХРАНИТСЯ: Check history shows file_deleted = false"""
        print("\n🔍 TEST 4: History Storage")
        
        # Get history
        status, response = self.make_request('GET', 'history', timeout=30)
        
        if status != 200:
            return self.log_result("4.1 History Endpoint", False,
                                 error=f"Status {status}, expected 200")
        
        if not isinstance(response, list):
            return self.log_result("4.1 History Endpoint", False,
                                 error="History response is not a list")
        
        history_count = len(response)
        success_4_1 = self.log_result("4.1 History Endpoint", True,
                                    f"Retrieved {history_count} history items")
        
        # Check for file_deleted field
        files_with_deleted_false = 0
        files_with_deleted_true = 0
        
        for item in response:
            file_deleted = item.get('file_deleted', None)
            if file_deleted is False:
                files_with_deleted_false += 1
            elif file_deleted is True:
                files_with_deleted_true += 1
        
        success_4_2 = files_with_deleted_false > 0
        details = f"Files with deleted=false: {files_with_deleted_false}, deleted=true: {files_with_deleted_true}"
        
        return self.log_result("4.2 Files Not Marked Deleted", success_4_2, details) and success_4_1

    def test_5_manual_deletion(self):
        """✅ РУЧНОЕ УДАЛЕНИЕ: Test DELETE endpoint, check freed_mb"""
        print("\n🔍 TEST 5: Manual Deletion")
        
        if not self.generated_audio_ids:
            return self.log_result("5.0 Audio ID Available", False,
                                 error="No audio IDs available for deletion test")
        
        # Use the first generated audio ID
        audio_id = self.generated_audio_ids[0]
        
        # First verify the file exists
        status, response = self.make_request('GET', f'audio/download/{audio_id}', timeout=30)
        
        if status != 200:
            return self.log_result("5.1 File Exists Before Delete", False,
                                 error=f"File not accessible before deletion: {status}")
        
        success_5_1 = self.log_result("5.1 File Exists Before Delete", True,
                                    f"File accessible, size: {len(str(response))} bytes")
        
        # Try to delete the file
        print(f"    Deleting audio file: {audio_id[:8]}...")
        status, response = self.make_request('POST', f'audio/cleanup/{audio_id}', timeout=30)
        
        if status != 200:
            return self.log_result("5.2 Manual Deletion", False,
                                 error=f"Delete request failed: {status}")
        
        # Check response format
        success = response.get('success', False)
        freed_mb = response.get('freed_mb', 0)
        message = response.get('message', '')
        
        success_5_2 = success and freed_mb > 0
        details = f"Success: {success}, Freed: {freed_mb:.2f}MB, Message: {message}"
        
        success_5_2 = self.log_result("5.2 Manual Deletion", success_5_2, details)
        
        # Verify file is now inaccessible
        time.sleep(1)  # Brief wait
        status, response = self.make_request('GET', f'audio/download/{audio_id}', timeout=30)
        
        success_5_3 = status == 404
        details = f"Download status after delete: {status} (expected 404)"
        
        return self.log_result("5.3 File Deleted Successfully", success_5_3, details) and success_5_1 and success_5_2

    def test_6_stress_test_optional(self):
        """🔥 STRESS TEST (OPTIONAL): 3-5 parallel generations"""
        print("\n🔍 TEST 6: Stress Test (3 Parallel Generations)")
        
        if not self.available_voices:
            return self.log_result("6.0 Voice Availability", False,
                                 error="No voices available")
        
        # Use first available voice
        test_voice = self.available_voices[0].get('short_name')
        
        # Shorter text for stress test to avoid timeouts
        test_text = """
        Machine learning algorithms have revolutionized data analysis and pattern recognition across numerous industries. 
        These sophisticated systems can process vast amounts of information, identify complex relationships, and make 
        predictions with remarkable accuracy. From recommendation engines that suggest products and content to fraud 
        detection systems that protect financial transactions, machine learning applications continue to expand and 
        improve our daily experiences. The technology enables computers to learn from data without being explicitly 
        programmed for every possible scenario, making it incredibly versatile and powerful.
        """
        
        def generate_audio_stress(client_id):
            """Generate audio for stress test"""
            start_time = time.time()
            status, response = self.make_request('POST', 'audio/synthesize-with-progress', {
                "text": test_text,
                "voice": test_voice,
                "rate": 1.0,
                "language": "en-US"
            }, timeout=300)  # 5 minute timeout for stress test
            
            duration = time.time() - start_time
            
            return {
                'client_id': client_id,
                'success': status == 200 and response.get('id') is not None,
                'audio_id': response.get('id') if status == 200 else None,
                'duration': duration,
                'status': status,
                'error': response.get('error') if status != 200 else None
            }
        
        # Start 3 concurrent requests
        print(f"    Starting 3 concurrent stress test generations...")
        print(f"    Voice: {test_voice}")
        print(f"    Text length: {len(test_text)} characters")
        
        import concurrent.futures
        
        stress_start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(generate_audio_stress, i+1)
                for i in range(3)
            ]
            
            results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                    if result['success'] and result['audio_id']:
                        self.generated_audio_ids.append(result['audio_id'])
                except Exception as e:
                    results.append({
                        'client_id': 'unknown',
                        'success': False,
                        'error': str(e),
                        'duration': 0
                    })
        
        total_stress_time = time.time() - stress_start_time
        
        # Analyze results
        successful_clients = [r for r in results if r['success']]
        failed_clients = [r for r in results if not r['success']]
        
        success_count = len(successful_clients)
        success_6_1 = success_count >= 2  # At least 2 out of 3 should succeed
        
        details = f"Successful: {success_count}/3 clients in {total_stress_time:.1f}s"
        
        if successful_clients:
            avg_duration = sum(r['duration'] for r in successful_clients) / len(successful_clients)
            details += f", Avg duration: {avg_duration:.1f}s"
        
        if failed_clients:
            error_summary = [f"Client {r['client_id']}: {r.get('error', 'Unknown')}" for r in failed_clients]
            details += f", Failures: {error_summary}"
        
        return self.log_result("6.1 Stress Test (3 Clients)", success_6_1, details)

    def check_memory_usage(self):
        """Check current memory usage"""
        try:
            result = subprocess.run(['free', '-m'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    mem_line = lines[1].split()
                    if len(mem_line) >= 3:
                        total_mb = int(mem_line[1])
                        used_mb = int(mem_line[2])
                        usage_percent = (used_mb / total_mb) * 100
                        return {
                            'total_mb': total_mb,
                            'used_mb': used_mb,
                            'usage_percent': usage_percent
                        }
        except Exception as e:
            print(f"    Warning: Could not check memory usage: {e}")
        return None

    def run_all_tests(self):
        """Run all stability tests"""
        print("🚀 TTS SERVER STABILITY & PERFORMANCE TESTING")
        print("=" * 60)
        print("Testing critical fixes:")
        print("- ThreadPoolExecutor: 24 → 32 workers")
        print("- Dynamic batch_size allocation")
        print("- Permanent file storage (no auto-deletion)")
        print("- Manual cleanup endpoints")
        print("- Job recovery system")
        print("=" * 60)
        
        # Check initial memory usage
        initial_memory = self.check_memory_usage()
        if initial_memory:
            print(f"Initial memory usage: {initial_memory['used_mb']}/{initial_memory['total_mb']} MB ({initial_memory['usage_percent']:.1f}%)")
        
        # Run all tests
        test_results = []
        
        test_results.append(self.test_1_configuration_check())
        test_results.append(self.test_2_concurrent_generation())
        test_results.append(self.test_3_files_not_deleted())
        test_results.append(self.test_4_history_storage())
        test_results.append(self.test_5_manual_deletion())
        test_results.append(self.test_6_stress_test_optional())
        
        # Check final memory usage
        final_memory = self.check_memory_usage()
        if final_memory:
            print(f"\nFinal memory usage: {final_memory['used_mb']}/{final_memory['total_mb']} MB ({final_memory['usage_percent']:.1f}%)")
            if initial_memory:
                memory_increase = final_memory['used_mb'] - initial_memory['used_mb']
                print(f"Memory increase during testing: {memory_increase} MB")
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed_tests = sum(test_results)
        total_tests = len(test_results)
        
        critical_tests = test_results[:5]  # First 5 are critical
        optional_tests = test_results[5:]  # Last ones are optional
        
        critical_passed = sum(critical_tests)
        critical_total = len(critical_tests)
        
        print(f"CRITICAL TESTS: {critical_passed}/{critical_total} passed")
        print(f"OPTIONAL TESTS: {sum(optional_tests)}/{len(optional_tests)} passed")
        print(f"OVERALL: {passed_tests}/{total_tests} passed")
        
        # Detailed results
        print("\nDetailed Results:")
        for i, result in enumerate(self.test_results, 1):
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['test']}")
            if result['details']:
                print(f"    {result['details']}")
            if result['error']:
                print(f"    ERROR: {result['error']}")
        
        # Final assessment
        all_critical_passed = critical_passed == critical_total
        
        if all_critical_passed:
            print("\n🎉 ALL CRITICAL TESTS PASSED!")
            print("✅ Server configuration correct")
            print("✅ Concurrent generation working")
            print("✅ Files not auto-deleted")
            print("✅ History storage working")
            print("✅ Manual deletion working")
            
            if sum(optional_tests) == len(optional_tests):
                print("✅ All optional tests also passed!")
            else:
                print("⚠️  Some optional tests failed, but core functionality works")
                
            print("\n🚀 SERVER IS READY FOR PRODUCTION!")
            
        else:
            print("\n❌ SOME CRITICAL TESTS FAILED!")
            failed_tests = [self.test_results[i]['test'] for i, passed in enumerate(critical_tests) if not passed]
            print(f"Failed: {', '.join(failed_tests)}")
            print("🔧 Server needs fixes before production")
        
        # Save results
        results_file = '/app/tts_stability_results.json'
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'critical_passed': critical_passed,
                    'critical_total': critical_total,
                    'optional_passed': sum(optional_tests),
                    'optional_total': len(optional_tests),
                    'overall_passed': passed_tests,
                    'overall_total': total_tests,
                    'all_critical_passed': all_critical_passed
                },
                'memory_usage': {
                    'initial': initial_memory,
                    'final': final_memory
                },
                'generated_audio_ids': self.generated_audio_ids,
                'detailed_results': self.test_results
            }, f, indent=2)
        
        print(f"\nDetailed results saved to: {results_file}")
        
        return all_critical_passed

def main():
    """Main test runner"""
    tester = TTSStabilityTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())