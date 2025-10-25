# 🚀 Гайд по хостингу TTS приложения

## 📊 Анализ проблемы

### Текущая ситуация:
- **Железо**: Ryzen 7 3750H (4 ядра/8 потоков) + GTX 1650
- **Скорость**: 50 минут аудио = 25 минут генерации
- **Нужно**: 50 минут аудио = 2 минуты генерации (**в 12.5 раз быстрее!**)

### Почему медленно:
1. **Piper TTS использует только CPU** (не GPU!)
2. Ryzen 7 3750H - мобильный процессор с низкой тактовой частотой
3. Даже с оптимизацией кода на этом железе невозможно достичь 2 минут

---

## ✅ Что я сделал в коде (оптимизация):

### 1. ThreadPoolExecutor с максимальными воркерами
```python
max_workers = max(multiprocessing.cpu_count() * 2, 16)
executor = ThreadPoolExecutor(max_workers=max_workers)
```

### 2. Уменьшил размер сегментов для большей параллелизации
- Было: 1500 символов
- Стало: **800 символов** (больше мелких задач = лучше параллелится)

### 3. Увеличил batch_size до максимума
- Было: 100 сегментов
- Стало: **все сегменты сразу** (batch_size = total_segments)

### 4. Использую shared thread pool
- Вместо создания нового потока для каждого сегмента
- Используется общий пул потоков (эффективнее)

### Ожидаемый результат:
- На вашем железе: **может улучшиться до 15-20 минут** (но не до 2 минут!)
- На мощном сервере: **2-5 минут возможно**

---

## 🌐 РЕШЕНИЕ #1: Бесплатный хостинг (с ограничениями)

### Railway.app (Рекомендую!)
**Плюсы:**
- $5 бесплатных кредитов в месяц
- 8 GB RAM, 8 vCPU
- Автодеплой из GitHub
- HTTPS из коробки

**Минусы:**
- После $5 нужно платить (~$5-10/месяц)
- 500 часов выполнения в месяц

**Как задеплоить:**
```bash
# 1. Создай аккаунт на railway.app
# 2. Подключи GitHub репозиторий
# 3. Railway автоматически определит FastAPI + React
# 4. Добавь переменные окружения:
#    - MONGO_URL (используй Railway MongoDB или MongoDB Atlas Free)
#    - EMERGENT_LLM_KEY
# 5. Deploy!
```

**Инструкция:**
1. Зайди на https://railway.app
2. "Start a New Project" → "Deploy from GitHub"
3. Выбери свой репозиторий
4. Railway создаст 2 сервиса: backend и frontend
5. Настрой переменные окружения
6. Получишь URL вида: `your-app.railway.app`

---

## 🌐 РЕШЕНИЕ #2: Render.com (Полностью бесплатно!)

**Плюсы:**
- **ПОЛНОСТЬЮ БЕСПЛАТНО**
- 0.5 GB RAM, shared CPU
- Автодеплой из GitHub
- HTTPS бесплатно

**Минусы:**
- Очень слабое железо (будет медленнее чем у тебя!)
- Засыпает после 15 минут неактивности
- **НЕ ПОДХОДИТ для твоей задачи** (слишком медленно)

---

## 💰 РЕШЕНИЕ #3: Платный хостинг (для скорости)

### Для достижения 2 минут нужно:
- **Минимум 16-32 ядра CPU** (AMD EPYC или Intel Xeon)
- 16+ GB RAM
- Желательно NVMe SSD

### Варианты хостинга:

#### A) Hetzner Cloud (Германия) - ЛУЧШАЯ ЦЕНА/КАЧЕСТВО
**CPX51** - €49.90/месяц (~$53)
- 16 vCPU (AMD EPYC)
- 32 GB RAM
- 360 GB NVMe SSD
- **Скорость: 50 минут аудио за ~2-3 минуты!**

**Как задеплоить:**
```bash
# 1. Создай VPS на hetzner.com
# 2. Подключись по SSH
ssh root@your-server-ip

# 3. Установи Docker и Docker Compose
apt update && apt install docker.io docker-compose -y

# 4. Склонируй репозиторий
git clone your-repo-url
cd your-repo

# 5. Создай docker-compose.yml (см. ниже)
# 6. Запусти
docker-compose up -d

# 7. Настрой Nginx и SSL (Let's Encrypt)
```

#### B) DigitalOcean - $96/месяц
**CPU-Optimized Droplet (16 vCPU)**
- 16 vCPU
- 32 GB RAM
- Хорошая поддержка

#### C) Linode (Akamai) - $96/месяц
**Dedicated 32GB**
- 16 CPU cores
- 32 GB RAM

