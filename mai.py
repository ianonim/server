import telebot
import json
import time
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv('bothelper')
LOG_CHAT_ID = -1003608057275
ADMIN_ID = 7614638047

bot = telebot.TeleBot(TOKEN)
active_users = {}

def get_user_identifier(user):
    if user.username:
        return f"@{user.username}"
    return f"{user.first_name} {user.last_name}" if user.last_name else user.first_name

def send_log(message, command, response):
    try:
        user_tag = get_user_identifier(message.from_user)
        chat_info = f"Исходный чат: {message.chat.type} (ID: {message.chat.id})"
        if message.chat.title:
            chat_info += f" — «{message.chat.title}»"
        log_msg = (
            f"📊 **ЛОГ ВЫПОЛНЕНИЯ КОМАНДЫ**\n\n"
            f"🔹 Команда: `/{command}`\n"
            f"🔹 Ответ: `{response[:100]}...`\n"
            f"🔹 Пользователь: {user_tag} (ID: {message.from_user.id})\n"
            f"{chat_info}\n"
            f"🔹 Дата: `{datetime.fromtimestamp(message.date).strftime('%Y-%m-%d %H:%M:%S')}`"
        )
        bot.send_message(LOG_CHAT_ID, log_msg, parse_mode='Markdown')
    except Exception as e:
        print(f"[ОШИБКА] Отправка лога: {e}")

def init_data():
    return {'chats': {}, 'reports': []}

