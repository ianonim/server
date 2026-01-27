import telebot
from telebot import types
import json
import datetime
import sqlite3
import sys
import time
import os
from typing import Dict, List, Tuple, Optional

# Проверка токена
def check_token_validity(token: str) -> bool:
    """Проверка валидности токена бота"""
    if not token or token == 'YOUR_BOT_TOKEN':
        print("❌ Ошибка: Токен не установлен. Замените 'YOUR_BOT_TOKEN' на ваш токен от @BotFather")
        return False
    
    # Проверка формата токена
    parts = token.split(':')
    if len(parts) != 2:
        print("❌ Ошибка: Неверный формат токена. Токен должен быть в формате '123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ'")
        return False
    
    try:
        # Попытка получить информацию о боте для проверки токена
        import requests
        response = requests.get(f'https://api.telegram.org/bot{token}/getMe')
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                print(f"✅ Токен валиден. Бот: @{data['result']['username']}")
                return True
            else:
                print(f"❌ Ошибка API: {data.get('description', 'Unknown error')}")
                return False
        else:
            print(f"❌ Ошибка сети: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка при проверке токена: {str(e)}")
        return False

# Конфигурация
TOKEN = os.getenv('7973595298:AAGLI_WkT6Okh2xzVamG3tNCRn0zMalUaUg', '7973595298:AAGLI_WkT6Okh2xzVamG3tNCRn0zMalUaUg')
ADMIN_CHAT_ID = --1003608057275  # ID чата для логов
BOT_USERNAME = '@Tresonline_bot'

# Проверяем токен перед запуском
if not check_token_validity(TOKEN):
    print("\n⚠️  Для продолжения выполните следующие шаги:")
    print("1. Создайте бота через @BotFather")
    print("2. Получите токен (формат: 123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ)")
    print("3. Установите токен одним из способов:")
    print("   - В коде: замените 'YOUR_BOT_TOKEN' на ваш токен")
    print("   - Через переменную окружения: export BOT_TOKEN='ваш_токен'")
    sys.exit(1)

# Инициализация бота с обработкой ошибок
class SafeBot:
    def __init__(self, token):
        self.bot = telebot.TeleBot(token, threaded=True)
        self.running = False
        self.last_update_id = 0
        self.polling_interval = 0.5
        
    def start(self):
        """Безопасный запуск бота с обработкой ошибок"""
        if self.running:
            print("⚠️ Бот уже запущен!")
            return
        
        self.running = True
        print("🤖 Бот запускается...")
        
        try:
            # Получаем информацию о боте
            bot_info = self.bot.get_me()
            print(f"✅ Бот @{bot_info.username} успешно запущен!")
            print(f"🆔 ID бота: {bot_info.id}")
            print(f"👤 Имя бота: {bot_info.first_name}")
            
            # Устанавливаем webhook в None для чистого запуска polling
            self.bot.remove_webhook()
            time.sleep(0.1)
            
            # Запускаем polling с обработкой ошибок
            self._start_polling()
            
        except Exception as e:
            print(f"❌ Критическая ошибка при запуске бота: {str(e)}")
            if "409" in str(e):
                print("\n⚠️  Ошибка 409: Обнаружено несколько запущенных экземпляров бота")
                print("   Решения:")
                print("   1. Убедитесь, что другой экземпляр бота не запущен")
                print("   2. Подождите 1-2 минуты перед повторным запуском")
                print("   3. Используйте параметр skip_pending=True при создании бота")
            self.running = False
            raise
    
    def _start_polling(self):
        """Запуск polling с обработкой ошибок"""
        print("🔄 Запуск polling...")
        
        try:
            # Пробуем использовать skip_pending для игнорирования старых updates
            self.bot.polling(none_stop=True, interval=self.polling_interval, timeout=20)
        except telebot.apihelper.ApiTelegramException as e:
            if "409" in str(e):
                print("\n⚠️  Ошибка 409: Конфликт polling запросов")
                print("   Пробуем перезапустить с новым offset...")
                self._handle_conflict()
            else:
                raise
        except Exception as e:
            print(f"❌ Ошибка в polling: {str(e)}")
            raise
    
    def _handle_conflict(self):
        """Обработка конфликта 409"""
        print("⏳ Ожидание 2 секунды...")
        time.sleep(2)
        
        try:
            # Пытаемся получить последние updates для правильного offset
            updates = self.bot.get_updates(offset=-1, timeout=10)
            if updates:
                self.last_update_id = updates[-1].update_id
                print(f"📝 Установлен последний update_id: {self.last_update_id}")
            
            # Перезапускаем polling с skip_pending
            print("🔄 Перезапуск polling...")
            self.bot.polling(
                none_stop=True, 
                interval=self.polling_interval, 
                timeout=20,
                skip_pending=True  # Игнорируем pending updates
            )
        except Exception as e:
            print(f"❌ Ошибка при перезапуске: {str(e)}")
            raise

