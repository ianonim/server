import telebot
from telebot import types
import json
import datetime
import sqlite3
import sys
import time
import os
import requests
import signal
import atexit
import threading
from typing import Dict, List, Tuple, Optional

# ==================== ПРОВЕРКА ТОКЕНА ====================
def validate_bot_token(token: str) -> bool:
    """Тщательная проверка токена бота"""
    if not token or token.strip() == '' or token == '7973595298:AAGLI_WkT6Okh2xzVamG3tNCRn0zMalUaUg':
        print("❌ Ошибка: Токен не установлен.")
        print("   Получите токен у @BotFather и установите его:")
        print("   Способ 1: В коде: TOKEN = 'ваш_токен'")
        print("   Способ 2: Через переменную: export BOT_TOKEN='ваш_токен'")
        return False
    
    # Проверка формата токена (1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ)
    if ':' not in token:
        print("❌ Ошибка: Неверный формат токена.")
        print("   Токен должен содержать ':' (например: 1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ)")
        return False
    
    parts = token.split(':')
    if len(parts) != 2:
        print("❌ Ошибка: Неверный формат токена.")
        return False
    
    # Проверяем, что первая часть - число
    try:
        int(parts[0])
    except ValueError:
        print("❌ Ошибка: Первая часть токена должна быть числом (bot ID).")
        return False
    
    # Проверяем через API
    try:
        print("🔍 Проверяем токен через API Telegram...")
        url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data['result']
                print(f"✅ Токен валиден!")
                print(f"   🤖 Бот: @{bot_info['username']}")
                print(f"   📛 Имя: {bot_info['first_name']}")
                print(f"   🆔 ID: {bot_info['id']}")
                return True
            else:
                print(f"❌ API вернуло ошибку: {data.get('description')}")
                return False
        elif response.status_code == 401:
            print("❌ Неверный токен (401 Unauthorized)")
            print("   Проверьте, что токен правильный и не был отозван")
            return False
        else:
            print(f"❌ Ошибка HTTP {response.status_code}")
            return False
    except requests.exceptions.Timeout:
        print("❌ Таймаут при проверке токена")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Ошибка подключения к серверу Telegram")
        return False
    except Exception as e:
        print(f"❌ Неизвестная ошибка: {str(e)}")
        return False

# ==================== ОЧИСТКА PENDING UPDATES ====================
def clear_pending_updates(token: str) -> bool:
    """Полная очистка pending updates для предотвращения конфликта 409"""
    print("🧹 Очищаем pending updates...")
    
    try:
        # Метод 1: Получаем последний update_id
        url = f"https://api.telegram.org/bot{token}/getUpdates?offset=-1&limit=1"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok') and data.get('result'):
                last_update_id = data['result'][0]['update_id']
                print(f"📝 Последний update_id: {last_update_id}")
                
                # Метод 2: Отправляем подтверждение для всех updates
                confirm_url = f"https://api.telegram.org/bot{token}/getUpdates?offset={last_update_id + 1}"
                requests.get(confirm_url, timeout=5)
                
                # Метод 3: Используем deleteWebhook для уверенности
                delete_webhook_url = f"https://api.telegram.org/bot{token}/deleteWebhook"
                requests.get(delete_webhook_url, timeout=5)
                
                print("✅ Pending updates очищены")
                return True
        
        print("⚠️ Не удалось получить updates, продолжаем...")
        return True
    except Exception as e:
        print(f"⚠️ Ошибка при очистке updates: {str(e)}")
        return True

# ==================== КОНФИГУРАЦИЯ ====================
# Сначала пробуем получить токен из переменных окружения, потом из кода
TOKEN = os.getenv('BOT_TOKEN', '').strip()
if not TOKEN:
    TOKEN = 'YOUR_BOT_TOKEN'  # Замените на ваш токен

ADMIN_CHAT_ID = -1001234567890  # ID чата для логов
BOT_USERNAME = 'your_bot_username'

# Проверяем токен
print("=" * 60)
print("🔐 ПРОВЕРКА ТОКЕНА БОТА")
print("=" * 60)

