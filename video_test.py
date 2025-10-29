#!/usr/bin/env python3
"""
Video Generation Testing Script
Focus: Critical video generation fixes verification

REVIEW REQUEST FOCUS:
1. Video generation endpoints testing (POST /api/video/generate-with-progress, GET /api/video/history, GET /api/video/status/{job_id})
2. HuggingFace API endpoint verification (should use new router.huggingface.co URL)
3. Video URL fix verification (should NOT have /api prefix in backend)
4. Backend stability check
"""

import requests
import json
import time
import sys
from pathlib import Path

class VideoGenerationTester:
    def __init__(self):
        # Use the production backend URL from frontend/.env
        self.base_url = "https://api-logger.preview.emergentagent.com/api"
        self.test_results = []
        
    def log_result(self, test_name, success, details):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        
    def test_huggingface_api_url_fix(self):
        """Verify HuggingFace API URL has been updated to new endpoint"""
        print("\n🔍 TESTING: HuggingFace API URL Fix")
        
        try:
            # Read video_service.py to check the API URL
            video_service_path = Path("/app/backend/video_service.py")
            
            if not video_service_path.exists():
                self.log_result("HF API URL Check", False, "video_service.py not found")
                return False
                
            with open(video_service_path, 'r') as f:
                content = f.read()
            
            # Check for new URL
            new_url = "https://router.huggingface.co/hf-inference/models"
            old_url = "api-inference.huggingface.co"
            
            has_new_url = new_url in content
            has_old_url = old_url in content
            
            if has_new_url and not has_old_url:
                self.log_result("HF API URL Fix", True, f"✅ Using new endpoint: {new_url}")
                return True
            elif has_old_url:
                self.log_result("HF API URL Fix", False, f"❌ Still using deprecated endpoint: {old_url}")
                return False
            else:
                self.log_result("HF API URL Fix", False, "❌ No HuggingFace API URL found")
                return False
                
        except Exception as e:
            self.log_result("HF API URL Fix", False, f"Error reading file: {str(e)}")
            return False
    
    def test_video_url_fix(self):
        """Verify video download URLs don't have double /api prefix"""
        print("\n🔍 TESTING: Video URL Fix (No Double /api Prefix)")
        
        try:
            # Read server.py to check video_url format
            server_path = Path("/app/backend/server.py")
            
            if not server_path.exists():
                self.log_result("Video URL Fix", False, "server.py not found")
                return False
                
            with open(server_path, 'r') as f:
                content = f.read()
            
            # Look for video_url assignments
            lines = content.split('\n')
            video_url_lines = [line for line in lines if 'video_url' in line and '/video/download/' in line]
            
            if not video_url_lines:
                self.log_result("Video URL Fix", False, "No video_url assignments found")
                return False
            
            # Check if any line has /api/video/download (double prefix)
            has_double_prefix = any('/api/video/download/' in line for line in video_url_lines)
            has_correct_format = any('"/video/download/' in line for line in video_url_lines)
            
            if has_correct_format and not has_double_prefix:
                self.log_result("Video URL Fix", True, "✅ video_url uses correct format: /video/download/{id}")
                return True
            elif has_double_prefix:
                self.log_result("Video URL Fix", False, "❌ Found double /api prefix in video URLs")
                return False
            else:
                self.log_result("Video URL Fix", False, "❌ video_url format unclear")
                return False
                
        except Exception as e:
            self.log_result("Video URL Fix", False, f"Error reading file: {str(e)}")
            return False
    
    def test_video_generate_endpoint(self):
        """Test POST /api/video/generate-with-progress endpoint"""
        print("\n🔍 TESTING: Video Generation Endpoint")
        
        try:
            url = f"{self.base_url}/video/generate-with-progress"
            
            # Test data as specified in review request
            test_data = {
                "text_id": "test_text_id",
                "audio_id": "test_audio_id",
                "video_type": "shorts"
            }
            
            response = requests.post(url, json=test_data, timeout=10)
            
            # Should return 401 without authentication (security working)
            if response.status_code == 401:
                self.log_result("Video Generate Endpoint", True, "✅ Returns 401 without auth (security working)")
                return True
            elif response.status_code == 200:
                self.log_result("Video Generate Endpoint", False, "❌ Accepts requests without auth (security issue)")
                return False
            else:
                self.log_result("Video Generate Endpoint", False, f"❌ Unexpected status: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_result("Video Generate Endpoint", False, f"Request error: {str(e)}")
            return False
    
    def test_video_history_endpoint(self):
        """Test GET /api/video/history endpoint"""
        print("\n🔍 TESTING: Video History Endpoint")
        
        try:
            url = f"{self.base_url}/video/history"
            
            response = requests.get(url, timeout=10)
            
            # Should return 401 without authentication
            if response.status_code == 401:
                self.log_result("Video History Endpoint", True, "✅ Returns 401 without auth (security working)")
                return True
            elif response.status_code == 200:
                self.log_result("Video History Endpoint", False, "❌ Accepts requests without auth (security issue)")
                return False
            else:
                self.log_result("Video History Endpoint", False, f"❌ Unexpected status: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_result("Video History Endpoint", False, f"Request error: {str(e)}")
            return False
    
    def test_video_status_endpoint(self):
        """Test GET /api/video/status/{job_id} endpoint"""
        print("\n🔍 TESTING: Video Status Endpoint")
        
        try:
            test_job_id = "test_job_id_123"
            url = f"{self.base_url}/video/status/{test_job_id}"
            
            response = requests.get(url, timeout=10)
            
            # Should return 401 without authentication or 404 for non-existent job
            if response.status_code in [401, 404]:
                self.log_result("Video Status Endpoint", True, f"✅ Returns {response.status_code} (expected behavior)")
                return True
            elif response.status_code == 200:
                self.log_result("Video Status Endpoint", False, "❌ Accepts requests without auth (security issue)")
                return False
            else:
                self.log_result("Video Status Endpoint", False, f"❌ Unexpected status: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_result("Video Status Endpoint", False, f"Request error: {str(e)}")
            return False
    
    def test_backend_stability(self):
        """Test backend stability and basic functionality"""
        print("\n🔍 TESTING: Backend Stability")
        
        try:
            # Test root endpoint
            url = f"{self.base_url}/"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "message" in data:
                        self.log_result("Backend Stability", True, f"✅ Backend responding: {data.get('message')}")
                        return True
                except:
                    pass
            
            self.log_result("Backend Stability", False, f"❌ Backend not responding properly: {response.status_code}")
            return False
            
        except requests.exceptions.RequestException as e:
            self.log_result("Backend Stability", False, f"Backend connection error: {str(e)}")
            return False
    
    def test_video_service_import(self):
        """Test that video_service can be imported without errors"""
        print("\n🔍 TESTING: Video Service Import")
        
        try:
            # Check if video_service.py exists and has no syntax errors
            video_service_path = Path("/app/backend/video_service.py")
            
            if not video_service_path.exists():
                self.log_result("Video Service Import", False, "video_service.py not found")
                return False
            
            # Try to compile the file to check for syntax errors
            with open(video_service_path, 'r') as f:
                content = f.read()
            
            try:
                compile(content, str(video_service_path), 'exec')
                self.log_result("Video Service Import", True, "✅ video_service.py compiles without syntax errors")
                return True
            except SyntaxError as e:
                self.log_result("Video Service Import", False, f"❌ Syntax error: {str(e)}")
                return False
                
        except Exception as e:
            self.log_result("Video Service Import", False, f"Error checking file: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all video generation tests"""
        print("🎬 VIDEO GENERATION CRITICAL FIXES TESTING")
        print("=" * 60)
        print(f"Backend URL: {self.base_url}")
        print()
        
        # Run all tests
        tests = [
            self.test_huggingface_api_url_fix,
            self.test_video_url_fix,
            self.test_video_service_import,
            self.test_backend_stability,
            self.test_video_generate_endpoint,
            self.test_video_history_endpoint,
            self.test_video_status_endpoint,
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 VIDEO GENERATION TEST SUMMARY")
        print("=" * 60)
        
        success_rate = (passed / total) * 100
        print(f"Tests Passed: {passed}/{total} ({success_rate:.1f}%)")
        
        # Categorize results
        critical_fixes = [
            "HF API URL Fix",
            "Video URL Fix", 
            "Video Service Import",
            "Backend Stability"
        ]
        
        endpoint_tests = [
            "Video Generate Endpoint",
            "Video History Endpoint", 
            "Video Status Endpoint"
        ]
        
        print("\n🔧 CRITICAL FIXES:")
        for result in self.test_results:
            if result["test"] in critical_fixes:
                status = "✅" if result["success"] else "❌"
                print(f"  {status} {result['test']}")
        
        print("\n🌐 ENDPOINT TESTS:")
        for result in self.test_results:
            if result["test"] in endpoint_tests:
                status = "✅" if result["success"] else "❌"
                print(f"  {status} {result['test']}")
        
        # Overall assessment
        critical_passed = sum(1 for r in self.test_results if r["test"] in critical_fixes and r["success"])
        endpoint_passed = sum(1 for r in self.test_results if r["test"] in endpoint_tests and r["success"])
        
        print(f"\n📈 RESULTS:")
        print(f"Critical Fixes: {critical_passed}/{len(critical_fixes)} passed")
        print(f"Endpoint Tests: {endpoint_passed}/{len(endpoint_tests)} passed")
        
        if critical_passed == len(critical_fixes) and endpoint_passed == len(endpoint_tests):
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ HuggingFace API updated to new endpoint")
            print("✅ Video URL double prefix issue fixed")
            print("✅ Video endpoints require authentication (security working)")
            print("✅ Backend is stable and running")
            return True
        elif critical_passed == len(critical_fixes):
            print("\n✅ CRITICAL FIXES VERIFIED!")
            print("⚠️  Some endpoint tests may need attention")
            return True
        else:
            print("\n❌ SOME CRITICAL ISSUES FOUND!")
            failed_critical = [r["test"] for r in self.test_results if r["test"] in critical_fixes and not r["success"]]
            if failed_critical:
                print(f"❌ Failed critical tests: {', '.join(failed_critical)}")
            return False

def main():
    tester = VideoGenerationTester()
    success = tester.run_all_tests()
    
    # Save results
    with open('/app/video_test_results.json', 'w') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'success': success,
            'test_results': tester.test_results
        }, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())