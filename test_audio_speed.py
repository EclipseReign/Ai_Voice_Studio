#!/usr/bin/env python3
"""Test script to measure audio generation speed"""
import time
import requests
import json

API = "http://localhost:8001/api"

# Short test text (simulate ~5 minutes)
test_text = """
Искусственный интеллект представляет собой одну из самых захватывающих областей современной науки и технологий. История развития ИИ начинается с середины двадцатого века, когда ученые впервые задумались о создании машин, способных мыслить. Первые шаги в этом направлении были сделаны в 1950-х годах, когда Алан Тьюринг предложил свой знаменитый тест для определения разумности машины.

В последующие десятилетия исследователи разработали множество подходов к созданию искусственного интеллекта. Символьные системы, экспертные системы и нейронные сети стали основными направлениями исследований. Каждый из этих подходов имел свои преимущества и ограничения, но все они внесли важный вклад в развитие области.

Современный этап развития ИИ начался с появлением глубокого обучения и больших данных. Эти технологии позволили создавать системы, способные решать сложные задачи распознавания образов, обработки естественного языка и принятия решений. Сегодня искусственный интеллект используется в самых разных областях: от медицины и финансов до транспорта и развлечений.
""".strip()

print("=" * 60)
print("ТЕСТ СКОРОСТИ ГЕНЕРАЦИИ АУДИО")
print("=" * 60)
print(f"\nДлина текста: {len(test_text)} символов")
print(f"Примерно ~{len(test_text) / 300:.1f} минут аудио")

# Test with SSE endpoint
print("\n[1/1] Тестируем SSE endpoint (с оптимизацией)...")
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
response = requests.get(url, params=params, stream=True, timeout=300)

if response.status_code == 200:
    segments_count = 0
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                try:
                    data = json.loads(line_str[6:])
                    msg_type = data.get('type', '')
                    progress = data.get('progress', 0)
                    message = data.get('message', '')
                    
                    if msg_type == 'info':
                        print(f"  📝 {message} (прогресс: {progress}%)")
                        if 'сегментов' in message:
                            import re
                            match = re.search(r'(\d+) сегментов', message)
                            if match:
                                segments_count = int(match.group(1))
                    elif msg_type == 'progress':
                        if progress % 20 == 0 or progress == 90:
                            print(f"  ⚙️  {message} (прогресс: {progress}%)")
                    elif msg_type == 'complete':
                        elapsed = time.time() - start_time
                        print(f"\n  ✅ Готово за {elapsed:.1f} секунд!")
                        print(f"  📊 Сегментов обработано: {segments_count}")
                        print(f"  ⚡ Скорость: ~{elapsed/60:.2f} минут для ~{len(test_text)/300:.1f} минут аудио")
                        break
                    elif msg_type == 'error':
                        print(f"  ❌ Ошибка: {data.get('message')}")
                        break
                except json.JSONDecodeError as e:
                    print(f"  ⚠️  Не удалось разобрать: {line_str}")
else:
    print(f"❌ Ошибка HTTP: {response.status_code}")
    print(response.text)

print("\n" + "=" * 60)
print("ТЕСТ ЗАВЕРШЕН")
print("=" * 60)
