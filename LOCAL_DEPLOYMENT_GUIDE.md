# 🚀 Гайд по развертыванию на локальной машине

Этот гайд поможет вам развернуть приложение для генерации текста и озвучки на вашем компьютере.

## 📋 Системные требования

- **Операционная система**: Windows, macOS или Linux
- **Python**: 3.9 или выше
- **Node.js**: 16.x или выше
- **MongoDB**: 4.4 или выше
- **RAM**: Минимум 4GB (рекомендуется 8GB)
- **Свободное место**: ~2GB для моделей Piper TTS

---

## 🔧 Шаг 1: Установка системных зависимостей

### Windows:

1. **Python 3.9+**
   - Скачайте с https://www.python.org/downloads/
   - Установите, отметив "Add Python to PATH"

2. **Node.js**
   - Скачайте с https://nodejs.org/
   - Установите LTS версию

3. **MongoDB**
   - Скачайте с https://www.mongodb.com/try/download/community
   - Установите как сервис
   - Или используйте MongoDB Compass для удобного управления

4. **FFmpeg** (для обработки аудио)
   ```bash
   # Скачайте с https://ffmpeg.org/download.html
   # Добавьте в PATH
   ```

5. **Yarn** (пакетный менеджер)
   ```bash
   npm install -g yarn
   ```

### macOS:

```bash
# Установите Homebrew (если еще не установлен)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Установите зависимости
brew install python@3.11
brew install node
brew tap mongodb/brew
brew install mongodb-community
brew install ffmpeg
npm install -g yarn

# Запустите MongoDB
brew services start mongodb-community
```

### Linux (Ubuntu/Debian):

```bash
# Обновите систему
sudo apt update && sudo apt upgrade -y

# Python 3.9+
sudo apt install python3 python3-pip python3-venv -y

# Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

# Yarn
npm install -g yarn

# MongoDB
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt update
sudo apt install mongodb-org -y
sudo systemctl start mongod
sudo systemctl enable mongod

# FFmpeg
sudo apt install ffmpeg -y
```

---

## 📥 Шаг 2: Клонирование проекта

```bash
# Клонируйте ваш репозиторий
git clone https://github.com/ВАШ_USERNAME/ВАШ_РЕПОЗИТОРИЙ.git
cd ВАШ_РЕПОЗИТОРИЙ
```

---

## 🔑 Шаг 3: Настройка переменных окружения

### Backend (.env файл)

Создайте файл `.env` в папке `backend/`:

```bash
cd backend
nano .env  # или используйте любой текстовый редактор
```

Добавьте следующие переменные:

```env
# MongoDB настройки
MONGO_URL=mongodb://localhost:27017
DB_NAME=audio_tts_db

# API ключи
# Получите ключ на https://emergent.com (если используете Emergent)
# Или используйте OpenAI API key: https://platform.openai.com/api-keys
EMERGENT_LLM_KEY=ваш_api_ключ_здесь

# Если вместо Emergent используете OpenAI напрямую
# OPENAI_API_KEY=sk-ваш_ключ_здесь

# Backend настройки
HOST=0.0.0.0
PORT=8001
```

### Frontend (.env файл)

Создайте файл `.env` в папке `frontend/`:

```bash
cd ../frontend
nano .env
```

Добавьте:

```env
# URL бэкенда (для локального развертывания)
REACT_APP_BACKEND_URL=http://localhost:8001
```

---

## 🐍 Шаг 4: Настройка Backend

```bash
# Перейдите в папку backend
cd backend

# Создайте виртуальное окружение
python3 -m venv venv

# Активируйте виртуальное окружение:
# На Windows:
venv\Scripts\activate
# На macOS/Linux:
source venv/bin/activate

# Установите зависимости
pip install --upgrade pip
pip install -r requirements.txt

# Установите emergentintegrations (если используете Emergent LLM)
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
```

**Важно**: Первый запуск может занять время, так как Piper TTS будет загружать модели голосов (~500MB).

---

## ⚛️ Шаг 5: Настройка Frontend

```bash
# Перейдите в папку frontend
cd ../frontend

# Установите зависимости с помощью Yarn
yarn install

# Если возникают ошибки, попробуйте:
yarn install --network-timeout 100000
```

---

## 🗄️ Шаг 6: Проверка MongoDB

Убедитесь, что MongoDB запущен:

```bash
# Windows (в PowerShell как администратор):
net start MongoDB

# macOS:
brew services list | grep mongodb

# Linux:
sudo systemctl status mongod

# Проверьте подключение:
mongosh  # или mongo (для старых версий)
# Вы должны увидеть MongoDB shell
# Выйдите командой: exit
```

