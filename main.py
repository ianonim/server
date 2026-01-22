import logging
import time
import telebot
from telebot import types
from funpay_api import FunPayAPI


# --- НАСТРОЙКИ ---
TOKEN_TELEGRAM_BOT = '7973595298:AAH1CKjhtrlSjSZx-5jNNVGfJK3qRZlpCtU'
LOG_CHAT_ID = -1003608057275  # чат для логов команд бота

FUNPAY_GOLDEN_KEY = "684riu7m6k7ieudx9k7b0xwynnxg7721"
TELEGRAM_TOKEN_FUNPAY = "8528567225:AAFsRElts8mqoheH89GmMDahZm4o2XVCuhk"
TELEGRAM_CHAT_ID_FUNPAY = -1003601117936  # чат для уведомлений FunPay (число, не строка!)
LOG_FILE = "bot.log"


# --- ИНИЦИАЛИЗАЦИЯ ---
bot = telebot.TeleBot(TOKEN_TELEGRAM_BOT)
fp = FunPayAPI(golden_key=FUNPAY_GOLDEN_KEY)
active_users = {}


# --- ЛОГГИНГ ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- ФУНКЦИИ TELEGRAM-БОТА ---
def get_user_identifier(user):
    if not user:
        return "Неизвестный пользователь"
    if user.username:
        return f"@{user.username}"
    elif user.last_name:
        return f"{user.first_name} {user.last_name}"
    else:
        return user.first_name

def send_log_to_chat(message, command, response_text):
    if not message.from_user:
        logger.error("Не удалось получить данные пользователя для лога.")
        return
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
        logger.error(f"[ОШИБКА] Не удалось отправить лог: {e}")


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
        admins = bot.get_chat_administrators(chat_id)  # Исправлено: "administrators" → "administrators"
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
            elif 'last_name' in user_info and user_tag
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
    if not message.from_user:
        return  # пропускаем сообщения без пользователя
    chat_id = message.chat.id
    user_id = message.from_user.id
    if chat_id not in active_users:
        active_users[chat_id] = {}
    active_users[chat_id][user_id] = {
        'name': message.from_user.first_name or '',
        'last_name': message.from_user.last_name or '',
        'username': message.from_user.username or ''
    }

# --- ФУНКЦИИ FUNPAY ---
def send_telegram_notification(message):
    """Отправляет уведомление в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID_FUNPAY, message)
        logger.info("Уведомление отправлено в Telegram")
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление в Telegram: {e}")


def raise_all_lots():
    """Поднимает все активные лоты."""
    try:
        lots = fp.get_lots()
        if not lots:
            logger.warning("Не удалось получить список лотов")
            return
        raised_count = 0
        for lot in lots:
            if lot.get("status") == "active":
                try:
                    fp.raise_lot(lot["id"])
                    logger.info(f"Поднят лот: #{lot['id']} ({lot['title']})")
                    raised_count += 1
                except Exception as e:
                    logger.error(f"Ошибка при поднятии лота {lot['id']}: {e}")
        if raised_count > 0:
            send_telegram_notification(f"Поднято лотов: {raised_count}")
    except Exception as e:
        logger.error(f"Ошибка при поднятии лотов: {e}")

def check_messages():
    """Проверяет новые сообщения и отправляет их в Telegram."""
    try:
        messages = fp.get_messages()
        if not messages:
            logger.warning("Не удалось получить сообщения от FunPay")
            return
        for msg in messages:
            if msg.get("new"):
                text = msg.get("message", "Нет текста")
                sender = msg.get("sender_name", "Неизвестный отправитель")
                order_id = msg.get("order_id", "без заказа")
                notification = (
                    f"Новое сообщение от {sender}\n"
                    f"Заказ: #{order_id}\n"
                    f"Текст: {text}"
                )
                send_telegram_notification(notification)
                logger.info(f"Отправлено уведомление о сообщении от {sender}")
    except Exception as e:
        logger.error(f"Ошибка при проверке сообщений: {e}")

# --- ОСНОВНОЙ ЦИКЛ ---
def main():
    logger.info("Бот запущен.")
    send_telegram_notification("Бот стартовал.")

    # Запуск Telegram-бота в отдельном потоке
    import threading
    tg_thread = threading.Thread(target=bot.infinity_polling, daemon=False)
    tg_thread.start()


    # Основной цикл для FunPay
    while True:
        try:
            # Поднимаем лоты
            raise_all_lots()

            # Проверяем сообщения
            check_messages()

            time.sleep(30)  # Цикл каждые 30 секунд


        except KeyboardInterrupt:
            logger.info("Бот остановлен пользователем.")
            break
        except Exception as e:
            logger.error(f"Критическая ошибка в основном цикле: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()

