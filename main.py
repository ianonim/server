import telebot
from telebot import types
from dotenv import load_dotenv
import os
import json
import logging

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv('bothelper')
LOG_CHAT_ID = -1003608057275  # Замените на свой ID чата/канала

# Инициализация бота
bot = telebot.TeleBot(TOKEN)

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Путь к файлу с данными ролей
DATA_FILE = "roles_data.json"

# Словарь для хранения активных участников
active_users = {}



def load_data():
    """Загрузка данных ролей из файла"""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"roles": {}, "users": {}}



def save_data(data):
    """Сохранение данных ролей в файл"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)



def has_permission(user_id, permission):
    """Проверка наличия разрешения у пользователя"""
    data = load_data()
    role = data["users"].get(str(user_id))
    if not role:
        return False
    permissions = data["roles"][role]["permissions"]
    return "*" in permissions or permission in permissions



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



# --- Команды с логированием ---

@bot.message_handler(commands=['start'])
def start(message):
    response = 'Привет! Я бот, созданный кем‑то.'
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


# --- Команды системы ролей ---

@bot.message_handler(commands=['roles'])
def cmd_roles(message):
    data = load_data()
    roles_info = "\n".join([
        f"- {role}: {', '.join(perms)}"
        for role, perms in data["roles"].items()
    ])
    response = f"Роли:\n{roles_info}" if roles_info else "Роли не определены."
    bot.reply_to(message, response)
    send_log_to_chat(message, 'roles', response)

@bot.message_handler(commands=['myrole'])
def cmd_myrole(message):
    user_id = str(message.from_user.id)
    data = load_data()
    role = data["users"].get(user_id, "нет роли")
    response = f"Ваша роль: {role}"
    bot.reply_to(message, response)
    send_log_to_chat(message, 'myrole', response)

@bot.message_handler(commands=['grant'])
def cmd_grant(message):
    args = message.text.split()[1:]  # Получаем аргументы после команды
    if len(args) != 2:
        response = "Используйте: /grant <user_id> <role>"
        bot.reply_to(message, response)
        send_log_to_chat(message, 'grant', response)
        return

    target_id, role = args
    data = load_data()

    # Проверка прав исполнителя
    if not has_permission(message.from_user.id, "grant_role"):
        response = "У вас нет прав для этой команды."
        bot.reply_to(message, response)
        send_log_to_chat(message, 'grant', response)
        return

    # Проверка существования роли
    if role not in data["roles"]:
        response = f"Роль {role} не существует."
        bot.reply_to(message, response)
        send_log_to_chat(message, 'grant', response)
        return

    data["users"][target_id] = role
    save_data(data)
    response = f"Пользователю {target_id} назначена роль {role}."
    bot.reply_to(message, response)
    send_log_to_chat(message, 'grant', response)


@bot.message_handler(commands=['revoke'])
def cmd_revoke(message):
    args = message.text.split()[1:]
    if len(args) != 1:
        response = "Используйте: /revoke <user_id>"
        bot.reply_to(message, response)
        send_log_to_chat(message, 'revoke', response)
        return

    target_id = args[0]
    data = load_data()

    if not has_permission(message.from_user.id, "revoke_role"):
        response = "У вас нет прав для этой команды."
        bot.reply_to(message, response)
        send_log_to_chat(message, 'revoke', response)
        return

    if target_id in data["users"]:
        del data["users"][target_id]
        save_data(data)
        response = f"У пользователя {target_id} снята роль."
    else:
        response = f"У пользователя {target_id} нет роли."


    bot.reply_to(message, response)
    send_log_to_chat(message, 'revoke', response)


@bot.message_handler(commands=['addrole'])
def cmd_addrole(message):
    args = message.text.split()[1:]
    if len(args) < 1:
        response = "Используйте: /addrole <role_name> [perm1,perm2,...]"
        bot.reply_to(message, response)
        send_log_to_chat(message, 'addrole', response)
        return

    role_name = args[0]
    permissions = args[1].split(",") if len(args) > 1 else []
    data = load_data()

    if not has_permission(message.from_user.id, "manage_roles"):
        response = "У вас нет прав для этой команды."
        bot.reply_to(message, response)
        send_log_to_chat(message, 'addrole', response)
        return

    data["roles"][role_name] = {"permissions": permissions}
    save_data(data)
    response = f"Роль {role_name} создана с правами: {', '.join(permissions)}."
    bot.reply_to(message, response)
    send_log_to_chat(message, 'addrole', response)


@bot.message_handler(commands=['delrole'])
def cmd_delrole(message):
    args = message.text.split()[1:]
    if len(args) != 1:
        response = "Используйте: /delrole <role_name>"
        bot.reply_to(message, response)
        send_log_to_chat(message, 'delrole', response)
        return


    role_name = args[0]
    data = load_data()

    if not has_permission(message.from_user.id, "manage_roles"):
        response = "У вас нет прав для этой команды."
        bot.reply_to(message, response)
        send_log_to_chat(message, 'delrole', response)
        return

    if role_name in data["roles"]:
        del data["roles"][role_name]
        # Снять роль со всех пользователей
        for user_id in list(data["users"]):
            if data["users"][user_id] == role_name:
                del data["users"][user_id]
        save_data(data)
        response = f"Роль {role_name} удалена."
    else:
        response = f"Роль {role_name} не существует."

    bot.reply_to(message, response)
    send_log_to_chat(message, 'delrole', response)

@bot.message_handler(commands=['perm'])
def cmd_perm(message):
    args = message.text.split()[1:]
    if len(args) != 3:
        response = "Используйте: /perm <role> <add/remove> <permission>"
        bot.reply_to(message, response)
        send_log_to_chat(message, 'perm', response)
        return

    role_name, action, permission = args
    data = load_data()

    if not has_permission(message.from_user.id, "manage_roles"):
        response = "У вас нет прав для этой команды."
        bot.reply_to(message, response)
        send_log_to_chat(message, 'perm', response)
        return

    if role_name not in data["roles"]:
        response = f"Роль {role_name} не существует."
        bot.reply_to(message, response)
        send_log_to_chat(message, 'perm', response)
        return

    permissions = data["roles"][role_name]["permissions"]
    if action == "add":
        if permission not in permissions:
            permissions.append(permission)
            response = f"Право {permission} добавлено для роли {role_name}."
        else:
            response = f"Право {permission} уже есть у роли {role_name}."
    elif action == "remove":
        if permission in permissions:
            permissions.remove(permission)
            response = f"Право {permission} удалено из роли {role_name}."
        else:
            response = f"Право {permission} отсутствует у роли {role_name}."
    else:
        response = "Действие должно быть 'add' или 'remove'."

    save_data(data)
    bot.reply_to(message, response)
    send_log_to_chat(message, 'perm', response)


# Обработчик всех остальных сообщений — фиксирует активных пользователей
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