---

## 🚀 Шаг 7: Запуск приложения

### Вариант 1: Запуск в двух терминалах (рекомендуется для разработки)

**Терминал 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # или venv\Scripts\activate на Windows
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

Вы должны увидеть:
```
INFO:     Uvicorn running on http://0.0.0.0:8001
INFO:     Application startup complete.
```

**Терминал 2 - Frontend:**
```bash
cd frontend
yarn start
```

Браузер автоматически откроется на `http://localhost:3000`

### Вариант 2: Использование скриптов (создайте для удобства)

**Создайте файл `start-backend.sh` (macOS/Linux):**
```bash
#!/bin/bash
cd backend
source venv/bin/activate
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

**Или `start-backend.bat` (Windows):**
```batch
@echo off
cd backend
call venv\Scripts\activate
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

**Создайте файл `start-frontend.sh` (macOS/Linux):**
```bash
#!/bin/bash
cd frontend
yarn start
```

**Или `start-frontend.bat` (Windows):**
```batch
@echo off
cd frontend
yarn start
```

Сделайте скрипты исполняемыми (macOS/Linux):
```bash
chmod +x start-backend.sh start-frontend.sh
```

Теперь запускайте:
```bash
# Терминал 1:
./start-backend.sh

# Терминал 2:
./start-frontend.sh
```

---

## ✅ Шаг 8: Проверка работоспособности

1. **Откройте браузер**: `http://localhost:3000`

2. **Проверьте Backend API**: `http://localhost:8001/docs`
   - Должна открыться Swagger документация

3. **Протестируйте генерацию**:
   - Выберите режим "AI Генерация"
   - Введите тему: "Космос"
   - Выберите длительность: 1 минута
   - Язык: Русский
   - Нажмите "Сгенерировать текст"
   - Затем "Озвучить текст"
   - Проверьте что аудио воспроизводится и скачивается

---

## 🔧 Устранение неполадок

### Backend не запускается

**Ошибка**: `ModuleNotFoundError`
```bash
# Убедитесь что виртуальное окружение активировано
# Переустановите зависимости:
pip install -r requirements.txt
```

**Ошибка**: `MongoDB connection failed`
```bash
# Проверьте что MongoDB запущен:
sudo systemctl status mongod  # Linux
brew services list | grep mongodb  # macOS
net start MongoDB  # Windows

# Проверьте MONGO_URL в .env файле
```

**Ошибка**: `EMERGENT_LLM_KEY not found`
```bash
# Убедитесь что в backend/.env есть строка:
EMERGENT_LLM_KEY=ваш_ключ
# Перезапустите backend
```

### Frontend не запускается

**Ошибка**: `Module not found`
```bash
# Очистите кэш и переустановите:
rm -rf node_modules yarn.lock
yarn install
```

**Ошибка**: `REACT_APP_BACKEND_URL not defined`
```bash
# Проверьте frontend/.env файл
# Перезапустите frontend
```

**Ошибка**: `Port 3000 already in use`
```bash
# Windows:
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# macOS/Linux:
lsof -ti:3000 | xargs kill -9
```

### Аудио не генерируется

**Ошибка**: `ffmpeg not found`
```bash
# Установите ffmpeg:
# Windows: Скачайте с https://ffmpeg.org/download.html
# macOS: brew install ffmpeg
# Linux: sudo apt install ffmpeg
```

**Модели Piper не загружаются**:
```bash
# Модели загружаются автоматически при первом использовании
# Проверьте интернет-соединение
# Папка с моделями: backend/piper_models/
```

### База данных не подключается

```bash
# Проверьте что MongoDB запущен и доступен:
mongosh mongodb://localhost:27017
# или
mongo mongodb://localhost:27017

# Если не работает, проверьте логи:
# macOS: /usr/local/var/log/mongodb/
# Linux: /var/log/mongodb/
# Windows: C:\Program Files\MongoDB\Server\X.X\log\
```

---

## 📊 Проверка логов

### Backend логи:
```bash
cd backend
# Логи появятся в терминале где запущен uvicorn
```

### Frontend логи:
```bash
# Откройте браузер
# Нажмите F12 (Developer Tools)
# Вкладка Console - логи JavaScript
# Вкладка Network - HTTP запросы
```

### MongoDB логи:
```bash
# Linux:
sudo tail -f /var/log/mongodb/mongod.log

# macOS:
tail -f /usr/local/var/log/mongodb/mongo.log
```

---

## 🎯 Полезные команды

