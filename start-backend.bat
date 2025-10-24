@echo off
chcp 65001 >nul

echo 🚀 Запуск Backend сервера...
echo.

cd /d "%~dp0backend"

REM Проверка виртуального окружения
if not exist "venv" (
    echo ❌ Виртуальное окружение не найдено!
    echo Создайте его командой: python -m venv venv
    pause
    exit /b 1
)

REM Проверка .env файла
if not exist ".env" (
    echo ⚠️  Файл .env не найден!
    echo Создайте backend\.env со следующим содержимым:
    echo.
    echo MONGO_URL=mongodb://localhost:27017
    echo DB_NAME=audio_tts_db
    echo EMERGENT_LLM_KEY=ваш_ключ_здесь
    echo HOST=0.0.0.0
    echo PORT=8001
    echo.
    pause
    exit /b 1
)

echo 📦 Активация виртуального окружения...
call venv\Scripts\activate

echo ✅ Все проверки пройдены!
echo.
echo 🌐 Backend будет доступен на: http://localhost:8001
echo 📚 API документация: http://localhost:8001/docs
echo.
echo Нажмите Ctrl+C для остановки
echo ═══════════════════════════════════════════════════════════
echo.

REM Запуск сервера
uvicorn server:app --reload --host 0.0.0.0 --port 8001
