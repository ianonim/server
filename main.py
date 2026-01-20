import telebot
from telebot import types

# Ваш токен от BotFather
TOKEN = '7973595298:AAH1CKjhtrlSjSZx-5jNNVGfJK3qRZlpCtU'

# Ваш ID пользователя (чтобы бот знал, куда пересылать)
YOUR_USER_ID = 7614638047  # замените на свой реальный Telegram ID

# Инициализация бота
bot = telebot.TeleBot(TOKEN)


# Обработчик всех сообщений, содержащих команды
@bot.message_handler(func=lambda message: message.text and message.text.startswith('/'))
def handle_command(message):
    # Извлекаем команду (без / и до первого пробела или конца строки)
    command = message.text.split()[0][1:]  # например, из "/help arg" → "help"

    # Полный текст сообщения (вся команда с аргументами)
    full_text = message.text

    # Информация об отправителе
    user_info = f"Пользователь: {message.from_user.full_name} (@{message.from_user.username or 'нет юзернейма'})"
    user_id = message.from_user.id

    # Информация о чате
    chat_info = f"Чат: {message.chat.type} (ID: {message.chat.id})"
    if message.chat.title:
        chat_info += f" — {message.chat.title}"

    # Формируем сообщение для пересылки вам
    forward_msg = (
        f"📬 Получена команда:\n"
        f"   Команда: /{command}\n"
        f"   Полный текст: `{full_text}`\n"
        f"{user_info}\n"
        f"   User ID: {user_id}\n"
        f"{chat_info}\n"
        f"   Дата: {message.date}"
    )

    # Отправляем вам сообщение
    bot.send_message(YOUR_USER_ID, forward_msg, parse_mode='Markdown')

    # Можно также переслать само исходное сообщение (опционально)
    # bot.forward_message(YOUR_USER_ID, message.chat.id, message.message_id)

    # Ответ пользователю (можно убрать, если не нужен)
    bot.reply_to(message, "Команда получена и переслана администратору.")

# Запуск бота
if __name__ == '__main__':
    bot.polling(none_stop=True)