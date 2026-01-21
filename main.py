import telebot
from telebot import types

# Ваш токен от BotFather
TOKEN = '7973595298:AAH1CKjhtrlSjSZx-5jNNVGfJK3qRZlpCtU'


# ID чата, куда отправлять логи (группа/канал)
LOG_CHAT_ID = -1003608057275  # ← замените на ID вашего чата/канала


# Инициализация бота
bot = telebot.TeleBot(TOKEN)


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


@bot.message_handler(commands=['start'])
def start(message):
    response = 'Привет! Я бот. Чем могу помочь?'
    bot.send_message(message.chat.id, response)
    send_log_to_chat(message, 'start', response)


@bot.message_handler(commands=['help'])
def help(message):
    response = 'Используйте команды: /start — начало, /help — помощь.'
    bot.send_message(message.chat.id, response)
    send_log_to_chat(message, 'help', response)


@bot.message_handler(commands=['ping'])
def ping(message):
    response = 'Бот работает. При неполадках обратитесь к @I_am_ripped'
    bot.send_message(message.chat.id, response)
    send_log_to_chat(message, 'ping', response)


@bot.message_handler(commands=['owner'])
def owner(message):
    response = 'Создатель бота: @I_am_Ripped'
    bot.send_message(message.chat.id, response)
    send_log_to_chat(message, 'owner', response)


@bot.message_handler(commands=['admins'])
def list_admins(message):
    chat_id = message.chat.id
    try:
        admins = bot.get_chat_administrators(chat_id)
        if admins:
            admin_list = []
            for admin in admins:
                user = admin.user
                user_tag = get_user_identifier(user)
                admin_list.append(f"• {user_tag} — ID: {user.id}")
            response = "👮 Администраторы чата:\n" + "\n".join(admin_list)
        else:
            response = "❌ В чате нет администраторов."
    except Exception as e:
        response = f"❌ Ошибка при получении списка админов: {e}"
    
    bot.reply_to(message, response)
    send_log_to_chat(message, 'admins', response)


@bot.message_handler(commands=['members'])
def list_members(message):
    chat_id = message.chat.id
    if chat_id in active_users and active_users[chat_id]:
        member_list = []
        for user_id, user_info in active_users[chat_id].items():
            name = user_info['name']
            username = user_info['username']
            if username:
                user_tag = f"@{username}"
            elif 'last_name' in user_info and user_info['last_name']:
                user_tag = f"{name} {user_info['last_name']}"
            else:
                user_tag = name
            member_list.append(f"• {user_tag} — ID: {user_id}")
        response = f"👥 Активные участники ({len(member_list)}):\n" + "\n".join(member_list)
    else:
        response = "❌ Нет данных об активных участниках. Пусть кто‑нибудь напишет в чат."
    bot.reply_to(message, response)
    send_log_to_chat(message, 'members', response)

@bot.message_handler(commands=['count'])
def count_members(message):
    chat_id = message.chat.id
    try:
        count = bot.get_chat_members_count(chat_id)
        response = f"📊 В чате {count} участников."
    except Exception as e:
        response = f"❌ Ошибка при подсчёте: {e}"
    bot.reply_to(message, response)
    send_log_to_chat(message, 'count', response)


@bot.message_handler(func=lambda msg: True)
def record_user(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if chat_id not in active_users:
        active_users[chat_id] = {}
    active_users[chat_id][user_id] = {
        'name': message.from_user.first_name,
        'last_name': message.from_user.last_name,
        'username': message.from_user.username
    }

if __name__ == '__main__':
    print("Бот запущен. Логи отправляются в чат ID:", LOG_CHAT_ID)
    bot.infinity_polling()

