import os
import re
import requests
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, MessageHandler, Filters, CommandHandler, CallbackContext
# from keep_alive import keep_alive

# Получение переменных окружения
TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))  # например: 908080934

bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=1)  # Важно: хотя бы 1 worker!

# Простая проверка фишинговой ссылки
def is_phishing_link(url):
    patterns = ["login", "secure", ".xyz", ".zip", "@", "paypal", "verify"]
    return any(p in url.lower() for p in patterns)

# Уведомление владельца
def notify_owner(original_message, sender_id):
    try:
        bot.send_message(
            chat_id=OWNER_ID,
            text=f"🚨 Возможно, фишинговая ссылка:\nОт пользователя {sender_id}:\n{original_message}"
        )
    except Exception as e:
        print("Ошибка при отправке владельцу:", e)

# Команда /start
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Привет! Отправь мне ссылку, я проверю её на фишинг.")

# Обработка любых текстовых сообщений
def handle_message(update: Update, context: CallbackContext):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    user_id = update.message.chat.id

    urls = re.findall(r'https?://\S+', user_text)
    if urls:
        flagged = False
        for url in urls:
            if is_phishing_link(url):
                update.message.reply_text("⚠️ Это может быть фишинговая ссылка!")
                notify_owner(user_text, user_id)
                flagged = True
        if not flagged:
            update.message.reply_text("✅ Ссылка выглядит безопасной.")
    else:
        update.message.reply_text("Пожалуйста, отправьте ссылку.")

# Добавление обработчиков
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# Обработка входящих обновлений из Telegram через Webhook
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
    except Exception as e:
        print("Ошибка при обработке update:", e)
    return "ok"

# Запуск keep_alive (если ты его используешь для Render)
keep_alive()

# Установка Webhook при запуске
if __name__ == "__main__":
    WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=8080)
