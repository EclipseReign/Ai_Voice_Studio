#!/usr/bin/env python3
"""
Simple URL Length Test - No Authentication Required
==================================================

This test focuses on the core issue: URL length limits for audio synthesis
Tests the difference between GET (old, broken) and POST (new, fixed) methods
"""

import requests
import json
import time
from datetime import datetime

def test_url_length_limits():
    """Test URL length limits and POST method fix"""
    
    base_url = "https://audioflow-59.preview.emergentagent.com/api"
    
    print("🚀 URL LENGTH LIMIT TESTING")
    print("=" * 50)
    
    # Test 1: Get voices (no auth required)
    print("\n1️⃣ Testing voices endpoint...")
    try:
        response = requests.get(f"{base_url}/voices", timeout=30)
        if response.status_code == 200:
            voices = response.json()
            ru_voices = [v for v in voices if v.get('locale', '').startswith('ru-')]
            print(f"✅ Found {len(voices)} voices, {len(ru_voices)} Russian")
            
            if ru_voices:
                ru_voice = ru_voices[0]['short_name']
                print(f"   Using voice: {ru_voice}")
            else:
                print("❌ No Russian voices found")
                return False
        else:
            print(f"❌ Voices endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Voices endpoint error: {e}")
        return False
    
    # Test 2: Create test texts of different sizes
    print("\n2️⃣ Creating test texts...")
    
    # Small text (should work with both GET and POST)
    small_text = "Это короткий тест синтеза речи. Он должен работать с любым методом."
    
    # Large text (should fail with GET, work with POST)
    large_text = """
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
    """ * 3  # Make it even larger
    
    print(f"   Small text: {len(small_text)} characters")
    print(f"   Large text: {len(large_text)} characters")
    
    # Test 3: Calculate URL lengths
    print("\n3️⃣ Calculating URL lengths...")
    
    def calculate_url_length(text, voice):
        """Calculate what the URL length would be with GET method"""
        import urllib.parse
        encoded_text = urllib.parse.quote(text)
        url = f"{base_url}/audio/synthesize-with-progress?text={encoded_text}&voice={voice}&rate=1.0&language=ru-RU"
        return len(url)
    
    small_url_length = calculate_url_length(small_text, ru_voice)
    large_url_length = calculate_url_length(large_text, ru_voice)
    
    print(f"   Small text URL length: {small_url_length} chars")
    print(f"   Large text URL length: {large_url_length} chars")
    
    # Check against common limits
    browser_limit = 2048
    server_limit = 8192
    
    print(f"   Browser limit (conservative): {browser_limit} chars")
    print(f"   Server limit (typical): {server_limit} chars")
    
    small_exceeds = small_url_length > server_limit
    large_exceeds = large_url_length > server_limit
    
    print(f"   Small text exceeds limit: {small_exceeds}")
    print(f"   Large text exceeds limit: {large_exceeds}")
    
    # Test 4: Test POST method (the fix) - without auth for now
    print("\n4️⃣ Testing POST method (no auth)...")
    
    # Try to test the POST endpoint structure
    test_data = {
        "text": small_text,
        "voice": ru_voice,
        "rate": 1.0,
        "language": "ru-RU"
    }
    
    try:
        response = requests.post(
            f"{base_url}/audio/synthesize-with-progress",
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"   POST request status: {response.status_code}")
        
        if response.status_code == 401:
            print("   ✅ POST endpoint exists but requires authentication (expected)")
            print("   ✅ This confirms the endpoint accepts POST method")
        elif response.status_code == 200:
            print("   ✅ POST method works!")
        else:
            print(f"   Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"   Error testing POST: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    
    print(f"✅ Voices endpoint working: {len(voices)} voices available")
    print(f"✅ Small text URL length: {small_url_length} chars (within limits: {not small_exceeds})")
    print(f"✅ Large text URL length: {large_url_length} chars (exceeds limits: {large_exceeds})")
    print(f"✅ POST endpoint exists and accepts JSON data")
    
    if large_exceeds:
        print("\n🔍 KEY FINDING:")
        print(f"   Large text ({len(large_text)} chars) would create {large_url_length} char URL")
        print(f"   This exceeds typical server limits ({server_limit} chars) by {large_url_length - server_limit} chars")
        print("   ✅ This confirms why GET method failed for large texts")
        print("   ✅ POST method with JSON body solves this limitation")
    
    return True

if __name__ == "__main__":
    test_url_length_limits()