import os
import re
import requests
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, MessageHandler, Filters, CommandHandler

TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
PORT = int(os.getenv("PORT", 8080))  # Render задаёт порт через переменную PORT

bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=0)

def is_phishing_link(url):
    patterns = ["login", "secure", ".xyz", ".zip", "@", "paypal", "verify"]
    return any(p in url.lower() for p in patterns)

def notify_owner(original_message, sender_id):
    bot.send_message(chat_id=OWNER_ID, text=f"🚨 Возможно, фишинговая ссылка:\nОт пользователя {sender_id}:\n{original_message}")

def handle_message(update, context):
    user_text = update.message.text
    sender_id = update.message.from_user.id
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

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

if __name__ == "__main__":
    # Устанавливаем вебхук, используем переменную окружения RENDER_EXTERNAL_HOSTNAME
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    bot.set_webhook(url=webhook_url)
    print(f"Webhook set to: {webhook_url}")

    # Запускаем Flask на порту, который выделил Render
    app.run(host="0.0.0.0", port=PORT)
