#!/bin/bash

# Скрипт первоначальной настройки проекта

echo "════════════════════════════════════════════════════════════"
echo "  🔧 Настройка проекта Audio TTS Generator"
echo "════════════════════════════════════════════════════════════"
echo ""

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода статуса
print_status() {
    echo -e "${GREEN}✅${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

# Проверка системных зависимостей
echo "📋 Проверка системных зависимостей..."
echo ""

# Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_status "Python установлен: $PYTHON_VERSION"
else
    print_error "Python3 не найден! Установите Python 3.9+"
    exit 1
fi

# Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    print_status "Node.js установлен: $NODE_VERSION"
else
    print_error "Node.js не найден! Установите Node.js 16+"
    exit 1
fi

# Yarn
if command -v yarn &> /dev/null; then
    YARN_VERSION=$(yarn --version)
    print_status "Yarn установлен: $YARN_VERSION"
else
    print_warning "Yarn не найден. Устанавливаю..."
    npm install -g yarn
fi

# MongoDB
if command -v mongosh &> /dev/null || command -v mongo &> /dev/null; then
    print_status "MongoDB CLI установлен"
else
    print_warning "MongoDB CLI не найден. Убедитесь что MongoDB установлен!"
fi

# FFmpeg
if command -v ffmpeg &> /dev/null; then
    print_status "FFmpeg установлен"
else
    print_warning "FFmpeg не найден. Установите для обработки аудио!"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  📦 Настройка Backend"
echo "═══════════════════════════════════════════════════════════"
echo ""

cd backend || exit

# Создание виртуального окружения
if [ ! -d "venv" ]; then
    echo "Создание виртуального окружения..."
    python3 -m venv venv
    print_status "Виртуальное окружение создано"
else
    print_status "Виртуальное окружение уже существует"
fi

# Активация и установка зависимостей
echo ""
echo "Установка Python зависимостей..."
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ --quiet
print_status "Backend зависимости установлены"

# Создание .env если не существует
if [ ! -f ".env" ]; then
    echo ""
    print_warning "Создание backend/.env файла..."
    cat > .env << EOL
# MongoDB настройки
MONGO_URL=mongodb://localhost:27017
DB_NAME=audio_tts_db

# API ключи
# Получите ключ на https://emergent.com
EMERGENT_LLM_KEY=your_api_key_here

# Backend настройки
HOST=0.0.0.0
PORT=8001
EOL
    print_status "Файл backend/.env создан"
    print_warning "⚠️  ВАЖНО: Добавьте ваш EMERGENT_LLM_KEY в backend/.env!"
else
    print_status "Файл backend/.env уже существует"
fi

cd ..

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ⚛️  Настройка Frontend"
echo "═══════════════════════════════════════════════════════════"
echo ""

cd frontend || exit

# Установка зависимостей
echo "Установка Node.js зависимостей (это может занять несколько минут)..."
yarn install
print_status "Frontend зависимости установлены"

# Создание .env если не существует
if [ ! -f ".env" ]; then
    echo ""
    print_warning "Создание frontend/.env файла..."
    cat > .env << EOL
# URL бэкенда (для локального развертывания)
REACT_APP_BACKEND_URL=http://localhost:8001
EOL
    print_status "Файл frontend/.env создан"
else
    print_status "Файл frontend/.env уже существует"
fi

cd ..

# Создание папок для данных
echo ""
echo "Создание папок для данных..."
mkdir -p backend/audio_files
mkdir -p backend/piper_models
print_status "Папки созданы"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✅ Настройка завершена!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📝 Следующие шаги:"
echo ""
echo "1. Добавьте ваш API ключ в backend/.env:"
echo "   EMERGENT_LLM_KEY=ваш_ключ_здесь"
echo ""
echo "2. Убедитесь что MongoDB запущен:"
echo "   macOS: brew services start mongodb-community"
echo "   Linux: sudo systemctl start mongod"
echo ""
echo "3. Запустите приложение:"
echo "   Терминал 1: ./start-backend.sh"
echo "   Терминал 2: ./start-frontend.sh"
echo ""
echo "4. Откройте браузер: http://localhost:3000"
echo ""
echo "📚 Подробная документация: LOCAL_DEPLOYMENT_GUIDE.md"
echo "⚡ Быстрый старт: QUICK_START.md"
echo ""
echo "════════════════════════════════════════════════════════════"