```bash
# Остановить все процессы
# Ctrl+C в каждом терминале

# Очистить базу данных MongoDB
mongosh
use audio_tts_db
db.dropDatabase()
exit

# Обновить зависимости
cd backend && pip install -r requirements.txt --upgrade
cd frontend && yarn upgrade

# Проверить версии
python --version
node --version
npm --version
yarn --version
mongod --version
```

---

## 🌐 Настройка для доступа из сети

Если хотите дать доступ другим устройствам в локальной сети:

1. **Узнайте ваш локальный IP**:
   ```bash
   # Windows:
   ipconfig
   # Найдите IPv4 Address (например, 192.168.1.100)
   
   # macOS/Linux:
   ifconfig | grep inet
   # или
   ip addr show
   ```

2. **Измените frontend/.env**:
   ```env
   REACT_APP_BACKEND_URL=http://192.168.1.100:8001
   ```

3. **Перезапустите frontend**

4. **Откройте на другом устройстве**: `http://192.168.1.100:3000`

---

## 📝 Структура проекта

```
.
├── backend/
│   ├── server.py              # Главный файл FastAPI
│   ├── requirements.txt       # Python зависимости
│   ├── .env                   # Переменные окружения (создать)
│   ├── audio_files/          # Сгенерированные аудио (создается автоматически)
│   └── piper_models/         # Модели TTS (загружаются автоматически)
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   └── HomePage.js   # Главная страница
│   │   └── App.js            # Основное приложение
│   ├── public/               # Статические файлы
│   ├── package.json          # Node.js зависимости
│   └── .env                  # Переменные окружения (создать)
│
└── README.md                 # Основная документация
```

---

## 🔐 Получение API ключей

### Emergent LLM Key (рекомендуется):
1. Зарегистрируйтесь на https://emergent.com
2. Войдите в аккаунт
3. Нажмите на иконку профиля → Universal Key
4. Скопируйте ключ и добавьте в `backend/.env`:
   ```env
   EMERGENT_LLM_KEY=ваш_ключ_здесь
   ```

### OpenAI API Key (альтернатива):
1. Зарегистрируйтесь на https://platform.openai.com
2. Создайте API ключ в разделе API Keys
3. Добавьте в `backend/.env`:
   ```env
   OPENAI_API_KEY=sk-ваш_ключ_здесь
   ```
4. **Важно**: Если используете OpenAI напрямую, нужно изменить код в `backend/server.py`:
   ```python
   # Найдите строку:
   chat = LlmChat(
       api_key=os.environ.get('EMERGENT_LLM_KEY'),
       ...
   )
   
   # Замените на:
   from openai import AsyncOpenAI
   client = AsyncOpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
   ```

---

## ⚡ Производительность

**Ожидаемые скорости генерации**:
- **Текст (1 минута)**: ~5-10 секунд
- **Аудио (1 минута)**: ~10-20 секунд
- **Текст (10 минут)**: ~20-40 секунд
- **Аудио (10 минут)**: ~60-90 секунд

**Первый запуск медленнее** из-за загрузки моделей Piper TTS (~500MB).

---

## 🎉 Готово!

Теперь у вас полностью работающее приложение на локальной машине!

**Что дальше?**
- Попробуйте разные языки и настройки
- Проверьте историю генераций
- Экспериментируйте с длительностью

**Нужна помощь?**
- Проверьте раздел "Устранение неполадок"
- Откройте issue на GitHub
- Проверьте логи в терминале

---

## 📌 Важные замечания

1. **API ключи**: Без `EMERGENT_LLM_KEY` или `OPENAI_API_KEY` генерация текста не будет работать
2. **MongoDB**: Должен быть запущен перед стартом backend
3. **FFmpeg**: Необходим для обработки аудио (склейка сегментов)
4. **Порты**: Убедитесь что порты 3000 и 8001 свободны
5. **Первый запуск**: Займет дольше времени из-за загрузки моделей

---

## 🛠 Для разработчиков

### Запуск тестов:
```bash
# Backend тесты
cd backend
pytest

# Frontend тесты
cd frontend
yarn test
```

### Форматирование кода:
```bash
# Backend (Python)
cd backend
black server.py
flake8 server.py

# Frontend (JavaScript)
cd frontend
yarn eslint src/
```

### Сборка для продакшена:
```bash
# Frontend production build
cd frontend
yarn build
# Файлы будут в папке build/

# Backend production запуск
cd backend
uvicorn server:app --host 0.0.0.0 --port 8001 --workers 4
```

---

**Версия гайда**: 1.0  
**Дата**: Январь 2025  
**Совместимость**: Python 3.9+, Node.js 16+, MongoDB 4.4+