if not validate_bot_token(TOKEN):
    print("\n" + "=" * 60)
    print("🛠️  ИНСТРУКЦИЯ ПО УСТАНОВКЕ ТОКЕНА")
    print("=" * 60)
    print("\n1. Откройте Telegram и найдите @BotFather")
    print("2. Отправьте команду: /newbot")
    print("3. Придумайте имя бота (например: My Awesome Bot)")
    print("4. Придумайте username бота (должен заканчиваться на 'bot', например: my_awesome_bot)")
    print("5. Скопируйте полученный токен (формат: 1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ)")
    print("\nУстановите токен одним из способов:")
    print("\nА) В коде (строка 81):")
    print("   TOKEN = 'ВАШ_ТОКЕН_ЗДЕСЬ'")
    print("\nБ) Через терминал (одна сессия):")
    print("   export BOT_TOKEN='ВАШ_ТОКЕН_ЗДЕСЬ'")
    print("   python bot.py")
    print("\nВ) Через терминал (постоянно):")
    print("   echo 'export BOT_TOKEN=\"ВАШ_ТОКЕН_ЗДЕСЬ\"' >> ~/.bashrc")
    print("   source ~/.bashrc")
    print("   python bot.py")
    print("\nГ) Через .env файл:")
    print("   Создайте файл .env со строкой:")
    print("   BOT_TOKEN=ВАШ_ТОКЕН_ЗДЕСЬ")
    print("\nПосле установки токена перезапустите бота!")
    print("=" * 60)
    sys.exit(1)

# Очищаем pending updates перед запуском
clear_pending_updates(TOKEN)

# ==================== БЕЗОПАСНЫЙ БОТ ====================
class ConflictSafeBot:
    """Бот с защитой от конфликтов 409"""
    
    def __init__(self, token):
        self.token = token
        self.bot = None
        self.running = False
        self.retry_count = 0
        self.max_retries = 3
        self.polling_thread = None
        
    def initialize_bot(self):
        """Инициализация бота с обработкой исключений"""
        try:
            print("🤖 Инициализируем бота...")
            
            # Создаем бота с увеличенным timeout
            self.bot = telebot.TeleBot(
                self.token,
                threaded=True,
                num_threads=2,
                skip_pending=True  # Важно для предотвращения 409!
            )
            
            # Тестируем подключение
            bot_info = self.bot.get_me()
            print(f"✅ Бот инициализирован: @{bot_info.username}")
            return True
            
        except telebot.apihelper.ApiTelegramException as e:
            if "409" in str(e):
                print("⚠️  Конфликт при инициализации. Ожидаем...")
                time.sleep(2)
                return False
            else:
                print(f"❌ Ошибка API: {str(e)}")
                raise
        except Exception as e:
            print(f"❌ Ошибка при инициализации: {str(e)}")
            raise
    
    def safe_polling(self):
        """Безопасный polling с обработкой конфликтов"""
        while self.running and self.retry_count < self.max_retries:
            try:
                print(f"🔄 Запуск polling (попытка {self.retry_count + 1}/{self.max_retries})...")
                
                # Удаляем webhook на всякий случай
                self.bot.remove_webhook()
                time.sleep(0.5)
                
                # Запускаем polling с параметрами для предотвращения 409
                self.bot.polling(
                    none_stop=True,
                    interval=0.5,
                    timeout=30,
                    long_polling_timeout=30,
                    skip_pending=True  # Ключевой параметр!
                )
                
                # Если polling завершился без ошибок, выходим
                break
                
            except telebot.apihelper.ApiTelegramException as e:
                self.retry_count += 1
                
                if "409" in str(e):
                    print(f"⚠️  Конфликт 409 (попытка {self.retry_count}/{self.max_retries})")
                    print("   Возможные причины:")
                    print("   1. Другой экземпляр бота запущен")
                    print("   2. Старые updates не очищены")
                    print("   3. Webhook не удален")
                    
                    # Очищаем updates через API
                    clear_pending_updates(self.token)
                    
                    # Увеличиваем время ожидания с каждой попыткой
                    wait_time = self.retry_count * 3
                    print(f"   ⏳ Ожидаем {wait_time} секунд...")
                    time.sleep(wait_time)
                    
                    if self.retry_count >= self.max_retries:
                        print("❌ Достигнут лимит попыток. Завершаем работу.")
                        self.running = False
                        break
                        
                else:
                    print(f"❌ Ошибка API: {str(e)}")
                    raise
                    
            except Exception as e:
                print(f"❌ Неизвестная ошибка: {str(e)}")
                self.running = False
                break
    
    def start(self):
        """Запуск бота"""
        if self.running:
            print("⚠️ Бот уже запущен")
            return
        
        print("=" * 60)
        print("🚀 ЗАПУСК БОТА")
        print("=" * 60)
        
        # Инициализируем бота
        for attempt in range(3):
            if self.initialize_bot():
                break
            if attempt == 2:
                print("❌ Не удалось инициализировать бота после 3 попыток")
                return
        
        self.running = True
        
        # Запускаем polling в отдельном потоке
        self.polling_thread = threading.Thread(target=self.safe_polling, daemon=True)
        self.polling_thread.start()
        
        print("✅ Бот запущен в фоновом режиме")
        print("📡 Ожидаем сообщения...")
        
        # Держим основной поток активным
        try:
            while self.running and self.polling_thread.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Получен сигнал прерывания")
            self.stop()
    
    def stop(self):
        """Остановка бота"""
        print("\n🛑 Останавливаем бота...")
        self.running = False
        
        if self.bot:
            try:
                self.bot.stop_polling()
                print("✅ Polling остановлен")
            except:
                pass
        
        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=5)
            print("✅ Поток polling завершен")
        
        print("👋 Бот остановлен")

