import telebot
from telebot import types

# Ваш токен от BotFather
TOKEN = '7973595298:AAH1CKjhtrlSjSZx-5jNNVGfJK3qRZlpCtU'

# Ваш ID пользователя (чтобы бот знал, куда пересылать)
YOUR_USER_ID = 7614638047  # замените на свой реальный Telegram ID

# Инициализация бота
bot = telebot.TeleBot(TOKEN)

# Словарь для хранения ID активных участников (тех, кто писал в чат)
active_users = {}


def send_log_to_owner(message, command, response_text):
    """Отправляет в ЛС владельцу бота информацию о команде и ответе"""
    user_info = f"Пользователь: {message.from_user.full_name} (@{message.from_user.username or 'нет юзернейма'})"
    user_id = message.from_user.id
    chat_info = f"Чат: {message.chat.type} (ID: {message.chat.id})"
    if message.chat.title:
        chat_info += f" — {message.chat.title}"

    log_msg = (
        f"📬 Выполнена команда:\n"
        f"   Команда: /{command}\n"
        f"   Ответ: `{response_text}`\n"
        f"{user_info}\n"
        f"   User ID: {user_id}\n"
        f"{chat_info}\n"
        f"   Дата: {message.date}"
    )
    bot.send_message(YOUR_USER_ID, log_msg, parse_mode='Markdown')

@bot.message_handler(commands=['start'])
def start(message):
    response = 'Привет! Я бот. Чем могу помочь?'
    bot.send_message(message.chat.id, response)
    send_log_to_owner(message, 'start', response)

@bot.message_handler(commands=['help'])
def help(message):
    response = 'Используйте команды: /start — начало, /help — помощь.'
    bot.send_message(message.chat.id, response)
    send_log_to_owner(message, 'help', response)

@bot.message_handler(commands=['ping'])
def ping(message):
    response = 'бот работает при неполадках обратитесь к @I_am_ripped'
    bot.send_message(message.chat.id, response)
    send_log_to_owner(message, 'ping', response)

@bot.message_handler(commands=['owner'])
def owner(message):
    response = 'Создатель бота @I_am_Ripped'
    bot.send_message(message.chat.id, response)
    send_log_to_owner(message, 'owner', response)

@bot.message_handler(commands=['admins'])
def list_admins(message):
    chat_id = message.chat.id
    try:
        admins = bot.get_chat_administrators(chat_id)
        if admins:
            admin_list = []
            for admin in admins:
                user = admin.user
                name = user.first_name
                if user.last_name:
                    name += f" {user.last_name}"
                username = f"@{user.username}" if user.username else "нет юзернейма"
                admin_list.append(f"• {name} ({username}) — ID: {user.id}")
            response = "👮 Администраторы чата:\n" + "\n".join(admin_list)
        else:
            response = "❌ В чате нет администраторов."
    except Exception as e:
        response = f"❌ Ошибка при получении списка админов: {e}"
    
    bot.reply_to(message, response)
    send_log_to_owner(message, 'admins', response)

@bot.message_handler(commands=['members'])
def list_members(message):
    chat_id = message.chat.id
    if chat_id in active_users and active_users[chat_id]:
        member_list = []
        for user_id, user_info in active_users[chat_id].items():
            name = user_info['name']
            username = f"@{user_info['username']}" if user_info['username'] else "нет юзернейма"
            member_list.append(f"• {name} ({username}) — ID: {user_id}")
        response = f"👥 Активные участники ({len(member_list)}):\n" + "\n".join(member_list)
    else:
        response = "❌ Нет данных об активных участниках. Пусть кто‑нибудь напишет в чат."
    
    bot.reply_to(message, response)
    send_log_to_owner(message, 'members', response)

@bot.message_handler(commands=['count'])
def count_members(message):
    chat_id = message.chat.id
    try:
        count = bot.get_chat_members_count(chat_id)
        response = f"📊 В чате {count} участников."
    except Exception as e:
        response = f"❌ Ошибка при подсчёте: {e}"
    
    bot.reply_to(message, response)
    send_log_to_owner(message, 'count', response)

@bot.message_handler(func=lambda msg: True)
def record_user(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # Если чата ещё нет в словаре — создаём
    if chat_id not in active_users:
        active_users[chat_id] = {}
    
    # Записываем данные пользователя
    active_users[chat_id][user_id] = {
        'name': message.from_user.first_name,
        'username': message.from_user.username  # может быть None
    }

bot.polling(none_stop=True, interval=0)
