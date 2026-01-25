import telebot
from telebot import types
import json
import datetime
import sqlite3
from dotenv import load_dotenv
from typing import Dict, List, Tuple, Optional

# Конфигурация
TOKEN = 'bothelper'
ADMIN_CHAT_ID = -1003608057275  # ID чата для логов
BOT_USERNAME = 'your_bot_username'

bot = telebot.TeleBot(TOKEN)

# База данных
conn = sqlite3.connect('bot_database.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц
cursor.execute('''
CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY,
    settings TEXT,
    created_at TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
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
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS roles (
    chat_id INTEGER,
    role_name TEXT,
    permissions TEXT,
    PRIMARY KEY (chat_id, role_name)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS user_roles (
    chat_id INTEGER,
    user_id INTEGER,
    role_name TEXT,
    PRIMARY KEY (chat_id, user_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS bans (
    chat_id INTEGER,
    user_id INTEGER,
    reason TEXT,
    banned_by INTEGER,
    banned_at TIMESTAMP,
    PRIMARY KEY (chat_id, user_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    reporter_id INTEGER,
    reported_user_id INTEGER,
    reason TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    user_id INTEGER,
    command TEXT,
    details TEXT,
    timestamp TIMESTAMP
)
''')

conn.commit()

# Утилиты
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
    except:
        pass
    
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
        'report_cooldown': 300
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
    except:
        return False

# Система ролей
@bot.message_handler(commands=['addrole'])
def add_role(message):
    """Добавление роли"""
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
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['assignrole'])
def assign_role(message):
    """Назначение роли пользователю"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not has_permission(chat_id, user_id, 'assign_roles'):
        bot.reply_to(message, "❌ У вас нет прав для назначения ролей!")
        return
    
    try:
        _, target_user_id, role_name = message.text.split()
        target_user_id = int(target_user_id)
        
        cursor.execute(
            'INSERT OR REPLACE INTO user_roles (chat_id, user_id, role_name) VALUES (?, ?, ?)',
            (chat_id, target_user_id, role_name)
        )
        conn.commit()
        
        bot.reply_to(message, f"✅ Роль '{role_name}' назначена пользователю {target_user_id}")
        log_command(chat_id, user_id, '/assignrole', f"Пользователь: {target_user_id}, Роль: {role_name}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

# Система варнов
@bot.message_handler(commands=['warn'])
def warn_user(message):
    """Выдача предупреждения"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not has_permission(chat_id, user_id, 'warn'):
        bot.reply_to(message, "❌ У вас нет прав для выдачи предупреждений!")
        return
    
    try:
        if message.reply_to_message:
            target_user_id = message.reply_to_message.from_user.id
            reason = ' '.join(message.text.split()[1:]) if len(message.text.split()) > 1 else 'Не указана'
        else:
            _, target_user_id, *reason_parts = message.text.split()
            target_user_id = int(target_user_id)
            reason = ' '.join(reason_parts) if reason_parts else 'Не указана'
        
        user_info = get_user_info(target_user_id, chat_id)
        warnings = user_info.get('warnings', 0) + 1
        
        settings = get_chat_settings(chat_id)
        warn_limit = settings.get('warn_limit', 3)
        
        update_user_info(target_user_id, chat_id, warnings=warnings)
        
        warn_msg = (
            f"⚠️ Пользователь {target_user_id} получил предупреждение!\n"
            f"📝 Причина: {reason}\n"
            f"🔢 Количество варнов: {warnings}/{warn_limit}"
        )
        
        if warnings >= warn_limit:
            # Автоматический бан при превышении лимита
            cursor.execute(
                'INSERT OR REPLACE INTO bans (chat_id, user_id, reason, banned_by, banned_at) VALUES (?, ?, ?, ?, ?)',
                (chat_id, target_user_id, f'Автобан за {warnings} предупреждений', user_id, datetime.datetime.now())
            )
            conn.commit()
            
            try:
                bot.ban_chat_member(chat_id, target_user_id)
                warn_msg += "\n🚫 Пользователь забанен за превышение лимита предупреждений!"
            except:
                pass
        
        bot.reply_to(message, warn_msg)
        log_command(chat_id, user_id, '/warn', f"Цель: {target_user_id}, Причина: {reason}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

# Система киков
@bot.message_handler(commands=['kick'])
def kick_user(message):
    """Кик пользователя"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not has_permission(chat_id, user_id, 'kick'):
        bot.reply_to(message, "❌ У вас нет прав для кика!")
        return
    
    try:
        if message.reply_to_message:
            target_user_id = message.reply_to_message.from_user.id
            reason = ' '.join(message.text.split()[1:]) if len(message.text.split()) > 1 else 'Не указана'
        else:
            _, target_user_id, *reason_parts = message.text.split()
            target_user_id = int(target_user_id)
            reason = ' '.join(reason_parts) if reason_parts else 'Не указана'
        
        try:
            bot.ban_chat_member(chat_id, target_user_id)
            bot.unban_chat_member(chat_id, target_user_id)
            bot.reply_to(message, f"👢 Пользователь {target_user_id} кикнут!\n📝 Причина: {reason}")
            log_command(chat_id, user_id, '/kick', f"Цель: {target_user_id}, Причина: {reason}")
        except Exception as e:
            bot.reply_to(message, f"❌ Не удалось кикнуть пользователя: {str(e)}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

# Система банов
@bot.message_handler(commands=['ban'])
def ban_user(message):
    """Бан пользователя"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not has_permission(chat_id, user_id, 'ban'):
        bot.reply_to(message, "❌ У вас нет прав для бана!")
        return
    
    try:
        if message.reply_to_message:
            target_user_id = message.reply_to_message.from_user.id
            reason = ' '.join(message.text.split()[1:]) if len(message.text.split()) > 1 else 'Не указана'
        else:
            _, target_user_id, *reason_parts = message.text.split()
            target_user_id = int(target_user_id)
            reason = ' '.join(reason_parts) if reason_parts else 'Не указана'
        
        cursor.execute(
            'INSERT OR REPLACE INTO bans (chat_id, user_id, reason, banned_by, banned_at) VALUES (?, ?, ?, ?, ?)',
            (chat_id, target_user_id, reason, user_id, datetime.datetime.now())
        )
        conn.commit()
        
        try:
            bot.ban_chat_member(chat_id, target_user_id)
            bot.reply_to(message, f"🚫 Пользователь {target_user_id} забанен!\n📝 Причина: {reason}")
            log_command(chat_id, user_id, '/ban', f"Цель: {target_user_id}, Причина: {reason}")
        except Exception as e:
            bot.reply_to(message, f"❌ Не удалось забанить пользователя: {str(e)}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    """Разбан пользователя"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not has_permission(chat_id, user_id, 'unban'):
        bot.reply_to(message, "❌ У вас нет прав для разбана!")
        return
    
    try:
        _, target_user_id = message.text.split()
        target_user_id = int(target_user_id)
        
        cursor.execute(
            'DELETE FROM bans WHERE chat_id = ? AND user_id = ?',
            (chat_id, target_user_id)
        )
        conn.commit()
        
        try:
            bot.unban_chat_member(chat_id, target_user_id)
            bot.reply_to(message, f"✅ Пользователь {target_user_id} разбанен!")
            log_command(chat_id, user_id, '/unban', f"Цель: {target_user_id}")
        except Exception as e:
            bot.reply_to(message, f"❌ Не удалось разбанить пользователя: {str(e)}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

# Система репортов
@bot.message_handler(commands=['report'])
def report_user(message):
    """Отправка репорта"""
    chat_id = message.chat.id
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение пользователя, которого хотите пожаловаться!")
        return
    
    reporter_id = message.from_user.id
    reported_user_id = message.reply_to_message.from_user.id
    reason = ' '.join(message.text.split()[1:]) if len(message.text.split()) > 1 else 'Не указана'
    
    # Проверка кулдауна
    cursor.execute(
        '''SELECT created_at FROM reports 
        WHERE chat_id = ? AND reporter_id = ? 
        ORDER BY created_at DESC LIMIT 1''',
        (chat_id, reporter_id)
    )
    result = cursor.fetchone()
    
    if result:
        last_report = datetime.datetime.fromisoformat(result[0])
        settings = get_chat_settings(chat_id)
        cooldown = settings.get('report_cooldown', 300)
        
        if (datetime.datetime.now() - last_report).seconds < cooldown:
            bot.reply_to(message, f"⏳ Вы можете отправлять репорты раз в {cooldown//60} минут!")
            return
    
    # Сохранение репорта
    cursor.execute(
        '''INSERT INTO reports 
        (chat_id, reporter_id, reported_user_id, reason, created_at) 
        VALUES (?, ?, ?, ?, ?)''',
        (chat_id, reporter_id, reported_user_id, reason, datetime.datetime.now())
    )
    conn.commit()
    
    # Уведомление администраторов
    admins = []
    try:
        chat_admins = bot.get_chat_administrators(chat_id)
        for admin in chat_admins:
            if not admin.user.is_bot:
                admins.append(admin.user.id)
    except:
        pass
    
    report_msg = (
        f"🚨 Новый репорт!\n"
        f"👤 От: {reporter_id}\n"
        f"⚠️ На: {reported_user_id}\n"
        f"📝 Причина: {reason}\n"
        f"💬 Чат: {chat_id}"
    )
    
    for admin_id in admins:
        try:
            bot.send_message(admin_id, report_msg)
        except:
            pass
    
    bot.reply_to(message, "✅ Ваш репорт отправлен администраторам!")
    log_command(chat_id, reporter_id, '/report', f"На: {reported_user_id}, Причина: {reason}")

# Система VIP статусов
@bot.message_handler(commands=['vip'])
def set_vip(message):
    """Выдача VIP статуса"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not has_permission(chat_id, user_id, 'grant_vip'):
        bot.reply_to(message, "❌ У вас нет прав для выдачи VIP статуса!")
        return
    
    try:
        _, target_user_id, days = message.text.split()
        target_user_id = int(target_user_id)
        days = int(days)
        
        vip_until = datetime.datetime.now() + datetime.timedelta(days=days)
        
        update_user_info(target_user_id, chat_id, vip_until=vip_until)
        
        bot.reply_to(message, f"⭐ Пользователь {target_user_id} получил VIP статус на {days} дней!")
        log_command(chat_id, user_id, '/vip', f"Цель: {target_user_id}, Дней: {days}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

# Система ников
@bot.message_handler(commands=['setnick'])
def set_nick(message):
    """Установка ника"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    try:
        _, nick = message.text.split(maxsplit=1)
        
        if not has_permission(chat_id, user_id, 'change_nick'):
            bot.reply_to(message, "❌ У вас нет прав для изменения ника!")
            return
        
        update_user_info(user_id, chat_id, nick=nick)
        bot.reply_to(message, f"✅ Ваш ник изменен на: {nick}")
        log_command(chat_id, user_id, '/setnick', f"Ник: {nick}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

# Система статистики
@bot.message_handler(commands=['stats'])
def show_stats(message):
    """Показать статистику"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    user_info = get_user_info(user_id, chat_id)
    
    stats_text = (
        f"📊 Ваша статистика:\n"
        f"👤 Имя: {user_info.get('first_name', 'N/A')}\n"
        f"📛 Ник: {user_info.get('nick', 'Не установлен')}\n"
        f"📅 В чате с: {user_info.get('join_date', 'N/A')}\n"
        f"💬 Сообщений: {user_info.get('messages_count', 0)}\n"
        f"⚠️ Предупреждений: {user_info.get('warnings', 0)}\n"
    )
    
    if user_info.get('vip_until'):
        vip_until = datetime.datetime.fromisoformat(user_info['vip_until'])
        if vip_until > datetime.datetime.now():
            stats_text += f"⭐ VIP до: {vip_until.strftime('%Y-%m-%d %H:%M')}\n"
        else:
            stats_text += "⭐ VIP: Нет\n"
    else:
        stats_text += "⭐ VIP: Нет\n"
    
    if user_info.get('invited_by'):
        stats_text += f"🤝 Пригласил: {user_info['invited_by']}\n"
    
    bot.reply_to(message, stats_text)

# Система мутов
@bot.message_handler(commands=['mute'])
def mute_user(message):
    """Мут пользователя"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not has_permission(chat_id, user_id, 'mute'):
        bot.reply_to(message, "❌ У вас нет прав для мута!")
        return
    
    try:
        if message.reply_to_message:
            target_user_id = message.reply_to_message.from_user.id
            duration = message.text.split()[1] if len(message.text.split()) > 1 else '1h'
        else:
            _, target_user_id, duration = message.text.split()
            target_user_id = int(target_user_id)
        
        # Парсинг времени
        if duration.endswith('d'):
            hours = int(duration[:-1]) * 24
        elif duration.endswith('h'):
            hours = int(duration[:-1])
        elif duration.endswith('m'):
            hours = int(duration[:-1]) / 60
        else:
            hours = 1
        
        mute_until = datetime.datetime.now() + datetime.timedelta(hours=hours)
        
        update_user_info(target_user_id, chat_id, muted_until=mute_until)
        
        try:
            until_date = int((datetime.datetime.now() + datetime.timedelta(hours=hours)).timestamp())
            bot.restrict_chat_member(
                chat_id, 
                target_user_id,
                until_date=until_date,
                permissions=types.ChatPermissions(
                    can_send_messages=False,
                    can_send_media_messages=False,
                    can_send_polls=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False,
                    can_change_info=False,
                    can_invite_users=False,
                    can_pin_messages=False
                )
            )
            bot.reply_to(message, f"🔇 Пользователь {target_user_id} замьючен на {hours} часов!")
            log_command(chat_id, user_id, '/mute', f"Цель: {target_user_id}, Часов: {hours}")
        except Exception as e:
            bot.reply_to(message, f"❌ Не удалось замьютить: {str(e)}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['unmute'])
def unmute_user(message):
    """Размут пользователя"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not has_permission(chat_id, user_id, 'unmute'):
        bot.reply_to(message, "❌ У вас нет прав для размута!")
        return
    
    try:
        _, target_user_id = message.text.split()
        target_user_id = int(target_user_id)
        
        update_user_info(target_user_id, chat_id, muted_until=None)
        
        try:
            bot.restrict_chat_member(
                chat_id, 
                target_user_id,
                permissions=types.ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_polls=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                    can_change_info=False,
                    can_invite_users=False,
                    can_pin_messages=False
                )
            )
            bot.reply_to(message, f"🔊 Пользователь {target_user_id} размьючен!")
            log_command(chat_id, user_id, '/unmute', f"Цель: {target_user_id}")
        except Exception as e:
            bot.reply_to(message, f"❌ Не удалось размьютить: {str(e)}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

# Обработчик новых участников
@bot.message_handler(content_types=['new_chat_members'])
def new_member_handler(message):
    """Обработка новых участников"""
    chat_id = message.chat.id
    
    for new_member in message.new_chat_members:
        if new_member.id == bot.get_me().id:
            # Бот добавлен в чат
            settings = get_chat_settings(chat_id)
            save_chat_settings(chat_id, settings)
            bot.send_message(chat_id, "🤖 Бот активирован! Используйте /help для списка команд.")
        
        # Сохраняем информацию о пользователе
        update_user_info(
            new_member.id,
            chat_id,
            username=new_member.username,
            first_name=new_member.first_name,
            last_name=new_member.last_name,
            join_date=datetime.datetime.now()
        )
        
        # Проверяем, кто пригласил
        if message.from_user.id != new_member.id:
            update_user_info(new_member.id, chat_id, invited_by=message.from_user.id)

# Обработчик сообщений для подсчета активности
@bot.message_handler(func=lambda message: True)
def count_messages(message):
    """Подсчет сообщений пользователя"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    user_info = get_user_info(user_id, chat_id)
    messages_count = user_info.get('messages_count', 0) + 1
    
    update_user_info(
        user_id,
        chat_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        messages_count=messages_count
    )

# Команда помощи
@bot.message_handler(commands=['help', 'start'])
def help_command(message):
    """Справка по командам"""
    help_text = """
🤖 *Доступные команды:*

*Административные:*
• /addrole [название] [разрешения] - Создать роль
• /assignrole [user_id] [роль] - Назначить роль
• /warn [user_id] [причина] - Выдать предупреждение
• /kick [user_id] [причина] - Кикнуть пользователя
• /ban [user_id] [причина] - Забанить пользователя
• /unban [user_id] - Разбанить пользователя
• /mute [user_id] [время] - Замьютить пользователя
• /unmute [user_id] - Размьютить пользователя

*Для пользователей:*
• /report [причина] - Пожаловаться на пользователя (ответом на сообщение)
• /setnick [ник] - Установить ник
• /stats - Показать статистику
• /vip [user_id] [дни] - Выдать VIP статус

*Примеры:*
• `/warn 123456 Спам` - Выдать предупреждение
• `/mute 123456 2h` - Мут на 2 часа
• `/report Оскорбления` - Пожаловаться (ответом)
    """
    
    bot.reply_to(message, help_text, parse_mode='Markdown')

# Запуск бота
if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)