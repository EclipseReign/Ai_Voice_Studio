# 🎙️ Audio TTS Generator - Генератор текста и озвучки

Веб-приложение для генерации текста с помощью AI и преобразования его в речь с использованием Piper TTS.

## ✨ Возможности

- **🤖 AI Генерация текста**: Создавайте контент на любую тему с заданной длительностью
- **🎤 Качественная озвучка**: Используйте Piper TTS для реалистичного звучания
- **🌍 Многоязычность**: Поддержка русского, английского и других языков
- **⚡ Быстрая генерация**: Параллельная обработка для длинных текстов
- **📊 Прогресс в реальном времени**: SSE для отслеживания процесса
- **💾 История генераций**: Сохранение всех созданных аудио
- **⬇️ Скачивание**: Экспорт аудио в формате WAV

## 🚀 Быстрый старт

### Автоматическая установка

**macOS/Linux:**
```bash
git clone https://github.com/ВАШ_USERNAME/ВАШ_РЕПО.git
cd ВАШ_РЕПО
./setup.sh
```

**Windows:**
```bash
git clone https://github.com/ВАШ_USERNAME/ВАШ_РЕПО.git
cd ВАШ_РЕПО
setup.bat
```

### Запуск приложения

**macOS/Linux:**
```bash
# Терминал 1 - Backend
./start-backend.sh

# Терминал 2 - Frontend
./start-frontend.sh
```

**Windows:**
```bash
# Терминал 1 - Backend
start-backend.bat

# Терминал 2 - Frontend
start-frontend.bat
```

Откройте браузер: **http://localhost:3000**

## 📋 Требования

- Python 3.9+
- Node.js 16+
- MongoDB 4.4+
- FFmpeg
- 4GB RAM (рекомендуется 8GB)
- ~2GB свободного места

## 🔑 API Ключи

Вам нужен API ключ для генерации текста:

1. **Emergent LLM Key** (рекомендуется):
   - Зарегистрируйтесь на https://emergent.com
   - Profile → Universal Key
   - Добавьте в `backend/.env`:
     ```env
     EMERGENT_LLM_KEY=ваш_ключ
     ```

2. **OpenAI API Key** (альтернатива):
   - https://platform.openai.com/api-keys
   - Добавьте в `backend/.env`:
     ```env
     OPENAI_API_KEY=sk-ваш_ключ
     ```

## 📚 Документация

- **Полный гайд**: [LOCAL_DEPLOYMENT_GUIDE.md](LOCAL_DEPLOYMENT_GUIDE.md)
- **Быстрый старт**: [QUICK_START.md](QUICK_START.md)

## 🛠️ Технологии

### Backend
- FastAPI (Python)
- Motor (MongoDB async driver)
- Piper TTS (локальная озвучка)
- emergentintegrations (LLM интеграция)
- pydub (обработка аудио)

### Frontend
- React 19
- Tailwind CSS
- Radix UI компоненты
- Axios для HTTP запросов
- Server-Sent Events (SSE) для реального времени

### База данных
- MongoDB (хранение текстов и метаданных)

## 📊 Производительность

- **1 минута аудио**: ~10-20 секунд генерации
- **10 минут аудио**: ~60-90 секунд генерации
- **Точность длительности**: ~83-100% от запрашиваемой

## 🐛 Устранение неполадок

### Backend не запускается
```bash
# Проверьте логи
tail -f /var/log/supervisor/backend.err.log

# Или в терминале где запущен uvicorn
```

### Frontend не подключается
1. Проверьте что backend запущен на http://localhost:8001
2. Проверьте `frontend/.env` - должен быть `REACT_APP_BACKEND_URL=http://localhost:8001`
3. Очистите кэш браузера (Ctrl+Shift+R)

### MongoDB не подключается
```bash
# Проверьте статус
# macOS:
brew services list | grep mongodb

# Linux:
sudo systemctl status mongod

# Windows:
net start MongoDB
```

### Аудио не генерируется
1. Проверьте что ffmpeg установлен: `ffmpeg -version`
2. Проверьте логи backend
3. Модели Piper загружаются автоматически при первом использовании

## 📝 Использование

1. **Откройте приложение**: http://localhost:3000
2. **Выберите режим**:
   - **AI Генерация**: Введите тему, выберите длительность и язык
   - **Ручной ввод**: Напишите свой текст
3. **Сгенерируйте текст** (для AI режима)
4. **Озвучьте текст**: Выберите голос и скорость
5. **Слушайте и скачивайте**: Воспроизведите или скачайте аудио

## 🔒 Безопасность

- API ключи хранятся в `.env` файлах (не коммитятся в git)
- MongoDB работает локально без внешнего доступа
- CORS настроен только для localhost

## 📄 Лицензия

MIT License - используйте свободно для личных и коммерческих проектов

## 🤝 Поддержка

Если у вас возникли проблемы:
1. Проверьте раздел "Устранение неполадок" в [LOCAL_DEPLOYMENT_GUIDE.md](LOCAL_DEPLOYMENT_GUIDE.md)
2. Откройте issue на GitHub
3. Проверьте логи backend и frontend

## 🎉 Готово!

Наслаждайтесь генерацией контента! 🚀
