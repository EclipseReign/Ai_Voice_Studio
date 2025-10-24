#!/bin/bash

# Скрипт для запуска Backend

echo "🚀 Запуск Backend сервера..."
echo ""

# Перейти в папку backend
cd "$(dirname "$0")/backend" || exit

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено!"
    echo "Создайте его командой: python3 -m venv venv"
    exit 1
fi

# Проверка .env файла
if [ ! -f ".env" ]; then
    echo "⚠️  Файл .env не найден!"
    echo "Создайте backend/.env со следующим содержимым:"
    echo ""
    echo "MONGO_URL=mongodb://localhost:27017"
    echo "DB_NAME=audio_tts_db"
    echo "EMERGENT_LLM_KEY=ваш_ключ_здесь"
    echo "HOST=0.0.0.0"
    echo "PORT=8001"
    echo ""
    exit 1
fi

# Активация виртуального окружения
echo "📦 Активация виртуального окружения..."
source venv/bin/activate

# Проверка MongoDB
echo "🔍 Проверка MongoDB..."
if ! mongosh --eval "db.version()" > /dev/null 2>&1; then
    echo "⚠️  MongoDB не запущен!"
    echo "Запустите MongoDB:"
    echo "  macOS: brew services start mongodb-community"
    echo "  Linux: sudo systemctl start mongod"
    echo ""
    read -p "Продолжить без проверки MongoDB? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "✅ Все проверки пройдены!"
echo ""
echo "🌐 Backend будет доступен на: http://localhost:8001"
echo "📚 API документация: http://localhost:8001/docs"
echo ""
echo "Нажмите Ctrl+C для остановки"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Запуск сервера
uvicorn server:app --reload --host 0.0.0.0 --port 8001