def load_data():
    try:
        with open('bot_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            data.setdefault('chats', {})
            data.setdefault('reports', [])
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return init_data()

def save_data():
    try:
        with open('bot_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ОШИБКА] Сохранение данных: {e}")

data = load_data()

def log_action(chat_id, user_id, action, details=''):
    try:
        msg = (f'[LOG] Чат {chat_id}\n'
               f'Пользователь {user_id} выполнил: {action}\n'
               f'Детали: {details}\n'
               f'Время: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        bot.send_message(LOG_CHAT_ID, msg)
    except Exception as e:
        print(f"[ОШИБКА] Логирование действия: {e}")

def get_user_info(chat_id, user_id):
    if chat_id not in data['chats']:
        data['chats'][chat_id] = {'users': {}, 'settings': {}}
    chat_data = data['chats'][chat_id]
    if str(user_id) not in chat_data['users']:
        chat_data['users'][str(user_id)] = {
            'role': 'user', 'warns': 0, 'vip': False, 'nick': None,
            'join_time': time.time(), 'inviter_id': None, 'muted_until': None
        }
        save_data()
    return chat_data['users'][str(user_id)]

def is_admin(chat_id, user_id):
    if user_id == ADMIN_ID:
        return True
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except Exception as e:
        print(f"[ОШИБКА] Проверка админа: {e}")
        return False

def reply_and_log(message, response, command):
    bot.reply_to(message, response)
    send_log(message, command, response)

def parse_args(message, min_args):
    parts = message.text.split()
    if len(parts) < min_args:
        return None, None
    try:
        target_id = int(parts[1])
        return target_id, parts[2:] if len(parts) > 2 else []
    except ValueError:
        return None, None

@bot.message_handler(commands=['start'])
def start(message):
    info = get_user_info(message.chat.id, message.from_user.id)
    response = f'Привет! Твой статус: {info["role"]}. VIP: {info["vip"]}'
    reply_and_log(message, response, 'start')

@bot.message_handler(commands=['stats'])
def stats(message):
    info = get_user_info(message.chat.id, message.from_user.id)
    joined = datetime.fromtimestamp(info['join_time']).strftime('%Y-%m-%d %H:%M:%S')
    inviter = info['inviter_id'] or 'неизвестно'
    muted = info['muted_until']
    muted_str = datetime.fromtimestamp(muted).strftime('%Y-%m-%d %H:%M:%S') if muted else 'нет'
    response = (f'Статистика:\n'
              f'Роль: {info["role"]}\nVIP: {info["vip"]}\nНик: {info["nick"] or "нет"}\n'
              f'Варны: {info["warns"]}\nВступил: {joined}\nПригласил: {inviter}\nЗамутён: {muted_str}')
    reply_and_log(message, response, 'stats')


@bot.message_handler(commands=['setrole', 'vip'])
def handle_role_vip(message):
    cmd = message.commands[0]
    if not is_admin(message.chat.id, message.from_user.id):
        reply_and_log(message, 'Только админы могут это делать.', cmd)
        return
    target_id, args = parse_args(message, 3)
    if target_id is None:
        reply_and_log(message, f'Использование: /{cmd} <id> <значение>', cmd)
        return
    info = get_user_info(message.chat.id, target_id)
    if cmd == 'setrole':
        info['role'] = args[0]
        response = f'Роль {target_id} изменена на {args[0]}.'
    else:
        info['vip'] = args[0].lower() == 'true'
        response = f'VIP {target_id}: {info["vip"]}.'
    save_data()
    reply_and_log(message, response, cmd)
    log_action(message.chat.id, message.from_user.id, cmd, f'user={target_id}')

@bot.message_handler(commands=['warn', 'kick', 'ban'])
def handle_moderation(message):
    cmd = message.commands[0]
    if not is_admin(message.chat.id, message.from_user.id):
        reply_and_log(message, 'Только админы могут это делать.', cmd)
        return
    target_id, _ = parse_args(message, 2)
    if target_id is None:
        reply_and_log(message, f'Использование: /{cmd} <id>', cmd)
        return
    if cmd == 'warn':
        info = get_user_info(message.chat.id, target_id)
                info['warns'] += 1
        save_data()
        response = f'Пользователь {target_id} получил варн (№{info["warns"]}).'
        if info['warns'] >= 3:
            try:
                bot.kick_chat_member(message.chat.id, target_id, until_date=int(time.time()) + 60)
                response += f'\nПользователь {target_id} кикнут за 3 варна.'
            except Exception as e:
                response += f'\nНе удалось кикнуть: {e}'
    elif cmd == 'kick':
        try:
            bot.kick_chat_member(message.chat.id, target_id, until_date=int(time.time()) + 60)
            response = f'Пользователь {target_id} кикнут.'
        except Exception as e:
            response = f'Ошибка при кике: {e}'
    elif cmd == 'ban':
        try:
            bot.ban_chat_member(message.chat.id, target_id)
            response = f'Пользователь {target_id} забанен.'
        except Exception as e:
            response = f'Ошибка при бане: {e}'
    
    reply_and_log(message, response, cmd)
    log_action(message.chat.id, message.from_user.id, cmd, f'user={target_id}')

@bot.message_handler(commands=['report'])
def report(message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        reply_and_log(message, 'Использование: /report <id> <причина>', 'report')
        return
    try:
        target_id = int(parts[1])
        reason = parts[2]
        data['reports'].append({
            'chat_id': message.chat.id,
            'reporter_id': message.from_user.id,
            'target_id': target_id,
            'reason': reason,
            'timestamp': time.time()
        })
        save_data()
        response = f'Репорт на {target_id} отправлен: {reason}.'
        reply_and_log(message, response, 'report')
        log_action(message.chat.id, message.from_user.id, 'report', f'target={target_id}, reason={reason}')
    except ValueError:
        reply_and_log(message, 'Использование: /report <id> <причина>', 'report')

@bot.message_handler(commands=['nick'])
def set_nick(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        reply_and_log(message, 'Использование: /nick <ник>', 'nick')
        return
    nick = parts[1]
    info = get_user_info(message.chat.id, message.from_user.id)
    info['nick'] = nick
    save_data()
    response = f'Ник установлен: {nick}.'
    reply_and_log(message, response, 'nick')
    log_action(message.chat.id, message.from_user.id, 'nick', f'nick={nick}')

@bot.message_handler(commands=['mute'])
def mute(message):
    if not is_admin(message.chat.id, message.from_user.id):
        reply_and_log(message, 'Только админы могут мутить.', 'mute')
        return
    parts = message.text.split()
    if len(parts) < 3:
        reply_and_log(message, 'Использование: /mute <id> <минуты>', 'mute')
        return
    try:
        target_id = int(parts[1])
        duration_min = int(parts[2])
        if duration_min > 10080:  # макс. 7 дней
            duration_min = 10080
        mute_until = time.time() + duration_min * 60

        try:
            bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=target_id,
                until_date=int(mute_until),
                permissions=telebot.types.ChatPermissions(can_send_messages=False)
            )
        except Exception as e:
            print(f"[ОШИБКА] API mute: {e}")


        info = get_user_info(message.chat.id, target_id)
        info['muted_until'] = mute_until
        save_data()

        response = f'Пользователь {target_id} замучен на {duration_min} минут.'
        reply_and_log(message, response, 'mute')
        log_action(message.chat.id, message.from_user.id, 'mute', f'user={target_id}, until={mute_until}')
    except ValueError:
        reply_and_log(message, 'Использование: /mute <id> <минуты>', 'mute')


@bot.message_handler(func=lambda m: True)
def check_mute(message):
    if message.text and message.text.startswith('/'):
        return  # команды пропускаем
    info = get_user_info(message.chat.id, message.from_user.id)
    if info['muted_until'] and info['muted_until'] > time.time():
        try:
            bot.delete_message(message.chat.id, message.message_id)
            current_time = time.time()
            if (message.from_user.id not in active_users or
                    current_time - active_users[message.from_user.id] > 30):
                mute_time = datetime.fromtimestamp(info['muted_until']).strftime("%Y-%m-%d %H:%M:%S")
                warning = f'@{get_user_identifier(message.from_user)}, вы замучены до {mute_time}.'
                bot.send_message(message.chat.id, warning)
                active_users[message.from_user.id] = current_time
        except Exception as e:
            print(f"[ОШИБКА] Удаление сообщения: {e}")

@bot.message_handler(content_types=['new_chat_members'])
def on_new_member(message):
    for member in message.new_chat_members:
        inviter_id = message.from_user.id if message.from_user.id != member.id else None
        info = get_user_info(message.chat.id, member.id)
        info['inviter_id'] = inviter_id
        save_data()
        log_action(message.chat.id, member.id, 'join', f'inviter={inviter_id}')
        welcome = f"Добро пожаловать, {member.first_name}!"
        if member.username:
            welcome += f" (@{member.username})"
        bot.send_message(message.chat.id, welcome)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"[ОШИБКА] Callback: {e}")

if __name__ == '__main__':
    print('Бот запущен...')
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"[КРИТИЧЕСКАЯ ОШИБКА] Бот упал: {e}")
        time.sleep(5)