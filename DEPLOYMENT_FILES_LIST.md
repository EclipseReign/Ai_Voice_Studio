# 📦 Список файлов для развертывания

Все необходимые файлы для развертывания приложения на локальной машине.

## 📚 Документация (5 файлов)

### 1. **README_RU.md**
   - 📝 Основной README на русском языке
   - Краткий обзор проекта
   - Быстрый старт
   - Основные возможности

### 2. **LOCAL_DEPLOYMENT_GUIDE.md**
   - 📖 Полный подробный гайд по развертыванию
   - Системные требования
   - Пошаговая установка
   - Устранение неполадок
   - Настройка для производства
   - **ГЛАВНЫЙ ДОКУМЕНТ** - читайте в первую очередь

### 3. **QUICK_START.md**
   - ⚡ Быстрая шпаргалка для опытных разработчиков
   - Минимальный набор команд
   - Для тех, кто знает что делает

### 4. **ENV_CONFIG_EXAMPLES.md**
   - 🔐 Примеры конфигурационных файлов
   - Как получить API ключи
   - Безопасность
   - Настройки для production
   
### 5. **DEPLOYMENT_FILES_LIST.md** (этот файл)
   - 📋 Список всех файлов
   - Описание каждого файла

---

## 🚀 Скрипты запуска (6 файлов)

### Для macOS/Linux:

#### 1. **setup.sh**
   ```bash
   ./setup.sh
   ```
   - Автоматическая установка всех зависимостей
   - Создание виртуальных окружений
   - Проверка системных требований
   - Создание .env файлов с примерами
   - **ЗАПУСТИТЕ ПЕРВЫМ** после клонирования

#### 2. **start-backend.sh**
   ```bash
   ./start-backend.sh
   ```
   - Запуск Backend сервера (FastAPI)
   - Автоматическая проверка MongoDB
   - Активация виртуального окружения
   - Запуск на порту 8001

#### 3. **start-frontend.sh**
   ```bash
   ./start-frontend.sh
   ```
   - Запуск Frontend приложения (React)
   - Проверка доступности Backend
   - Автоматическое открытие браузера
   - Запуск на порту 3000

### Для Windows:

#### 4. **setup.bat**
   ```batch
   setup.bat
   ```
   - Аналог setup.sh для Windows
   - Автоматическая установка
   - Проверка зависимостей

#### 5. **start-backend.bat**
   ```batch
   start-backend.bat
   ```
   - Запуск Backend на Windows
   - Проверки и активация venv

#### 6. **start-frontend.bat**
   ```batch
   start-frontend.bat
   ```
   - Запуск Frontend на Windows
   - Проверка зависимостей

---

## 📁 Структура проекта

```
.
├── 📚 ДОКУМЕНТАЦИЯ
│   ├── README_RU.md                    # Основной README
│   ├── LOCAL_DEPLOYMENT_GUIDE.md       # Полный гайд ⭐
│   ├── QUICK_START.md                  # Быстрый старт
│   ├── ENV_CONFIG_EXAMPLES.md          # Примеры .env
│   └── DEPLOYMENT_FILES_LIST.md        # Этот файл
│
├── 🚀 СКРИПТЫ ЗАПУСКА
│   ├── setup.sh                        # Установка (macOS/Linux)
│   ├── setup.bat                       # Установка (Windows)
│   ├── start-backend.sh                # Backend (macOS/Linux)
│   ├── start-backend.bat               # Backend (Windows)
│   ├── start-frontend.sh               # Frontend (macOS/Linux)
│   └── start-frontend.bat              # Frontend (Windows)
│
├── 🔧 BACKEND
│   ├── server.py                       # Главный FastAPI сервер
│   ├── requirements.txt                # Python зависимости
│   ├── .env                            # Создайте по примеру ⚠️
│   └── venv/                           # Создается автоматически
│
├── ⚛️ FRONTEND
│   ├── src/
│   │   ├── App.js
│   │   └── pages/HomePage.js
│   ├── package.json                    # Node.js зависимости
│   ├── .env                            # Создайте по примеру ⚠️
│   └── node_modules/                   # Создается автоматически
│
└── 🗄️ ДАННЫЕ
    ├── audio_files/                    # Генерированные аудио
    └── piper_models/                   # Модели TTS
```

---

## ⚡ Быстрый старт (3 шага)

### Шаг 1: Установка
```bash
# macOS/Linux
./setup.sh

# Windows
setup.bat
```

### Шаг 2: Добавьте API ключ
Отредактируйте `backend/.env`:
```env
EMERGENT_LLM_KEY=ваш_ключ_здесь
```

