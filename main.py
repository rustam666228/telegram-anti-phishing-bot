import os
import re
import pickle
import requests
import joblib
clf = joblib.load("phishing_model.pkl")
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, MessageHandler, Filters, CommandHandler, CallbackContext
from sklearn.feature_extraction.text import CountVectorizer

# Загрузка переменных окружения
TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
GSB_API_KEY = os.getenv("GSB_API_KEY")
VT_API_KEY = os.getenv("VT_API_KEY")
PORT = int(os.getenv("PORT", 8080))

# Инициализация бота и Flask
bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=1)

# Загрузка модели машинного обучения
with open("phishing_model.pkl", "rb") as f:
    model = pickle.load(f)
vectorizer = CountVectorizer()

# === Методы проверки ссылок ===

# Эвристический анализ
def is_phishing_link(url):
    patterns = ["login", "secure", ".xyz", ".zip", "@", "paypal", "verify"]
    return any(p in url.lower() for p in patterns)

# Google Safe Browsing
def check_google_safe_browsing(url):
    endpoint = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={GSB_API_KEY}"
    payload = {
        "client": {"clientId": "phishing-bot", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}]
        }
    }
    try:
        response = requests.post(endpoint, json=payload)
        return bool(response.json().get("matches"))
    except Exception as e:
        print("GSB error:", e)
        return False

# VirusTotal
def check_virustotal(url):
    headers = {"x-apikey": VT_API_KEY}
    try:
        resp = requests.post("https://www.virustotal.com/api/v3/urls", headers=headers, data={"url": url})
        analysis_id = resp.json()["data"]["id"]
        analysis_url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"
        result = requests.get(analysis_url, headers=headers).json()
        stats = result["data"]["attributes"]["stats"]
        return stats.get("malicious", 0) > 0 or stats.get("suspicious", 0) > 0
    except Exception as e:
        print("VT error:", e)
        return False

# OpenPhish
def check_openphish(url):
    try:
        response = requests.get("https://openphish.com/feed.txt", timeout=10)
        if response.status_code == 200:
            return url.strip() in response.text
        return False
    except Exception as e:
        print("OpenPhish error:", e)
        return False

# Проверка ссылкой через ML-модель
def check_with_model(url):
    try:
        X = vectorizer.fit_transform([url])
        prediction = model.predict(X)
        return prediction[0] == 1
    except Exception as e:
        print("ML model error:", e)
        return False

# Отправка уведомления владельцу
def notify_owner(original_message, sender_id):
    bot.send_message(chat_id=OWNER_ID, text=f"🚨 Suspicious link from {sender_id}:\n{original_message}")

# === Telegram-обработчики ===

def start(update: Update, context: CallbackContext):
    update.message.reply_text("👋 Send me a link and I will check if it's phishing.")

def handle_message(update: Update, context: CallbackContext):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    sender_id = update.message.from_user.id
    urls = re.findall(r'https?://\S+', user_text)

    if urls:
        flagged = False
        for url in urls:
            if (
                is_phishing_link(url)
                or check_google_safe_browsing(url)
                or check_virustotal(url)
                or check_openphish(url)
                or check_with_model(url)
            ):
                update.message.reply_text("⚠️ This might be a phishing link!")
                notify_owner(user_text, sender_id)
                flagged = True
        if not flagged:
            update.message.reply_text("✅ The link looks safe.")
    else:
        update.message.reply_text("Please send a valid link.")

# === Регистрация обработчиков ===

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# === Webhook ===

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

# === Запуск Flask ===

if __name__ == "__main__":
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    bot.set_webhook(url=webhook_url)
    app.run(host="0.0.0.0", port=PORT)
