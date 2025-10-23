#!/usr/bin/env python3
"""Test script to measure audio generation speed for longer text"""
import time
import requests
import json

API = "http://localhost:8001/api"

# Generate a longer text (simulate ~10-15 minutes)
base_paragraph = """
Искусственный интеллект представляет собой одну из самых захватывающих областей современной науки и технологий. 
История развития ИИ начинается с середины двадцатого века, когда ученые впервые задумались о создании машин, 
способных мыслить. Первые шаги в этом направлении были сделаны в 1950-х годах, когда Алан Тьюринг предложил 
свой знаменитый тест для определения разумности машины. В последующие десятилетия исследователи разработали 
множество подходов к созданию искусственного интеллекта. Символьные системы, экспертные системы и нейронные 
сети стали основными направлениями исследований. Каждый из этих подходов имел свои преимущества и ограничения, 
но все они внесли важный вклад в развитие области. Современный этап развития ИИ начался с появлением глубокого 
обучения и больших данных. Эти технологии позволили создавать системы, способные решать сложные задачи 
распознавания образов, обработки естественного языка и принятия решений.
"""

# Repeat to make it longer (~5000 characters = ~15-20 segments)
test_text = (base_paragraph * 8).strip()

print("=" * 60)
print("ТЕСТ СКОРОСТИ ГЕНЕРАЦИИ АУДИО (ДЛИННЫЙ ТЕКСТ)")
print("=" * 60)
print(f"\nДлина текста: {len(test_text)} символов")
print(f"Примерно ~{len(test_text) / 300:.1f} минут аудио")
print(f"Ожидаемое количество сегментов: ~{len(test_text) / 1500:.0f}-{len(test_text) / 1000:.0f}")

# Test with SSE endpoint
print("\n[ТЕСТ] SSE endpoint с оптимизацией...")
print("-" * 60)

start_time = time.time()
url = f"{API}/audio/synthesize-with-progress"
params = {
    'text': test_text,
    'voice': 'ru_RU-irina-medium',
    'rate': 1.0,
    'language': 'ru-RU'
}

# Use requests with stream=True for SSE
response = requests.get(url, params=params, stream=True, timeout=600)

if response.status_code == 200:
    segments_count = 0
    batch_times = []
    last_progress_time = start_time
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                try:
                    data = json.loads(line_str[6:])
                    msg_type = data.get('type', '')
                    progress = data.get('progress', 0)
                    message = data.get('message', '')
                    current_time = time.time()
                    
                    if msg_type == 'info':
                        print(f"  📝 [{current_time-start_time:.1f}s] {message}")
                        if 'сегментов' in message:
                            import re
                            match = re.search(r'(\d+) сегментов', message)
                            if match:
                                segments_count = int(match.group(1))
                    elif msg_type == 'progress':
                        batch_time = current_time - last_progress_time
                        batch_times.append(batch_time)
                        print(f"  ⚙️  [{current_time-start_time:.1f}s] {message} (+{batch_time:.1f}s)")
                        last_progress_time = current_time
                    elif msg_type == 'complete':
                        elapsed = time.time() - start_time
                        print(f"\n  ✅ ГОТОВО за {elapsed:.1f} секунд ({elapsed/60:.2f} минут)!")
                        print(f"\n  📊 СТАТИСТИКА:")
                        print(f"     • Всего сегментов: {segments_count}")
                        print(f"     • Размер текста: {len(test_text)} символов")
                        print(f"     • Примерная длина аудио: ~{len(test_text)/300:.1f} минут")
                        print(f"     • Время генерации: {elapsed:.1f} секунд")
                        print(f"     • Скорость: {len(test_text)/elapsed:.0f} символов/сек")
                        if batch_times:
                            avg_batch = sum(batch_times) / len(batch_times)
                            print(f"     • Среднее время на батч: {avg_batch:.1f}s")
                        
                        # Calculate efficiency
                        audio_minutes = len(test_text) / 300
                        generation_minutes = elapsed / 60
                        ratio = audio_minutes / generation_minutes
                        print(f"\n  ⚡ ЭФФЕКТИВНОСТЬ: {ratio:.1f}x")
                        print(f"     (генерация {audio_minutes:.1f} минут аудио за {generation_minutes:.2f} минут)")
                        break
                    elif msg_type == 'error':
                        print(f"  ❌ Ошибка: {data.get('message')}")
                        break
                except json.JSONDecodeError as e:
                    pass
else:
    print(f"❌ Ошибка HTTP: {response.status_code}")

print("\n" + "=" * 60)
print("ТЕСТ ЗАВЕРШЕН")
print("=" * 60)
