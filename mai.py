import telebot
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

# Загрузка токена из переменных окружения (рекомендуется)
TOKEN = os.getenv('bothelper')
    # Если не найден в .env, попробуем взять из кода (не рекомендуется для продакшена)
 # Замените на ваш реальный токен

# ID чата для логов (убедитесь, что бот добавлен в этот чат как администратор)
LOG_CHAT_ID = -1003608057275  # ← замените на реальный ID вашего чата
ADMIN_ID = 7614638047  # ← замените на ваш реальный ID

# Инициализация бота
bot = telebot.TeleBot(TOKEN)

# Словарь для активных сессий (не путать с постоянным хранилищем)
active_users = {}

def get_user_identifier(user):
    """Формирует читаемый идентификатор: @username или Имя Фамилия"""
    if user.username:
        return f"@{user.username}"
    elif user.last_name:
        return f"{user.first_name} {user.last_name}"
    else:
        return user.first_name

def send_log_to_chat(message, command, response_text):
    """Отправляет лог в указанный чат (LOG_CHAT_ID)"""
    try:
        user_tag = get_user_identifier(message.from_user)
        chat_info = f"Исходный чат: {message.chat.type} (ID: {message.chat.id})"
        if message.chat.title:
            chat_info += f" — «{message.chat.title}»"

        log_msg = (
            f"📊 **ЛОГ ВЫПОЛНЕНИЯ КОМАНДЫ**\n\n"
            f"🔹 Команда: `/{command}`\n"
            f"🔹 Ответ бота: `{response_text[:100]}...`\n"
            f"🔹 Пользователь: {user_tag} (ID: {message.from_user.id})\n"
            f"{chat_info}\n"
            f"🔹 Дата: `{datetime.fromtimestamp(message.date).strftime('%Y-%m-%d %H:%M:%S')}`"
        )
        bot.send_message(LOG_CHAT_ID, log_msg, parse_mode='Markdown')
    except Exception as e:
        print(f"[ОШИБКА] Не удалось отправить лог: {e}")

# Инициализация структуры данных
def init_data_structure():
    return {
        'chats': {},  # {chat_id: {users: {}, settings: {}}}
        'reports': []
    }

# Загрузка/сохранение данных
def load_data():
    try:
        with open('bot_data.json', 'r', encoding='utf-8') as f:
            loaded = json.load(f)
            # Проверяем структуру
            if 'chats' not in loaded:
                loaded['chats'] = {}
            if 'reports' not in loaded:
                loaded['reports'] = []
            return loaded
    except FileNotFoundError:
        return init_data_structure()
    except json.JSONDecodeError:
        print("Ошибка чтения JSON, создаю новую структуру данных")
        return init_data_structure()

