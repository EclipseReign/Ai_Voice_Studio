# ⚡ Быстрый старт (TL;DR)

Краткая инструкция для опытных разработчиков.

## 📦 Установите зависимости

```bash
# System dependencies
# macOS:
brew install python node mongodb-community ffmpeg
brew services start mongodb-community

# Linux (Ubuntu/Debian):
sudo apt install python3 nodejs mongodb ffmpeg -y
sudo systemctl start mongod

# Windows: установите вручную с официальных сайтов
```

## 🚀 Быстрая настройка

```bash
# 1. Клонируйте репо
git clone https://github.com/ВАШ_USERNAME/ВАШ_РЕПО.git
cd ВАШ_РЕПО

# 2. Backend setup
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/

# Создайте backend/.env:
cat > .env << EOL
MONGO_URL=mongodb://localhost:27017
DB_NAME=audio_tts_db
EMERGENT_LLM_KEY=ваш_ключ_здесь
HOST=0.0.0.0
PORT=8001
EOL

# 3. Frontend setup
cd ../frontend
yarn install

# Создайте frontend/.env:
cat > .env << EOL
REACT_APP_BACKEND_URL=http://localhost:8001
EOL
```

## ▶️ Запуск

```bash
# Терминал 1 - Backend:
cd backend
source venv/bin/activate
uvicorn server:app --reload --host 0.0.0.0 --port 8001

# Терминал 2 - Frontend:
cd frontend
yarn start
```

## ✅ Проверка

- Frontend: http://localhost:3000
- Backend API: http://localhost:8001/docs
- MongoDB: `mongosh` (проверка подключения)

## 🔑 Получите API ключ

**Emergent LLM** (рекомендуется):
https://emergent.com → Profile → Universal Key

**Или OpenAI**:
https://platform.openai.com/api-keys

---

**Проблемы?** Смотрите полный гайд в `LOCAL_DEPLOYMENT_GUIDE.md`
