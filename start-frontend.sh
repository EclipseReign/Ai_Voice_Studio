#!/bin/bash

# Скрипт для запуска Frontend

echo "🚀 Запуск Frontend приложения..."
echo ""

# Перейти в папку frontend
cd "$(dirname "$0")/frontend" || exit

# Проверка node_modules
if [ ! -d "node_modules" ]; then
    echo "❌ Зависимости не установлены!"
    echo "Установите их командой: yarn install"
    exit 1
fi

# Проверка .env файла
if [ ! -f ".env" ]; then
    echo "⚠️  Файл .env не найден!"
    echo "Создайте frontend/.env со следующим содержимым:"
    echo ""
    echo "REACT_APP_BACKEND_URL=http://localhost:8001"
    echo ""
    exit 1
fi

# Проверка доступности Backend
echo "🔍 Проверка Backend сервера..."
if ! curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "⚠️  Backend сервер не отвечает на http://localhost:8001"
    echo "Убедитесь что Backend запущен (./start-backend.sh)"
    echo ""
    read -p "Продолжить без проверки Backend? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "✅ Все проверки пройдены!"
echo ""
echo "🌐 Frontend будет доступен на: http://localhost:3000"
echo "📱 Браузер откроется автоматически"
echo ""
echo "Нажмите Ctrl+C для остановки"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Запуск приложения
yarn start
