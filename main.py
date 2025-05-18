import os
import re
import requests
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, MessageHandler, Filters, CommandHandler
from keep_alive import keep_alive

TOKEN = os.getenv("TOKEN")  # Установи переменную окружения в Render
OWNER_ID = int(os.getenv("OWNER_ID"))  # тоже в Render: 908080934

bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=0)

# Простая проверка ссылки
def is_phishing_link(url):
    patterns = ["login", "secure", ".xyz", ".zip", "@", "paypal", "verify"]
    return any(p in url.lower() for p in patterns)

# Отправка предупреждения тебе
def notify_owner(original_message, sender_id):
    bot.send_message(chat_id=OWNER_ID, text=f"🚨 Возможно, фишинговая ссылка:\nОт пользователя {sender_id}:\n{original_message}")

# Ответ пользователю
def handle_message(update, context):
    user_text = update.message.text
    sender_id = update.message.from_user.id  # ID отправителя
    chat_id = update.message.chat_id

    urls = re.findall(r'https?://\S+', user_text)
    if urls:
        flagged = False
        for url in urls:
            if is_phishing_link(url):
                update.message.reply_text("⚠️ Это может быть фишинговая ссылка!")
                notify_owner(user_text, sender_id)
                flagged = True
        if not flagged:
            update.message.reply_text("✅ Ссылка выглядит безопасной.")
    else:
        update.message.reply_text("Пожалуйста, отправьте ссылку.")

def start(update, context):
    update.message.reply_text("Привет! Отправь мне ссылку, я проверю её на фишинг.")

# Обработка входящих сообщений
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# Webhook Flask
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

keep_alive()

if __name__ == "__main__":
    bot.set_webhook(url=f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}")
    app.run(host="0.0.0.0", port=8080)