### Шаг 3: Запустите
```bash
# Терминал 1
./start-backend.sh   # или start-backend.bat

# Терминал 2
./start-frontend.sh  # или start-frontend.bat
```

Откройте: **http://localhost:3000** 🎉

---

## 📋 Чек-лист установки

### Перед началом:
- [ ] Python 3.9+ установлен
- [ ] Node.js 16+ установлен
- [ ] MongoDB установлен и запущен
- [ ] FFmpeg установлен
- [ ] Git установлен

### Установка:
- [ ] Клонирован репозиторий
- [ ] Запущен `setup.sh` (или `setup.bat`)
- [ ] Создан `backend/.env` с API ключом
- [ ] Создан `frontend/.env`

### Запуск:
- [ ] MongoDB запущен
- [ ] Backend запущен (`./start-backend.sh`)
- [ ] Frontend запущен (`./start-frontend.sh`)
- [ ] Открыт http://localhost:3000
- [ ] Протестирована генерация текста
- [ ] Протестирована озвучка

---

## 🔍 Какой файл читать?

### Новичок в разработке?
1. ✅ Читайте **README_RU.md** - краткий обзор
2. ✅ Читайте **LOCAL_DEPLOYMENT_GUIDE.md** - подробные инструкции
3. ✅ Используйте скрипты `setup.sh` и `start-*.sh`

### Опытный разработчик?
1. ✅ Читайте **QUICK_START.md** - быстрые команды
2. ✅ Смотрите **ENV_CONFIG_EXAMPLES.md** - примеры конфигов
3. ✅ Запускайте напрямую без скриптов

### Нужна конфигурация?
1. ✅ Читайте **ENV_CONFIG_EXAMPLES.md**
2. ✅ Копируйте примеры .env файлов
3. ✅ Получите API ключи по инструкциям

### Возникли проблемы?
1. ✅ Раздел "Устранение неполадок" в **LOCAL_DEPLOYMENT_GUIDE.md**
2. ✅ Проверьте логи backend и frontend
3. ✅ Откройте issue на GitHub

---

## 📦 Что делать с этими файлами?

### 1. Закоммитьте в Git

```bash
git add README_RU.md
git add LOCAL_DEPLOYMENT_GUIDE.md
git add QUICK_START.md
git add ENV_CONFIG_EXAMPLES.md
git add DEPLOYMENT_FILES_LIST.md
git add setup.sh start-backend.sh start-frontend.sh
git add setup.bat start-backend.bat start-frontend.bat
git commit -m "Add deployment documentation and scripts"
git push origin main
```

### 2. Проверьте что .env НЕ в git

```bash
# Убедитесь что .env файлы в .gitignore
cat .gitignore | grep ".env"

# Должно быть: *.env
```

### 3. Сделайте скрипты исполняемыми (macOS/Linux)

```bash
chmod +x setup.sh
chmod +x start-backend.sh
chmod +x start-frontend.sh
```

---

## 🎯 Рекомендуемый порядок чтения

### Для первого раза:
1. **README_RU.md** (5 минут) - понять что это за проект
2. **LOCAL_DEPLOYMENT_GUIDE.md** (20 минут) - полная установка
3. **ENV_CONFIG_EXAMPLES.md** (10 минут) - настроить конфигурацию
4. Запустить `setup.sh`
5. Добавить API ключ в `backend/.env`
6. Запустить `start-backend.sh` и `start-frontend.sh`
7. Протестировать на http://localhost:3000

### Для опытных:
1. **QUICK_START.md** (2 минуты)
2. Запустить команды из QUICK_START
3. Готово! ✅

---

## 💡 Полезные ссылки

- **API документация Backend**: http://localhost:8001/docs (после запуска)
- **Frontend**: http://localhost:3000 (после запуска)
- **MongoDB**: mongodb://localhost:27017

---

## 🆘 Помощь

Если что-то не работает:

1. 📖 Прочитайте раздел "Устранение неполадок" в **LOCAL_DEPLOYMENT_GUIDE.md**
2. 🔍 Проверьте логи:
   - Backend: в терминале где запущен `start-backend.sh`
   - Frontend: в терминале где запущен `start-frontend.sh`
   - Browser: F12 → Console
3. ✅ Проверьте чек-лист выше
4. 💬 Откройте issue на GitHub

---

## ✨ Готовы начать?

Выберите ваш путь:

### 🚀 Быстрый путь (опытные)
```bash
./setup.sh
# Добавьте API ключ в backend/.env
./start-backend.sh &
./start-frontend.sh
```

### 📚 Подробный путь (новички)
1. Откройте **LOCAL_DEPLOYMENT_GUIDE.md**
2. Следуйте инструкциям шаг за шагом
3. Все получится! 💪

---

**Успехов в развертывании! 🎉**
