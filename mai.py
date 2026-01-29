import telebot
import json
import time
from datetime import datetime, timedelta

from dotenv import load_dotenv
import os

load_dotenv()

LOG_CHAT_ID = -1003608057275  # ← замените на ID вашего чата/канала
# Настройки
API_TOKEN = 'ВАШ_ТОКЕН'
LOG_CHAT_ID = -1001234567890  # ID чата для логов
ADMIN_ID = 123456789  # Ваш ID для доступа к админ‑командам

# Инициализация бота
bot = telebot.TeleBot(API_TOKEN)

# Словарь для хранения данных активных участников
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
    user_tag = get_user_identifier(message.from_user)
    chat_info = f"Исходный чат: {message.chat.type} (ID: {message.chat.id})"
    if message.chat.title:
        chat_info += f" — «{message.chat.title}»"

    log_msg = (
        f"📊 **ЛОГ ВЫПОЛНЕНИЯ КОМАНДЫ**\n\n"
        f"🔹 Команда: `/{command}`\n"
        f"🔹 Ответ бота: `{response_text}`\n"
        f"🔹 Пользователь: {user_tag} (ID: {message.from_user.id})\n"
        f"{chat_info}\n"
        f"🔹 Дата: `{message.date}`"
    )
    try:
        bot.send_message(LOG_CHAT_ID, log_msg, parse_mode='Markdown')
    except Exception as e:
        print(f"[ОШИБКА] Не удалось отправить лог: {e}")

# Хранилище данных (в реальном проекте используйте БД: SQLite, MongoDB и т. п.)
data = {
    'chats': {},  # {chat_id: {users: {}, settings: {}}}
    'reports': []
}

