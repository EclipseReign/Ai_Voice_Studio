@echo off
chcp 65001 >nul

echo ════════════════════════════════════════════════════════════
echo   🔧 Настройка проекта Audio TTS Generator
echo ════════════════════════════════════════════════════════════
echo.

echo 📋 Проверка системных зависимостей...
echo.

REM Python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Python установлен
) else (
    echo ❌ Python не найден! Установите Python 3.9+
    pause
    exit /b 1
)

REM Node.js
node --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Node.js установлен
) else (
    echo ❌ Node.js не найден! Установите Node.js 16+
    pause
    exit /b 1
)

REM Yarn
yarn --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Yarn установлен
) else (
    echo ⚠️  Yarn не найден. Устанавливаю...
    npm install -g yarn
)

echo.
echo ═══════════════════════════════════════════════════════════
echo   📦 Настройка Backend
echo ═══════════════════════════════════════════════════════════
echo.

cd backend

REM Создание виртуального окружения
if not exist "venv" (
    echo Создание виртуального окружения...
    python -m venv venv
    echo ✅ Виртуальное окружение создано
) else (
    echo ✅ Виртуальное окружение уже существует
)

REM Активация и установка зависимостей
echo.
echo Установка Python зависимостей...
call venv\Scripts\activate
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ --quiet
echo ✅ Backend зависимости установлены

REM Создание .env если не существует
if not exist ".env" (
    echo.
    echo ⚠️  Создание backend\.env файла...
    (
        echo # MongoDB настройки
        echo MONGO_URL=mongodb://localhost:27017
        echo DB_NAME=audio_tts_db
        echo.
        echo # API ключи
        echo # Получите ключ на https://emergent.com
        echo EMERGENT_LLM_KEY=your_api_key_here
        echo.
        echo # Backend настройки
        echo HOST=0.0.0.0
        echo PORT=8001
    ) > .env
    echo ✅ Файл backend\.env создан
    echo ⚠️  ВАЖНО: Добавьте ваш EMERGENT_LLM_KEY в backend\.env!
) else (
    echo ✅ Файл backend\.env уже существует
)

cd ..

echo.
echo ═══════════════════════════════════════════════════════════
echo   ⚛️  Настройка Frontend
echo ═══════════════════════════════════════════════════════════
echo.

cd frontend

REM Установка зависимостей
echo Установка Node.js зависимостей (это может занять несколько минут)...
yarn install
echo ✅ Frontend зависимости установлены

REM Создание .env если не существует
if not exist ".env" (
    echo.
    echo ⚠️  Создание frontend\.env файла...
    (
        echo # URL бэкенда (для локального развертывания)
        echo REACT_APP_BACKEND_URL=http://localhost:8001
    ) > .env
    echo ✅ Файл frontend\.env создан
) else (
    echo ✅ Файл frontend\.env уже существует
)

cd ..

REM Создание папок для данных
echo.
echo Создание папок для данных...
if not exist "backend\audio_files" mkdir backend\audio_files
if not exist "backend\piper_models" mkdir backend\piper_models
echo ✅ Папки созданы

echo.
echo ════════════════════════════════════════════════════════════
echo   ✅ Настройка завершена!
echo ════════════════════════════════════════════════════════════
echo.
echo 📝 Следующие шаги:
echo.
echo 1. Добавьте ваш API ключ в backend\.env:
echo    EMERGENT_LLM_KEY=ваш_ключ_здесь
echo.
echo 2. Убедитесь что MongoDB запущен:
echo    Windows: net start MongoDB
echo.
echo 3. Запустите приложение:
echo    Терминал 1: start-backend.bat
echo    Терминал 2: start-frontend.bat
echo.
echo 4. Откройте браузер: http://localhost:3000
echo.
echo 📚 Подробная документация: LOCAL_DEPLOYMENT_GUIDE.md
echo ⚡ Быстрый старт: QUICK_START.md
echo.
echo ════════════════════════════════════════════════════════════
echo.
pause
