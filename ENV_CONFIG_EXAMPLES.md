# 🔐 Примеры конфигурационных файлов

Этот файл содержит примеры `.env` файлов для быстрой настройки проекта.

## Backend .env файл

Создайте файл `backend/.env` со следующим содержимым:

```env
# ========================================
# MongoDB Настройки
# ========================================
MONGO_URL=mongodb://localhost:27017
DB_NAME=audio_tts_db

# ========================================
# API Ключи
# ========================================

# Вариант 1: Emergent LLM Key (рекомендуется)
# Получите на: https://emergent.com → Profile → Universal Key
EMERGENT_LLM_KEY=your_emergent_key_here

# Вариант 2: OpenAI API Key (альтернатива)
# Получите на: https://platform.openai.com/api-keys
# OPENAI_API_KEY=sk-your_openai_key_here

# ========================================
# Backend Настройки
# ========================================
HOST=0.0.0.0
PORT=8001

# ========================================
# Опциональные настройки
# ========================================
# DEBUG=True
# LOG_LEVEL=INFO
```

---

## Frontend .env файл

Создайте файл `frontend/.env` со следующим содержимым:

```env
# ========================================
# Backend URL
# ========================================

# Для локального развертывания
REACT_APP_BACKEND_URL=http://localhost:8001

# Для доступа из локальной сети (замените на ваш IP)
# REACT_APP_BACKEND_URL=http://192.168.1.100:8001

# Для production (замените на ваш домен)
# REACT_APP_BACKEND_URL=https://yourdomain.com
```

---

## 📝 Инструкции по настройке

### Шаг 1: Создайте backend/.env

**macOS/Linux:**
```bash
cd backend
cat > .env << 'EOL'
MONGO_URL=mongodb://localhost:27017
DB_NAME=audio_tts_db
EMERGENT_LLM_KEY=your_key_here
HOST=0.0.0.0
PORT=8001
EOL
```

**Windows (PowerShell):**
```powershell
cd backend
@"
MONGO_URL=mongodb://localhost:27017
DB_NAME=audio_tts_db
EMERGENT_LLM_KEY=your_key_here
HOST=0.0.0.0
PORT=8001
"@ | Out-File -FilePath .env -Encoding utf8
```

**Или создайте вручную:**
1. Откройте текстовый редактор
2. Создайте файл `backend/.env`
3. Скопируйте содержимое из примера выше
4. Замените `your_key_here` на ваш реальный ключ

### Шаг 2: Создайте frontend/.env

**macOS/Linux:**
```bash
cd frontend
echo "REACT_APP_BACKEND_URL=http://localhost:8001" > .env
```

**Windows (PowerShell):**
```powershell
cd frontend
"REACT_APP_BACKEND_URL=http://localhost:8001" | Out-File -FilePath .env -Encoding utf8
```

**Или создайте вручную:**
1. Откройте текстовый редактор
2. Создайте файл `frontend/.env`
3. Добавьте строку: `REACT_APP_BACKEND_URL=http://localhost:8001`

---

## 🔑 Где получить API ключи

### Emergent LLM Key (рекомендуется)

1. Зарегистрируйтесь: https://emergent.com
2. Войдите в аккаунт
3. Нажмите на иконку профиля (правый верхний угол)
4. Выберите "Universal Key"
5. Скопируйте ключ
6. Добавьте в `backend/.env`:
   ```env
   EMERGENT_LLM_KEY=emergent_ваш_ключ_здесь
   ```

**Преимущества Emergent LLM Key:**
- ✅ Работает с OpenAI, Anthropic, Google Gemini
- ✅ Единый ключ для всех провайдеров
- ✅ Удобное управление
- ✅ Бесплатный тестовый период

### OpenAI API Key (альтернатива)

1. Зарегистрируйтесь: https://platform.openai.com
2. Войдите в аккаунт
3. Перейдите в раздел "API Keys"
4. Нажмите "Create new secret key"
5. Скопируйте ключ (он показывается только один раз!)
6. Добавьте в `backend/.env`:
   ```env
   OPENAI_API_KEY=sk-proj-ваш_ключ_здесь
   ```

**Важно:**
- ⚠️ Для OpenAI нужна действующая подписка
- ⚠️ Стоимость: ~$0.002 за 1000 токенов для GPT-4o-mini
- ⚠️ Ключ показывается только один раз при создании

---

## 🔒 Безопасность

### ❌ НЕ ДЕЛАЙТЕ:

```bash
# НЕ коммитьте .env файлы в git
git add backend/.env    # ❌ ПЛОХО
git add frontend/.env   # ❌ ПЛОХО

# НЕ публикуйте ключи в коде
const API_KEY = "sk-proj-xxxxx";  # ❌ ПЛОХО
```

### ✅ ДЕЛАЙТЕ:

```bash
# Используйте переменные окружения
import os
api_key = os.environ.get('EMERGENT_LLM_KEY')  # ✅ ХОРОШО

# Проверьте что .env в .gitignore
cat .gitignore | grep ".env"  # Должно быть: *.env
```

### Защита ключей:

1. **Никогда не коммитьте .env** файлы в git
2. **Используйте .gitignore** для исключения .env
3. **Не делитесь скриншотами** с ключами
4. **Ротируйте ключи** регулярно
5. **Используйте разные ключи** для разработки и продакшена

---

## 🌐 Настройка для продакшена

### Backend .env (производство)

```env
# MongoDB (используйте MongoDB Atlas или другой cloud)
MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/dbname

# База данных
DB_NAME=audio_tts_prod

# API ключи
EMERGENT_LLM_KEY=your_production_key_here

# Backend настройки
HOST=0.0.0.0
PORT=8001

# Production настройки
DEBUG=False
LOG_LEVEL=WARNING
ALLOWED_ORIGINS=https://yourdomain.com
```

### Frontend .env (производство)

```env
# Production backend URL
REACT_APP_BACKEND_URL=https://api.yourdomain.com

# Или если backend и frontend на одном домене
# REACT_APP_BACKEND_URL=https://yourdomain.com/api
```

---

## 🔧 Расширенные настройки

### Использование Docker

Создайте файл `.env.docker`:

```env
# Docker-specific settings
MONGO_URL=mongodb://mongodb:27017
DB_NAME=audio_tts_db
EMERGENT_LLM_KEY=${EMERGENT_LLM_KEY}
HOST=0.0.0.0
PORT=8001
```

### Использование с Nginx

```env
# Backend за Nginx proxy
REACT_APP_BACKEND_URL=https://yourdomain.com/api
BACKEND_PROXY_PATH=/api
```

### Множественные окружения

**development.env:**
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=audio_tts_dev
EMERGENT_LLM_KEY=dev_key
DEBUG=True
```

**production.env:**
```env
MONGO_URL=mongodb+srv://cluster.mongodb.net/
DB_NAME=audio_tts_prod
EMERGENT_LLM_KEY=prod_key
DEBUG=False
```

Загрузка:
```bash
# Development
source development.env && uvicorn server:app

# Production
source production.env && uvicorn server:app
```

---

## ✅ Проверка конфигурации

### Проверка Backend:

```bash
cd backend
source venv/bin/activate

# Проверка переменных
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print(f'MONGO_URL: {os.environ.get('MONGO_URL')[:20]}...')
print(f'DB_NAME: {os.environ.get('DB_NAME')}')
print(f'EMERGENT_LLM_KEY: {os.environ.get('EMERGENT_LLM_KEY')[:10]}...')
"
```

### Проверка Frontend:

```bash
cd frontend

# Проверка переменных
cat .env | grep REACT_APP_BACKEND_URL

# Или в Node.js
node -e "console.log(require('dotenv').config().parsed)"
```

---

## 🆘 Troubleshooting

### "Environment variable not found"

```bash
# Убедитесь что .env файл существует
ls -la backend/.env
ls -la frontend/.env

# Проверьте права доступа
chmod 600 backend/.env
chmod 600 frontend/.env

# Перезапустите приложение после изменений
```

### "MongoDB connection failed"

```bash
# Проверьте MONGO_URL
echo $MONGO_URL

# Проверьте что MongoDB запущен
mongosh $MONGO_URL
```

### "EMERGENT_LLM_KEY invalid"

```bash
# Проверьте что ключ правильный
echo $EMERGENT_LLM_KEY

# Убедитесь что нет лишних пробелов
EMERGENT_LLM_KEY=key_without_spaces
```

---

## 📚 Дополнительная информация

- **Полная документация**: [LOCAL_DEPLOYMENT_GUIDE.md](LOCAL_DEPLOYMENT_GUIDE.md)
- **Быстрый старт**: [QUICK_START.md](QUICK_START.md)
- **README**: [README_RU.md](README_RU.md)

---

**Версия**: 1.0  
**Последнее обновление**: Январь 2025