# Загрузка/сохранение данных
def load_data():
    try:
        with open('bot_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return data

def save_data():
    with open('bot_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# Вспомогательные функции
def log_action(chat_id, user_id, action, details=''):
    msg = (f'[LOG] Чат {chat_id}\n'
           f'Пользователь {user_id} выполнил: {action}\n'
           f'Детали: {details}\n'
           f'Время: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    bot.send_message(LOG_CHAT_ID, msg)

def get_user_info(chat_id, user_id):
    if chat_id not in data['chats']:
        data['chats'][chat_id] = {'users': {}, 'settings': {}}
    if user_id not in data['chats'][chat_id]['users']:
        data['chats'][chat_id]['users'][user_id] = {
            'role': 'user',
            'warns': 0,
            'vip': False,
            'nick': None,
            'join_time': time.time(),
            'inviter_id': None,
            'muted_until': None
        }
    return data['chats'][chat_id]['users'][user_id]

def is_admin(chat_id, user_id):
    member = bot.get_chat_member(chat_id, user_id)
    return member.status in ['administrator', 'creator'] or user_id == ADMIN_ID

# Команды

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    info = get_user_info(chat_id, user_id)
    bot.reply_to(message, f'Привет! Твой статус: {info["role"]}. VIP: {info["vip"]}')

@bot.message_handler(commands=['stats'])
def stats(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    info = get_user_info(chat_id, user_id)
    joined = datetime.fromtimestamp(info['join_time']).strftime('%Y-%m-%d %H:%M:%S')
    inviter = info['inviter_id'] if info['inviter_id'] else 'неизвестно'
    stats_msg = (f'Статистика пользователя {user_id}:\n'
                 f'Роль: {info["role"]}\n'
                 f'VIP: {info["vip"]}\n'
                 f'Ник: {info["nick"] or "не установлен"}\n'
                 f'Варны: {info["warns"]}\n'
                 f'Время вступления: {joined}\n'
                 f'Пригласил: {inviter}\n'
                 f'Замутён до: {info["muted_until"] or "нет"}')
    bot.reply_to(message, stats_msg)

@bot.message_handler(commands=['setrole'])
def set_role(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if not is_admin(chat_id, user_id):
        bot.reply_to(message, 'Только админы могут менять роли.')
        return
    try:
        target_id = int(message.text.split()[1])
        role = message.text.split()[2]
        info = get_user_info(chat_id, target_id)
        info['role'] = role
        save_data()
        log_action(chat_id, user_id, 'setrole', f'user={target_id}, role={role}')
        bot.reply_to(message, f'Роль пользователя {target_id} изменена на {role}.')
    except (IndexError, ValueError):
        bot.reply_to(message, 'Использование: /setrole <user_id> <role>')

@bot.message_handler(commands=['warn'])
def warn(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if not is_admin(chat_id, user_id):
        bot.reply_to(message, 'Только админы могут выдавать варны.')
        return
    try:
        target_id = int(message.text.split()[1])
        info = get_user_info(chat_id, target_id)
        info['warns'] += 1
        save_data()
        log_action(chat_id, user_id, 'warn', f'user={target_id}, warns={info["warns"]}')
        bot.reply_to(message, f'Пользователь {target_id} получил варн (№{info["warns"]}).')
        if info['warns'] >= 3:
            bot.kick_chat_member(chat_id, target_id)
            bot.send_message(chat_id, f'Пользователь {target_id} кикнут за 3 варна.')
    except (IndexError, ValueError):
        bot.reply_to(message, 'Использование: /warn <user_id>')

@bot.message_handler(commands=['kick'])
def kick(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if not is_admin(chat_id, user_id):
        bot.reply_to(message, 'Только админы могут кикать.')
        return
    try:
        target_id = int(message.text.split()[1])
        bot.kick_chat_member(chat_id, target_id)
        log_action(chat_id, user_id, 'kick', f'user={target_id}')
        bot.reply_to(message, f'Пользователь {target_id} кикнут.')
    except (IndexError, ValueError):
        bot.reply_to(message, 'Использование: /kick <user_id>')

@bot.message_handler(commands=['ban'])
def ban(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if not is_admin(chat_id, user_id):
        bot.reply_to(message, 'Только админы могут банить.')
        return
    try:
        target_id = int(message.text.split()[1])
        bot.ban_chat_member(chat_id, target_id)
        log_action(chat_id, user_id, 'ban', f'user={target_id}')
        bot.reply_to(message, f'Пользователь {target_id} забанен.')
    except (IndexError, ValueError):
        bot.reply_to(message, 'Использование: /ban <user_id>')

@bot.message_handler(commands=['report'])
def report(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    try:
        target_id = int(message.text.split()[1])
        reason = message.text.split()[2] if len(message.text.split()) > 2 else 'без причины'
        data['reports'].append({
            'chat_id': chat_id,
                    'target_id': target_id,
        'reason': reason,
        'timestamp': time.time()
    })
    save_data()
    log_action(chat_id, user_id, 'report', f'target={target_id}, reason={reason}')
    bot.reply_to(message, f'Репорт на пользователя {target_id} отправлен с причиной: {reason}.')
except (IndexError, ValueError):
    bot.reply_to(message, 'Использование: /report <user_id> <причина>')

@bot.message_handler(commands=['vip'])
def set_vip(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if not is_admin(chat_id, user_id):
        bot.reply_to(message, 'Только админы могут назначать VIP.')
        return
    try:
        target_id = int(message.text.split()[1])
        is_vip = message.text.split()[2].lower() == 'true'
        info = get_user_info(chat_id, target_id)
        info['vip'] = is_vip
        save_data()
        log_action(chat_id, user_id, 'vip', f'user={target_id}, vip={is_vip}')
        bot.reply_to(message, f'VIP-статус пользователя {target_id} установлен как {is_vip}.')
    except (IndexError, ValueError):
        bot.reply_to(message, 'Использование: /vip <user_id> <true/false>')

@bot.message_handler(commands=['nick'])
def set_nick(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    try:
        nick = message.text.split(maxsplit=1)[1]
        info = get_user_info(chat_id, user_id)
        info['nick'] = nick
        save_data()
        log_action(chat_id, user_id, 'nick', f'nick={nick}')
        bot.reply_to(message, f'Ваш ник установлен как {nick}.')
    except IndexError:
        bot.reply_to(message, 'Использование: /nick <ник>')

@bot.message_handler(commands=['mute'])
def mute(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if not is_admin(chat_id, user_id):
        bot.reply_to(message, 'Только админы могут мутить.')
        return
    try:
        target_id = int(message.text.split()[1])
        duration_min = int(message.text.split()[2])
        mute_until = time.time() + duration_min * 60
        info = get_user_info(chat_id, target_id)
        info['muted_until'] = mute_until
        save_data()
        log_action(chat_id, user_id, 'mute', f'user={target_id}, until={mute_until}')
        bot.reply_to(message, f'Пользователь {target_id} замучен на {duration_min} мин.')
    except (IndexError, ValueError):
        bot.reply_to(message, 'Использование: /mute <user_id> <минуты>')

@bot.message_handler(func=lambda m: True)
def check_mute(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    info = get_user_info(chat_id, user_id)
    if info['muted_until'] and info['muted_until'] > time.time():
        bot.delete_message(chat_id, message.message_id)
        bot.send_message(chat_id, f'@{message.from_user.username}, вы замутены до {datetime.fromtimestamp(info["muted_until"]).strftime("%H:%M:%S")}.')

# Обработка инвайтинга (приглашения)
@bot.chat_member_handler()
def on_chat_member_update(update):
    chat_id = update.chat.id
    new_status = update.new_chat_member.status
    user_id = update.new_chat_member.user.id
    if new_status == 'member' and user_id not in data['chats'].get(chat_id, {}).get('users', {}):
        # Первый вход в чат
        inviter_id = None
        if update.from_user and update.from_user.id != user_id:
            inviter_id = update.from_user.id
        info = get_user_info(chat_id, user_id)
        info['inviter_id'] = inviter_id
        save_data()
        log_action(chat_id, user_id, 'join', f'inviter={inviter_id}')

# Запуск бота
if __name__ == '__main__':
    print('Бот запущен...')
    bot.infinity_polling()