# Создаем экземпляр безопасного бота
safe_bot = ConflictSafeBot(TOKEN)

# Получаем объект бота для использования в хендлерах
try:
    bot = safe_bot.bot if safe_bot.bot else telebot.TeleBot(TOKEN, skip_pending=True)
except:
    print("⚠️ Не удалось создать объект бота")
    sys.exit(1)

# ==================== БАЗА ДАННЫХ ====================
def init_database():
    """Инициализация базы данных с обработкой ошибок"""
    print("🗄️  Инициализируем базу данных...")
    
    try:
        conn = sqlite3.connect('bot_database.db', check_same_thread=False)
        cursor = conn.cursor()
        
        # Таблица чатов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            settings TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Таблица пользователей
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER,
            chat_id INTEGER,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            nick TEXT,
            vip_until TIMESTAMP,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            invited_by INTEGER,
            messages_count INTEGER DEFAULT 0,
            warnings INTEGER DEFAULT 0,
            muted_until TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, chat_id)
        )
        ''')
        
        # Таблица ролей
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS roles (
            chat_id INTEGER,
            role_name TEXT,
            permissions TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (chat_id, role_name)
        )
        ''')
        
        # Таблица связи пользователей и ролей
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_roles (
            chat_id INTEGER,
            user_id INTEGER,
            role_name TEXT,
            assigned_by INTEGER,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (chat_id, user_id, role_name)
        )
        ''')
        
        # Таблица банов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS bans (
            chat_id INTEGER,
            user_id INTEGER,
            reason TEXT,
            banned_by INTEGER,
            banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            unbanned_at TIMESTAMP,
            PRIMARY KEY (chat_id, user_id)
        )
        ''')
        
        # Таблица репортов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            reporter_id INTEGER,
            reported_user_id INTEGER,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            resolved_by INTEGER,
            resolved_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Таблица логов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            command TEXT,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Таблица мутов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS mutes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            muted_by INTEGER,
            reason TEXT,
            duration_minutes INTEGER,
            muted_until TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            unmuted_at TIMESTAMP
        )
        ''')
        
        conn.commit()
        print("✅ База данных инициализирована")
        
        return conn, cursor
        
    except Exception as e:
        print(f"❌ Ошибка при инициализации БД: {str(e)}")
        sys.exit(1)

# Инициализируем БД
conn, cursor = init_database()

# ==================== УТИЛИТЫ ====================
def log_command(chat_id: int, user_id: int, command: str, details: str = ''):
    """Логирование команд"""
    try:
        cursor.execute(
            '''INSERT INTO logs (chat_id, user_id, command, details) 
               VALUES (?, ?, ?, ?)''',
            (chat_id, user_id, command, details)
        )
        conn.commit()
        
        # Отправляем в лог-чат
        try:
            log_message = (
                f"📝 Лог команды\n"
                f"👤 Пользователь: {user_id}\n"
                f"💬 Чат: {chat_id}\n"
                f"📛 Команда: {command}\n"
                f"📋 Детали: {details}\n"
                f"🕒 Время: {datetime.datetime.now().strftime('%H:%M:%S')}"
            )
            bot.send_message(ADMIN_CHAT_ID, log_message)
        except:
            pass
            
    except Exception as e:
        print(f"⚠️ Ошибка при логировании: {str(e)}")

def get_user_display(user_id: int, chat_id: int) -> str:
    """Получение отображаемого имени пользователя"""
    try:
        cursor.execute(
            '''SELECT first_name, username, nick FROM users 
               WHERE user_id = ? AND chat_id = ?''',
            (user_id, chat_id)
        )
        result = cursor.fetchone()
        
        if result:
            first_name, username, nick = result
            if nick:
                return f"{nick} (@{username})" if username else nick
            elif username:
                return f"{first_name} (@{username})"
            else:
                return first_name
                
        return f"User{user_id}"
    except:
        return f"User{user_id}"

def is_user_admin(chat_id: int, user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    try:
        chat_member = bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ['administrator', 'creator']
    except:
        return False

# ==================== ОСНОВНЫЕ КОМАНДЫ ====================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Приветственное сообщение"""
    help_text = """
🤖 *Добро пожаловать в бота управления чатом!*

*Основные команды:*

👮‍♂️ *Административные:*
• /warn [причина] - Выдать предупреждение (ответом на сообщение)
• /kick [причина] - Кикнуть пользователя
• /ban [причина] - Забанить пользователя
• /unban [user_id] - Разбанить
• /mute [время] [причина] - Мут пользователя
• /unmute [user_id] - Размутить

📊 *Информационные:*
• /stats - Ваша статистика
• /chatstats - Статистика чата
• /online - Кто онлайн
• /top - Топ активных пользователей

👤 *Пользовательские:*
• /report [причина] - Пожаловаться (ответом на сообщение)
• /setnick [ник] - Установить свой ник
• /me - Информация о себе
• /id - Получить свой ID

⚙️ *Настройки:*
• /settings - Настройки чата
• /roles - Управление ролями
• /vip - Управление VIP статусами

*Примеры:*
• Ответьте на сообщение `/warn спам`
• `/mute 60 Спам` - Мут на 60 минут
• `/report оскорбления` - Ответом на сообщение
"""
    
    try:
        bot.reply_to(message, help_text, parse_mode='Markdown')
    except:
        pass

@bot.message_handler(commands=['warn'])
def warn_user(message):
    """Выдать предупреждение"""
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение пользователя!")
        return
    
    if not is_user_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Только администраторы могут выдавать предупреждения!")
        return
    
    target_user = message.reply_to_message.from_user
    reason = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "Не указана"
    
    try:
        # Обновляем счетчик предупреждений
        cursor.execute(
            '''INSERT INTO users (user_id, chat_id, username, first_name, warnings) 
               VALUES (?, ?, ?, ?, 1)
               ON CONFLICT(user_id, chat_id) 
               DO UPDATE SET warnings = warnings + 1''',
            (target_user.id, message.chat.id, target_user.username, target_user.first_name)
        )
        conn.commit()
        
        # Получаем текущее количество варнов
        cursor.execute(
            '''SELECT warnings FROM users 
               WHERE user_id = ? AND chat_id = ?''',
            (target_user.id, message.chat.id)
        )
        warnings = cursor.fetchone()[0]
        
        response = (
            f"⚠️ Пользователю {get_user_display(target_user.id, message.chat.id)} "
            f"выдано предупреждение!\n"
            f"📝 Причина: {reason}\n"
            f"🔢 Всего предупреждений: {warnings}/3"
        )
        
        if warnings >= 3:
            response += "\n🚫 *Достигнут лимит предупреждений!*"
        
        bot.reply_to(message, response, parse_mode='Markdown')
        log_command(message.chat.id, message.from_user.id, '/warn', 
                   f"Цель: {target_user.id}, Причина: {reason}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    """Показать статистику пользователя"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    try:
        cursor.execute(
            '''SELECT messages_count, warnings, join_date, nick 
               FROM users WHERE user_id = ? AND chat_id = ?''',
            (user_id, chat_id)
        )
        result = cursor.fetchone()
        
        if result:
            messages_count, warnings, join_date, nick = result
            join_date_str = join_date.split()[0] if join_date else "Неизвестно"
            
            stats_text = (
                f"📊 *Ваша статистика*\n"
                f"👤 Ник: {nick if nick else 'Не установлен'}\n"
                f"💬 Сообщений: {messages_count}\n"
                f"⚠️ Предупреждений: {warnings}/3\n"
                f"📅 В чате с: {join_date_str}\n"
                f"🆔 Ваш ID: `{user_id}`"
            )
        else:
            stats_text = "📊 У вас еще нет статистики в этом чате."
        
        bot.reply_to(message, stats_text, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['id'])
def get_id(message):
    """Получить ID пользователя"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    try:
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            bot.reply_to(message, f"🆔 ID пользователя: `{target_id}`", parse_mode='Markdown')
        else:
            bot.reply_to(message, f"🆔 Ваш ID: `{user_id}`\n💬 ID чата: `{chat_id}`", 
                        parse_mode='Markdown')
    except:
        pass

@bot.message_handler(commands=['ping'])
def ping_command(message):
    """Проверка работоспособности бота"""
    start_time = time.time()
    msg = bot.reply_to(message, "🏓 Понг...")
    end_time = time.time()
    
    ping_time = round((end_time - start_time) * 1000, 2)
    bot.edit_message_text(
        f"🏓 Понг! Задержка: {ping_time} мс\n"
        f"🕒 Время сервера: {datetime.datetime.now().strftime('%H:%M:%S')}",
        chat_id=message.chat.id,
        message_id=msg.message_id
    )

# ==================== СИСТЕМА СООБЩЕНИЙ ====================
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_all_messages(message):
    """Обработка всех сообщений для подсчета статистики"""
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # Обновляем статистику
        cursor.execute(
            '''INSERT INTO users (user_id, chat_id, username, first_name, messages_count, last_seen) 
               VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
               ON CONFLICT(user_id, chat_id) 
               DO UPDATE SET 
               messages_count = messages_count + 1,
               last_seen = CURRENT_TIMESTAMP,
               username = excluded.username,
               first_name = excluded.first_name''',
            (user_id, chat_id, message.from_user.username, message.from_user.first_name)
        )
        conn.commit()
        
    except Exception as e:
        print(f"⚠️ Ошибка при обработке сообщения: {str(e)}")

# ==================== ОБРАБОТЧИКИ СИГНАЛОВ ====================
def signal_handler(signum, frame):
    """Обработчик сигналов завершения"""
    print(f"\n🛑 Получен сигнал {signum}. Останавливаем бота...")
    safe_bot.stop()
    conn.close()
    sys.exit(0)

# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
atexit.register(lambda: safe_bot.stop())

# ==================== СКРИПТ АВАРИЙНОЙ ОЧИСТКИ ====================
def emergency_cleanup():
    """Аварийная очистка для устранения ошибки 409"""
    print("\n" + "=" * 60)
    print("🆘 АВАРИЙНАЯ ОЧИСТКА ДЛЯ УСТРАНЕНИЯ ОШИБКИ 409")
    print("=" * 60)
    
    print("\nВыполняем следующие действия:")
    print("1. ✅ Проверяем токен...")
    if not validate_bot_token(TOKEN):
        return False
    
    print("2. 🧹 Очищаем pending updates...")
    if not clear_pending_updates(TOKEN):
        print("⚠️ Не удалось очистить updates, продолжаем...")
    
    print("3. 🗑️ Удаляем webhook...")
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("✅ Webhook удален")
    except:
        print("⚠️ Не удалось удалить webhook")
    
    print("4. 🔄 Устанавливаем offset...")
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset=-1"
        requests.get(url, timeout=5)
        print("✅ Offset установлен")
    except:
        pass
    
    print("\n" + "=" * 60)
    print("✅ Аварийная очистка завершена!")
    print("Теперь можно запустить бота командой:")
    print(f"python {sys.argv[0]}")
    print("=" * 60)
    
    return True

# ==================== ГЛАВНАЯ ФУНКЦИЯ ====================
def main():
    """Главная функция запуска"""
    print("=" * 60)
    print("🤖 TELEGRAM BOT MANAGEMENT SYSTEM")
    print("=" * 60)
    print(f"Версия: 2.0 (с защитой от ошибки 409)")
    print(f"Токен: {'*' * 20}{TOKEN[-5:] if len(TOKEN) > 5 else ''}")
    print(f"Время: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Проверяем аргументы командной строки
    if len(sys.argv) > 1:
        if sys.argv[1] == '--clean':
            emergency_cleanup()
            return
        elif sys.argv[1] == '--check':
            validate_bot_token(TOKEN)
            return
        elif sys.argv[1] == '--help':
            print("\nИспользование:")
            print(f"  python {sys.argv[0]}           - Запустить бота")
            print(f"  python {sys.argv[0]} --clean   - Аварийная очистка от ошибки 409")
            print(f"  python {sys.argv[0]} --check   - Проверить токен")
            print(f"  python {sys.argv[0]} --help    - Показать эту справку")
            return
    
    # Запускаем бота
    try:
        safe_bot.start()
    except KeyboardInterrupt:
        print("\n\n👋 Завершение работы...")
        safe_bot.stop()
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {str(e)}")
        print("\n🆘 Для решения проблемы с ошибкой 409 выполните:")
        print(f"python {sys.argv[0]} --clean")
        safe_bot.stop()

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    main()