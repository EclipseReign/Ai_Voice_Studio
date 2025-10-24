@echo off
chcp 65001 >nul

echo 🚀 Запуск Frontend приложения...
echo.

cd /d "%~dp0frontend"

REM Проверка node_modules
if not exist "node_modules" (
    echo ❌ Зависимости не установлены!
    echo Установите их командой: yarn install
    pause
    exit /b 1
)

REM Проверка .env файла
if not exist ".env" (
    echo ⚠️  Файл .env не найден!
    echo Создайте frontend\.env со следующим содержимым:
    echo.
    echo REACT_APP_BACKEND_URL=http://localhost:8001
    echo.
    pause
    exit /b 1
)

echo ✅ Все проверки пройдены!
echo.
echo 🌐 Frontend будет доступен на: http://localhost:3000
echo 📱 Браузер откроется автоматически
echo.
echo Нажмите Ctrl+C для остановки
echo ═══════════════════════════════════════════════════════════
echo.

REM Запуск приложения
yarn start