#### D) Contabo - €30/месяц (~$32) - ДЕШЕВО!
**VPS L**
- 8 vCPU
- 30 GB RAM
- 800 GB SSD
- **Минус**: медленнее чем Hetzner, но дешевле

---

## 🔧 Docker Compose для продакшена

Создай `docker-compose.yml`:

```yaml
version: '3.8'

services:
  mongodb:
    image: mongo:latest
    restart: always
    volumes:
      - mongodb_data:/data/db
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: change_me_strong_password

  backend:
    build: ./backend
    restart: always
    ports:
      - "8001:8001"
    environment:
      - MONGO_URL=mongodb://admin:change_me_strong_password@mongodb:27017/
      - DB_NAME=tts_app
      - EMERGENT_LLM_KEY=your_key_here
    volumes:
      - audio_files:/app/audio_files
      - piper_models:/app/piper_models
    depends_on:
      - mongodb
    deploy:
      resources:
        limits:
          cpus: '15'  # Используй почти все ядра
          memory: 24G

  frontend:
    build: ./frontend
    restart: always
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_BACKEND_URL=https://your-domain.com/api

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend

volumes:
  mongodb_data:
  audio_files:
  piper_models:
```

---

## 🎯 МОЯ РЕКОМЕНДАЦИЯ

### Для бесплатного старта:
**Railway.app** - получишь 500 часов бесплатно, этого хватит на тестирование

### Для продакшена (2 минуты для 50 минут аудио):
**Hetzner Cloud CPX51** (€49.90/мес) или **Contabo VPS L** (€30/мес)

### Самый дешевый вариант:
**Contabo VPS M** (€15/мес) - 6 vCPU, 16 GB RAM
- Скорость будет ~5-7 минут для 50 минут аудио
- Не достигнет 2 минут, но в 3-5 раз быстрее твоего ноутбука

---

## 📝 Пошаговая инструкция деплоя на Hetzner

### 1. Создай аккаунт на hetzner.com
### 2. Купи сервер CPX51 (или меньше для теста)
### 3. Подключись по SSH:
```bash
ssh root@your-server-ip
```

### 4. Установи Docker:
```bash
apt update
apt install docker.io docker-compose git -y
```

### 5. Склонируй репозиторий:
```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo
```

### 6. Создай .env файлы:
```bash
# backend/.env
MONGO_URL=mongodb://admin:password@mongodb:27017/
DB_NAME=tts_app
EMERGENT_LLM_KEY=your_key

# frontend/.env
REACT_APP_BACKEND_URL=https://your-domain.com/api
```

### 7. Создай Dockerfile для backend:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Установи ffmpeg для pydub
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
```

### 8. Создай Dockerfile для frontend:
```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package.json yarn.lock ./
RUN yarn install

COPY . .

CMD ["yarn", "start"]
```

### 9. Запусти:
```bash
docker-compose up -d
```

### 10. Настрой домен и SSL:
- Купи домен на Namecheap (~$10/год)
- Направь A-запись на IP сервера
- Используй Certbot для SSL

---

## ⚡ АЛЬТЕРНАТИВА: Используй облачный TTS API

Если не хочешь платить за мощный сервер, используй облачные TTS API:

### Google Cloud Text-to-Speech
- **Цена**: $4 за 1 млн символов (WaveNet)
- **Скорость**: 50 минут аудио за 10-20 секунд!
- **Качество**: отличное
- **Бесплатно**: первые 4 млн символов/месяц (Standard voices)

### Как использовать:
1. Зайди на cloud.google.com
2. Создай проект и включи Text-to-Speech API
3. Получи API key
4. Замени Piper TTS на Google TTS в коде

### Примерная стоимость для твоего случая:
- 50 минут текста = ~45,000 символов
- 100 запросов в день = 4.5 млн символов/месяц
- **Стоимость: БЕСПЛАТНО** (в рамках лимита)

---

## 💡 ИТОГОВАЯ РЕКОМЕНДАЦИЯ

### Для минимальных затрат:
1. **Railway.app** для хостинга ($5 бесплатно, потом $10-15/мес)
2. **Google Cloud TTS** вместо Piper (бесплатно в лимите)
3. **Результат**: скорость 2-5 минут, почти бесплатно!

### Для твоего варианта (Piper TTS):
1. **Contabo VPS L** (€30/мес) - минимум для приемлемой скорости
2. Или **Hetzner CPX51** (€49.90/мес) - для целевой скорости 2 минуты

Выбирай что тебе больше подходит! Нужна помощь с деплоем - дай знать!
