import os
import re
import requests
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, MessageHandler, Filters, CommandHandler, CallbackContext

# Настройки
TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
GSB_API_KEY = os.getenv("GSB_API_KEY")
PORT = int(os.getenv("PORT", 8080))

bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=1)

# Простая эвристика
def is_phishing_link(url):
    patterns = ["login", "secure", ".xyz", ".zip", "@", "paypal", "verify"]
    return any(p in url.lower() for p in patterns)

# Google Safe Browsing
def check_google_safe_browsing(url):
    endpoint = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={GSB_API_KEY}"
    payload = {
        "client": {
            "clientId": "phishing-bot",
            "clientVersion": "1.0"
        },
        "threatInfo": {
            "threatTypes": [
                "MALWARE", "SOCIAL_ENGINEERING",
                "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"
            ],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}]
        }
    }

    try:
        response = requests.post(endpoint, json=payload)
        result = response.json()
        return bool(result.get("matches"))
    except Exception as e:
        print("GSB Error:", e)
        return False

# Оповещение владельца
def notify_owner(message, sender_id):
    bot.send_message(chat_id=OWNER_ID, text=f"🚨 Suspicious link from {sender_id}:\n{message}")

# /start
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Hi! Send me a link and I will check if it's phishing.")

# Обработка сообщений
def handle_message(update: Update, context: CallbackContext):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    sender_id = update.message.from_user.id
    urls = re.findall(r'https?://\S+', user_text)
    if urls:
        flagged = False
        for url in urls:
            if is_phishing_link(url) or check_google_safe_browsing(url):
                update.message.reply_text("⚠️ This might be a phishing link!")
                notify_owner(user_text, sender_id)
                flagged = True
        if not flagged:
            update.message.reply_text("✅ The link looks safe.")
    else:
        update.message.reply_text("Please send a valid link.")

# Обработчики
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# Webhook
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

# Запуск
if __name__ == "__main__":
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    bot.set_webhook(url=webhook_url)
    app.run(host="0.0.0.0", port=PORT)
