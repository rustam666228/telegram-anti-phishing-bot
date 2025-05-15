import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

app = Flask(__name__)

TOKEN = os.environ.get("TOKEN")  # Токен должен быть в переменных окружения!
bot = Bot(token=TOKEN)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

# === Обработчики ===
def start(update, context):
    update.message.reply_text("Привет! Отправь ссылку — я проверю её на фишинг.")

def handle_message(update, context):
    url = update.message.text.lower()
    if "login" in url or "secure" in url or ".xyz" in url:
        update.message.reply_text("⚠️ Это может быть фишинговая ссылка!")
    else:
        update.message.reply_text("✅ Ссылка выглядит безопасной.")

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# === Вебхук ===
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok", 200

@app.route("/")
def index():
    return "Бот работает!", 200

if __name__ == "__main__":
    PORT = int(os.environ.get('PORT', 10000))
    app.run(host="0.0.0.0", port=PORT)

