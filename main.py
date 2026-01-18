import telebot

bot = telebot.TeleBot('7973595298:AAH1CKjhtrlSjSZx-5jNNVGfJK3qRZlpCtU')

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 'Привет! Я бот. Чем могу помочь?')

@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id, 'Используйте команды: /start — начало, /help — помощь.')

@bot.message_handler(commands=['ping'])
def ping(message):
    bot.send_message(message.chat.id, 'бот работает при неполадках обратитесь к @I_am_ripped')

@bot.message_handler(commands=['owner'])
def owner(message):
    bot.send_message(message.chat.id, 'Создатель бота @I_am_Ripped')
# Словарь для хранения ID активных участников (тех, кто писал в чат)
active_users = {}

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
        bot.reply_to(message, response)
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка при получении списка админов: {e}")

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

@bot.message_handler(commands=['count'])
def count_members(message):
    chat_id = message.chat.id
    try:
        count = bot.get_chat_members_count(chat_id)
        bot.reply_to(message, f"📊 В чате {count} участников.")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка при подсчёте: {e}")

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