# Создаем экземпляр безопасного бота
safe_bot = SafeBot(TOKEN)
bot = safe_bot.bot

# База данных
conn = sqlite3.connect('bot_database.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц (если они еще не созданы)
def init_database():
    """Инициализация базы данных"""
    tables = [
        '''CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            settings TEXT,
            created_at TIMESTAMP
        )''',
        
        '''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER,
            chat_id INTEGER,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            nick TEXT,
            vip_until TIMESTAMP,
            join_date TIMESTAMP,
            invited_by INTEGER,
            messages_count INTEGER DEFAULT 0,
            warnings INTEGER DEFAULT 0,
            muted_until TIMESTAMP,
            PRIMARY KEY (user_id, chat_id)
        )''',
        
        '''CREATE TABLE IF NOT EXISTS roles (
            chat_id INTEGER,
            role_name TEXT,
            permissions TEXT,
            PRIMARY KEY (chat_id, role_name)
        )''',
        
        '''CREATE TABLE IF NOT EXISTS user_roles (
            chat_id INTEGER,
            user_id INTEGER,
            role_name TEXT,
            PRIMARY KEY (chat_id, user_id)
        )''',
        
        '''CREATE TABLE IF NOT EXISTS bans (
            chat_id INTEGER,
            user_id INTEGER,
            reason TEXT,
            banned_by INTEGER,
            banned_at TIMESTAMP,
            PRIMARY KEY (chat_id, user_id)
        )''',
        
        '''CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            reporter_id INTEGER,
            reported_user_id INTEGER,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP
        )''',
        
        '''CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            command TEXT,
            details TEXT,
            timestamp TIMESTAMP
        )'''
    ]
    
    for table_sql in tables:
        try:
            cursor.execute(table_sql)
        except Exception as e:
            print(f"❌ Ошибка при создании таблицы: {str(e)}")
    
    conn.commit()
    print("✅ База данных инициализирована")

# Инициализируем БД
init_database()

# Утилиты (те же функции, что и в предыдущем коде)
def log_command(chat_id: int, user_id: int, command: str, details: str = ''):
    """Логирование команд"""
    cursor.execute(
        'INSERT INTO logs (chat_id, user_id, command, details, timestamp) VALUES (?, ?, ?, ?, ?)',
        (chat_id, user_id, command, details, datetime.datetime.now())
    )
    
    # Отправка в лог-чат
    try:
        user_info = get_user_info(user_id, chat_id)
        log_text = (
            f"📝 Лог команды\n"
            f"👤 Пользователь: {user_info['first_name']} (@{user_info.get('username', 'N/A')})\n"
            f"🆔 ID: {user_id}\n"
            f"💬 Чат: {chat_id}\n"
            f"📛 Команда: {command}\n"
            f"📋 Детали: {details}"
        )
        bot.send_message(ADMIN_CHAT_ID, log_text)
    except Exception as e:
        print(f"⚠️ Ошибка при отправке лога: {str(e)}")
    
    conn.commit()

def get_chat_settings(chat_id: int) -> Dict:
    """Получение настроек чата"""
    cursor.execute('SELECT settings FROM chats WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()
    if result:
        return json.loads(result[0])
    return {
        'warn_limit': 3,
        'mute_durations': [300, 900, 3600],  # 5 мин, 15 мин, 1 час
        'vip_days': 30,
        'report_cooldown': 300,
        'welcome_message': 'Добро пожаловать в чат!'
    }

def save_chat_settings(chat_id: int, settings: Dict):
    """Сохранение настроек чата"""
    cursor.execute('SELECT chat_id FROM chats WHERE chat_id = ?', (chat_id,))
    if not cursor.fetchone():
        cursor.execute(
            'INSERT INTO chats (chat_id, settings, created_at) VALUES (?, ?, ?)',
            (chat_id, json.dumps(settings), datetime.datetime.now())
        )
    else:
        cursor.execute(
            'UPDATE chats SET settings = ? WHERE chat_id = ?',
            (json.dumps(settings), chat_id)
        )
    conn.commit()

def get_user_info(user_id: int, chat_id: int) -> Dict:
    """Получение информации о пользователе"""
    cursor.execute(
        '''SELECT username, first_name, last_name, nick, vip_until, 
           join_date, invited_by, messages_count, warnings, muted_until 
           FROM users WHERE user_id = ? AND chat_id = ?''',
        (user_id, chat_id)
    )
    result = cursor.fetchone()
    if result:
        return {
            'username': result[0],
            'first_name': result[1],
            'last_name': result[2],
            'nick': result[3],
            'vip_until': result[4],
            'join_date': result[5],
            'invited_by': result[6],
            'messages_count': result[7],
            'warnings': result[8],
            'muted_until': result[9]
        }
    return {}

def update_user_info(user_id: int, chat_id: int, **kwargs):
    """Обновление информации о пользователе"""
    # Проверяем существование записи
    cursor.execute(
        'SELECT user_id FROM users WHERE user_id = ? AND chat_id = ?',
        (user_id, chat_id)
    )
    
    if not cursor.fetchone():
        # Создаем новую запись
        cursor.execute(
            '''INSERT INTO users 
            (user_id, chat_id, username, first_name, last_name, nick, 
             vip_until, join_date, invited_by, messages_count, warnings, muted_until) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (user_id, chat_id, 
             kwargs.get('username', ''), 
             kwargs.get('first_name', ''),
             kwargs.get('last_name', ''),
             kwargs.get('nick', None),
             kwargs.get('vip_until', None),
             kwargs.get('join_date', datetime.datetime.now()),
             kwargs.get('invited_by', None),
             kwargs.get('messages_count', 0),
             kwargs.get('warnings', 0),
             kwargs.get('muted_until', None))
        )
    else:
        # Обновляем существующую запись
        update_fields = []
        values = []
        
        for key, value in kwargs.items():
            if value is not None:
                update_fields.append(f"{key} = ?")
                values.append(value)
        
        if update_fields:
            values.extend([user_id, chat_id])
            cursor.execute(
                f'UPDATE users SET {", ".join(update_fields)} WHERE user_id = ? AND chat_id = ?',
                values
            )
    
    conn.commit()

def has_permission(chat_id: int, user_id: int, permission: str) -> bool:
    """Проверка прав пользователя"""
    # Получаем роли пользователя
    cursor.execute(
        'SELECT role_name FROM user_roles WHERE chat_id = ? AND user_id = ?',
        (chat_id, user_id)
    )
    user_roles = cursor.fetchall()
    
    # Проверяем права для каждой роли
    for role_tuple in user_roles:
        role_name = role_tuple[0]
        cursor.execute(
            'SELECT permissions FROM roles WHERE chat_id = ? AND role_name = ?',
            (chat_id, role_name)
        )
        result = cursor.fetchone()
        if result:
            permissions = json.loads(result[0])
            if permission in permissions and permissions[permission]:
                return True
    
    return False

def is_admin(chat_id: int, user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except Exception as e:
        print(f"⚠️ Ошибка при проверке админа: {str(e)}")
        return False

# Система ролей (команды остаются те же, но с обработкой ошибок)
@bot.message_handler(commands=['addrole'])
def add_role(message):
    """Добавление роли"""
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        
        if not is_admin(chat_id, user_id):
            bot.reply_to(message, "❌ Только администраторы могут создавать роли!")
            return
        
        try:
            _, role_name, *permissions = message.text.split()
            
            # Создаем словарь разрешений
            perm_dict = {}
            for perm in permissions:
                if '=' in perm:
                    key, value = perm.split('=')
                    perm_dict[key] = value.lower() == 'true'
            
            cursor.execute(
                'INSERT OR REPLACE INTO roles (chat_id, role_name, permissions) VALUES (?, ?, ?)',
                (chat_id, role_name, json.dumps(perm_dict))
            )
            conn.commit()
            
            bot.reply_to(message, f"✅ Роль '{role_name}' создана!")
            log_command(chat_id, user_id, '/addrole', f"Роль: {role_name}")
        except ValueError:
            bot.reply_to(message, "❌ Использование: /addrole [название] [perm1=true/false] [perm2=true/false]")
        except Exception as e:
            bot.reply_to(message, f"❌ Ошибка: {str(e)}")
    except Exception as e:
        print(f"⚠️ Ошибка в add_role: {str(e)}")

# ... остальные функции команд остаются такими же как в предыдущем коде ...
# (warn_user, kick_user, ban_user, report_user, set_vip, set_nick, show_stats, mute_user, etc.)

# Для экономии места, остальные функции команд остаются без изменений
# Вы можете скопировать их из предыдущего кода

# Команда для проверки статуса бота
@bot.message_handler(commands=['status'])
def bot_status(message):
    """Проверка статуса бота"""
    try:
        status_text = (
            f"🤖 *Статус бота*\n"
            f"✅ Бот работает\n"
            f"📊 Всего чатов в БД: {cursor.execute('SELECT COUNT(*) FROM chats').fetchone()[0]}\n"
            f"👤 Всего пользователей: {cursor.execute('SELECT COUNT(*) FROM users').fetchone()[0]}\n"
            f"🕒 Время сервера: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        bot.reply_to(message, status_text, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

# Команда для очистки старых логов
@bot.message_handler(commands=['clearlogs'])
def clear_old_logs(message):
    """Очистка старых логов (только для админов)"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not is_admin(chat_id, user_id):
        bot.reply_to(message, "❌ Только администраторы могут очищать логи!")
        return
    
    try:
        # Удаляем логи старше 30 дней
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=30)
        cursor.execute(
            'DELETE FROM logs WHERE timestamp < ?',
            (cutoff_date,)
        )
        deleted_count = cursor.rowcount
        conn.commit()
        
        bot.reply_to(message, f"✅ Удалено {deleted_count} старых логов")
        log_command(chat_id, user_id, '/clearlogs', f"Удалено: {deleted_count}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

# Обработчик ошибок для всех команд
def safe_command_handler(func):
    """Декоратор для безопасной обработки команд"""
    def wrapper(message):
        try:
            return func(message)
        except Exception as e:
            print(f"⚠️ Ошибка в команде {func.__name__}: {str(e)}")
            try:
                bot.reply_to(message, "❌ Произошла ошибка при выполнении команды")
            except:
                pass
    return wrapper

# Применяем декоратор ко всем командам
for handler in bot.message_handlers:
    handler['function'] = safe_command_handler(handler['function'])

# Функция для плавной остановки бота
import signal
import atexit

def shutdown_handler(signum=None, frame=None):
    """Обработчик завершения работы"""
    print("\n🛑 Завершение работы бота...")
    
    # Закрываем соединение с БД
    conn.close()
    print("✅ Соединение с БД закрыто")
    
    # Останавливаем polling
    safe_bot.running = False
    bot.stop_polling()
    
    print("✅ Бот остановлен")
    sys.exit(0)

# Регистрируем обработчики завершения
signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)
atexit.register(shutdown_handler)

# Основная функция запуска
def main():
    """Основная функция запуска бота"""
    print("=" * 50)
    print("🤖 Telegram Bot Management System")
    print("=" * 50)
    
    try:
        # Запускаем безопасный бот
        safe_bot.start()
    except KeyboardInterrupt:
        print("\n\n👋 Завершение работы по запросу пользователя")
        shutdown_handler()
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {str(e)}")
        print("\n🔧 Возможные решения:")
        print("1. Проверьте токен бота")
        print("2. Убедитесь, что бот не запущен в другом месте")
        print("3. Проверьте подключение к интернету")
        print("4. Очистите pending updates командой: ")
        print("   curl -X POST https://api.telegram.org/bot{YOUR_TOKEN}/getUpdates?offset=-1")
        sys.exit(1)

# Запуск
if __name__ == '__main__':
    main()