def save_data():
    try:
        with open('bot_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ОШИБКА] Не удалось сохранить данные: {e}")

# Загружаем данные при старте
data = load_data()

# Вспомогательные функции
def log_action(chat_id, user_id, action, details=''):
    """Логирование действий в LOG_CHAT_ID"""
    try:
        msg = (f'[LOG] Чат {chat_id}\n'
               f'Пользователь {user_id} выполнил: {action}\n'
               f'Детали: {details}\n'
               f'Время: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        bot.send_message(LOG_CHAT_ID, msg)
    except Exception as e:
        print(f"[ОШИБКА] Не удалось отправить лог действия: {e}")

def get_user_info(chat_id, user_id):
    """Получение информации о пользователе с созданием записи при необходимости"""
    if chat_id not in data['chats']:
        data['chats'][chat_id] = {'users': {}, 'settings': {}}
    
    chat_data = data['chats'][chat_id]
    if 'users' not in chat_data:
        chat_data['users'] = {}
    
    if str(user_id) not in chat_data['users']:
        chat_data['users'][str(user_id)] = {
            'role': 'user',
            'warns': 0,
            'vip': False,
            'nick': None,
            'join_time': time.time(),
            'inviter_id': None,
            'muted_until': None
        }
        save_data()  # Сохраняем при создании нового пользователя
    
    return chat_data['users'][str(user_id)]

def is_admin(chat_id, user_id):
    """Проверка, является ли пользователь администратором"""
    try:
        if user_id == ADMIN_ID:
            return True
        
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except Exception as e:
        print(f"[ОШИБКА] Проверка прав администратора: {e}")
        return False

# Команды
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    info = get_user_info(chat_id, user_id)
    response = f'Привет! Твой статус: {info["role"]}. VIP: {info["vip"]}'
    bot.reply_to(message, response)
    send_log_to_chat(message, 'start', response)

@bot.message_handler(commands=['stats'])
def stats(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    info = get_user_info(chat_id, user_id)
    joined = datetime.fromtimestamp(info['join_time']).strftime('%Y-%m-%d %H:%M:%S')
    inviter = info['inviter_id'] if info['inviter_id'] else 'неизвестно'
    muted_until = 'нет'
    if info['muted_until']:
        muted_until = datetime.fromtimestamp(info['muted_until']).strftime('%Y-%m-%d %H:%M:%S')
    
    stats_msg = (f'Статистика пользователя {user_id}:\n'
                 f'Роль: {info["role"]}\n'
                 f'VIP: {info["vip"]}\n'
                 f'Ник: {info["nick"] or "не установлен"}\n'
                 f'Варны: {info["warns"]}\n'
                 f'Время вступления: {joined}\n'
                 f'Пригласил: {inviter}\n'
                 f'Замутён до: {muted_until}')
    bot.reply_to(message, stats_msg)
    send_log_to_chat(message, 'stats', f'Показана статистика для {user_id}')

@bot.message_handler(commands=['setrole'])
def set_role(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not is_admin(chat_id, user_id):
        response = 'Только админы могут менять роли.'
        bot.reply_to(message, response)
        send_log_to_chat(message, 'setrole', 'Ошибка: нет прав')
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            response = 'Использование: /setrole <user_id> <role>'
            bot.reply_to(message, response)
            return
        
        target_id = int(parts[1])
        role = parts[2]
        
        info = get_user_info(chat_id, target_id)
        info['role'] = role
        save_data()
        
        response = f'Роль пользователя {target_id} изменена на {role}.'
        bot.reply_to(message, response)
        log_action(chat_id, user_id, 'setrole', f'user={target_id}, role={role}')
        send_log_to_chat(message, 'setrole', response)
        
    except (IndexError, ValueError) as e:
        response = 'Использование: /setrole <user_id> <role>'
        bot.reply_to(message, response)

@bot.message_handler(commands=['warn'])
def warn(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not is_admin(chat_id, user_id):
        response = 'Только админы могут выдавать варны.'
        bot.reply_to(message, response)
        send_log_to_chat(message, 'warn', 'Ошибка: нет прав')
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            response = 'Использование: /warn <user_id>'
            bot.reply_to(message, response)
            return
        
        target_id = int(parts[1])
        info = get_user_info(chat_id, target_id)
        info['warns'] += 1
        save_data()
        
        response = f'Пользователь {target_id} получил варн (№{info["warns"]}).'
        bot.reply_to(message, response)
        log_action(chat_id, user_id, 'warn', f'user={target_id}, warns={info["warns"]}')
        send_log_to_chat(message, 'warn', response)
        
        if info['warns'] >= 3:
            try:
                bot.kick_chat_member(chat_id, target_id, until_date=int(time.time()) + 60)
                bot.send_message(chat_id, f'Пользователь {target_id} кикнут за 3 варна.')
            except Exception as e:
                bot.send_message(chat_id, f'Не удалось кикнуть пользователя {target_id}: {e}')
                
    except (IndexError, ValueError) as e:
        response = 'Использование: /warn <user_id>'
        bot.reply_to(message, response)

@bot.message_handler(commands=['kick'])
def kick(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not is_admin(chat_id, user_id):
        response = 'Только админы могут кикать.'
        bot.reply_to(message, response)
        send_log_to_chat(message, 'kick', 'Ошибка: нет прав')
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            response = 'Использование: /kick <user_id>'
            bot.reply_to(message, response)
            return
        
        target_id = int(parts[1])
        # Кик на 1 минуту (можно будет вернуться)
        bot.kick_chat_member(chat_id, target_id, until_date=int(time.time()) + 60)
        
        response = f'Пользователь {target_id} кикнут.'
        bot.reply_to(message, response)
        log_action(chat_id, user_id, 'kick', f'user={target_id}')
        send_log_to_chat(message, 'kick', response)
        
    except (IndexError, ValueError) as e:
        response = 'Использование: /kick <user_id>'
        bot.reply_to(message, response)
    except Exception as e:
        response = f'Ошибка при кике: {e}'
        bot.reply_to(message, response)

@bot.message_handler(commands=['ban'])
def ban(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not is_admin(chat_id, user_id):
        response = 'Только админы могут банить.'
        bot.reply_to(message, response)
        send_log_to_chat(message, 'ban', 'Ошибка: нет прав')
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            response = 'Использование: /ban <user_id>'
            bot.reply_to(message, response)
            return
        
        target_id = int(parts[1])
        # Бан навсегда (until_date=None)
        bot.ban_chat_member(chat_id, target_id)
        
        response = f'Пользователь {target_id} забанен.'
        bot.reply_to(message, response)
        log_action(chat_id, user_id, 'ban', f'user={target_id}')
        send_log_to_chat(message, 'ban', response)
        
    except (IndexError, ValueError) as e:
        response = 'Использование: /ban <user_id>'
        bot.reply_to(message, response)
    except Exception as e:
        response = f'Ошибка при бане: {e}'
        bot.reply_to(message, response)

@bot.message_handler(commands=['report'])
def report(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            response = 'Использование: /report <user_id> <причина>'
            bot.reply_to(message, response)
            return
        
        target_id = int(parts[1])
        reason = parts[2] if len(parts) > 2 else 'без причины'
        
        data['reports'].append({
            'chat_id': chat_id,
            'reporter_id': user_id,
            'target_id': target_id,
            'reason': reason,
            'timestamp': time.time()
        })
        save_data()
        
        response = f'Репорт на пользователя {target_id} отправлен с причиной: {reason}.'
        bot.reply_to(message, response)
        log_action(chat_id, user_id, 'report', f'target={target_id}, reason={reason}')
        send_log_to_chat(message, 'report', response)
        
    except (IndexError, ValueError) as e:
        response = 'Использование: /report <user_id> <причина>'
        bot.reply_to(message, response)

@bot.message_handler(commands=['vip'])
def set_vip(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not is_admin(chat_id, user_id):
        response = 'Только админы могут назначать VIP.'
        bot.reply_to(message, response)
        send_log_to_chat(message, 'vip', 'Ошибка: нет прав')
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            response = 'Использование: /vip <user_id> <true/false>'
            bot.reply_to(message, response)
            return
        
        target_id = int(parts[1])
        is_vip = parts[2].lower() == 'true'
        
        info = get_user_info(chat_id, target_id)
        info['vip'] = is_vip
        save_data()
        
        response = f'VIP-статус пользователя {target_id} установлен как {is_vip}.'
        bot.reply_to(message, response)
        log_action(chat_id, user_id, 'vip', f'user={target_id}, vip={is_vip}')
        send_log_to_chat(message, 'vip', response)
        
    except (IndexError, ValueError) as e:
        response = 'Использование: /vip <user_id> <true/false>'
        bot.reply_to(message, response)

@bot.message_handler(commands=['nick'])
def set_nick(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            response = 'Использование: /nick <ник>'
            bot.reply_to(message, response)
            return
        
        nick = parts[1]
        info = get_user_info(chat_id, user_id)
        info['nick'] = nick
        save_data()
        
        response = f'Ваш ник установлен как {nick}.'
        bot.reply_to(message, response)
        log_action(chat_id, user_id, 'nick', f'nick={nick}')
        send_log_to_chat(message, 'nick', response)
        
    except IndexError as e:
        response = 'Использование: /nick <ник>'
        bot.reply_to(message, response)

@bot.message_handler(commands=['mute'])
def mute(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not is_admin(chat_id, user_id):
        response = 'Только админы могут мутить.'
        bot.reply_to(message, response)
        send_log_to_chat(message, 'mute', 'Ошибка: нет прав')
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            response = 'Использование: /mute <user_id> <минуты>'
            bot.reply_to(message, response)
            return
        
        target_id = int(parts[1])
        duration_min = int(parts[2])
        
        # Ограничиваем максимальное время мута (например, 7 дней)
        if duration_min > 10080:  # 7 дней в минутах
            duration_min = 10080
        
        mute_until = time.time() + duration_min * 60
        
        # Пытаемся замутить через права чата
        try:
            bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=target_id,
                until_date=int(mute_until),
                permissions=telebot.types.ChatPermissions(
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
        except Exception as e:
            print(f"[ОШИБКА] Не удалось установить мут через API: {e}")
        
        # Сохраняем в нашей БД
        info = get_user_info(chat_id, target_id)
        info['muted_until'] = mute_until
        save_data()
        
        response = f'Пользователь {target_id} замучен на {duration_min} минут.'
        bot.reply_to(message, response)
        log_action(chat_id, user_id, 'mute', f'user={target_id}, until={mute_until}')
        send_log_to_chat(message, 'mute', response)
        
    except (IndexError, ValueError) as e:
        response = 'Использование: /mute <user_id> <минуты>'
        bot.reply_to(message, response)

@bot.message_handler(func=lambda m: True)
def check_mute(message):
    """Проверка мута для всех сообщений"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # Пропускаем команды
    if message.text and message.text.startswith('/'):
        return
    
    info = get_user_info(chat_id, user_id)
    
    if info['muted_until'] and info['muted_until'] > time.time():
        try:
            bot.delete_message(chat_id, message.message_id)
            
            # Отправляем предупреждение только раз в 30 секунд
            current_time = time.time()
            if user_id not in active_users or current_time - active_users[user_id] > 30:
                mute_time = datetime.fromtimestamp(info['muted_until']).strftime("%Y-%m-%d %H:%M:%S")
                warning = f'@{message.from_user.username if message.from_user.username else "Пользователь"}, вы замучены до {mute_time}.'
                bot.send_message(chat_id, warning)
                active_users[user_id] = current_time
        except Exception as e:
            print(f"[ОШИБКА] Не удалось удалить сообщение или отправить предупреждение: {e}")

# Обработка новых участников
@bot.message_handler(content_types=['new_chat_members'])
def on_new_chat_members(message):
    """Обработка вступления новых участников"""
    chat_id = message.chat.id
    
    for new_member in message.new_chat_members:
        user_id = new_member.id
        
        # Определяем, кто пригласил
        inviter_id = None
        if message.from_user and message.from_user.id != user_id:
            inviter_id = message.from_user.id
        
        # Создаем запись о пользователе
        info = get_user_info(chat_id, user_id)
        info['inviter_id'] = inviter_id
        save_data()
        
        log_action(chat_id, user_id, 'join', f'inviter={inviter_id}')
        
        # Приветствие
        welcome_msg = f"Добро пожаловать, {new_member.first_name}!"
        if new_member.username:
            welcome_msg += f" (@{new_member.username})"
        
        bot.send_message(chat_id, welcome_msg)

# Обработчик callback-запросов (для инлайн-клавиатур, если будут)
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Обработка callback-запросов от inline-клавиатур"""
    try:
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"[ОШИБКА] Обработка callback: {e}")

# Запуск бота
if __name__ == '__main__':
    print('Бот запущен...')
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"[КРИТИЧЕСКАЯ ОШИБКА] Бот упал: {e}")
        time.sleep(5)