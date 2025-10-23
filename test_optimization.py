#!/usr/bin/env python3
"""Simple test to verify audio generation optimization"""
import time
import requests
import json
import sys

API = "http://localhost:8001/api"

# Medium test text (~2000 chars = ~3-4 segments with 1500 char limit)
test_text = """
Искусственный интеллект представляет собой одну из самых захватывающих областей современной науки и технологий. 
История развития ИИ начинается с середины двадцатого века, когда ученые впервые задумались о создании машин, 
способных мыслить. Первые шаги в этом направлении были сделаны в 1950-х годах, когда Алан Тьюринг предложил 
свой знаменитый тест для определения разумности машины.

В последующие десятилетия исследователи разработали множество подходов к созданию искусственного интеллекта. 
Символьные системы, экспертные системы и нейронные сети стали основными направлениями исследований. Каждый из 
этих подходов имел свои преимущества и ограничения, но все они внесли важный вклад в развитие области.

Современный этап развития ИИ начался с появлением глубокого обучения и больших данных. Эти технологии позволили 
создавать системы, способные решать сложные задачи распознавания образов, обработки естественного языка и принятия 
решений. Сегодня искусственный интеллект используется в самых разных областях: от медицины и финансов до транспорта 
и развлечений.

Машинное обучение стало ключевой технологией в развитии современного ИИ. Алгоритмы машинного обучения позволяют 
компьютерам учиться на данных без явного программирования. Глубокие нейронные сети, вдохновленные структурой 
человеческого мозга, показали выдающиеся результаты в распознавании изображений, понимании речи и игре в сложные 
стратегические игры. Эти достижения открыли новые возможности для применения ИИ в реальном мире.

Будущее искусственного интеллекта обещает быть еще более впечатляющим. Исследователи работают над созданием 
более мощных и эффективных алгоритмов, которые смогут решать все более сложные задачи. Важным направлением 
является разработка объяснимого ИИ, который сможет не только принимать решения, но и объяснять их человеку.
""".strip()

print("=" * 70)
print("ТЕСТ ОПТИМИЗАЦИИ ГЕНЕРАЦИИ АУДИО")
print("=" * 70)
print(f"Размер текста: {len(test_text)} символов")
print(f"Ожидаемые сегменты: ~{(len(test_text) // 1500) + 1}")
print(f"Примерная длина аудио: ~{len(test_text) / 300:.1f} минут")
print("=" * 70)

start_time = time.time()
url = f"{API}/audio/synthesize-with-progress"
params = {
    'text': test_text,
    'voice': 'ru_RU-irina-medium',
    'rate': 1.0,
    'language': 'ru-RU'
}

try:
    response = requests.get(url, params=params, stream=True, timeout=120)
    
    if response.status_code == 200:
        segments_count = 0
        progress_updates = []
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])
                        msg_type = data.get('type', '')
                        progress = data.get('progress', 0)
                        message = data.get('message', '')
                        elapsed = time.time() - start_time
                        
                        if msg_type == 'info':
                            print(f"[{elapsed:5.1f}s] 📝 {message}")
                            if 'сегментов' in message:
                                import re
                                match = re.search(r'(\d+) сегментов', message)
                                if match:
                                    segments_count = int(match.group(1))
                        elif msg_type == 'progress':
                            progress_updates.append((elapsed, progress, message))
                            print(f"[{elapsed:5.1f}s] ⚙️  {message} - {progress}%")
                        elif msg_type == 'complete':
                            total_time = time.time() - start_time
                            print(f"\n{'='*70}")
                            print(f"✅ УСПЕШНО ЗАВЕРШЕНО!")
                            print(f"{'='*70}")
                            print(f"⏱️  Время генерации: {total_time:.1f} секунд")
                            print(f"📊 Обработано сегментов: {segments_count}")
                            print(f"📏 Размер текста: {len(test_text)} символов")
                            print(f"🎵 Примерная длина аудио: ~{len(test_text)/300:.1f} минут")
                            print(f"⚡ Скорость: {len(test_text)/total_time:.0f} символов/сек")
                            
                            # Calculate ratio
                            audio_minutes = len(test_text) / 300
                            gen_minutes = total_time / 60
                            ratio = audio_minutes / gen_minutes if gen_minutes > 0 else 0
                            print(f"🚀 Эффективность: {ratio:.1f}x скорость реального времени")
                            print(f"   (генерация {audio_minutes:.1f} мин аудио за {gen_minutes:.2f} мин)")
                            print(f"{'='*70}")
                            sys.exit(0)
                        elif msg_type == 'error':
                            print(f"❌ ОШИБКА: {data.get('message')}")
                            sys.exit(1)
                    except json.JSONDecodeError:
                        pass
    else:
        print(f"❌ HTTP ошибка: {response.status_code}")
        print(response.text[:500])
        sys.exit(1)

except Exception as e:
    print(f"❌ ИСКЛЮЧЕНИЕ: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
