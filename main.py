import os
import re
import csv
import requests
from datetime import datetime
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, MessageHandler, Filters, CommandHandler, CallbackContext
import joblib

# === НАСТРОЙКИ ===
TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
GSB_API_KEY = os.getenv("GSB_API_KEY")
VT_API_KEY = os.getenv("VT_API_KEY")
PORT = int(os.getenv("PORT", 8080))
MODEL_PATH = "phishing_model.pkl"

bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=1)

# === ML-МОДЕЛЬ ===
model = None
if os.path.exists(MODEL_PATH):
    model = joblib.load(MODEL_PATH)

def extract_features(url):
    return [
        len(url),
        int("@" in url),
        int("login" in url.lower()),
        int("secure" in url.lower()),
        int("paypal" in url.lower()),
        url.count("."),
        url.count("="),
        url.count("?")
    ]

# === ПРОВЕРКИ ===
def is_phishing_link(url):
    patterns = ["login", "secure", ".xyz", ".zip", "@", "paypal", "verify"]
    return any(p in url.lower() for p in patterns)

def check_google_safe_browsing(url):
    try:
        endpoint = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={GSB_API_KEY}"
        payload = {
            "client": {"clientId": "phishing-bot", "clientVersion": "1.0"},
            "threatInfo": {
                "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING"],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": url}]
            }
        }
        r = requests.post(endpoint, json=payload)
        return bool(r.json().get("matches"))
    except:
        return False

def check_virustotal(url):
    try:
        headers = {"x-apikey": VT_API_KEY}
        resp = requests.post("https://www.virustotal.com/api/v3/urls", headers=headers, data={"url": url})
        if resp.status_code != 200:
            return False
        analysis_id = resp.json()["data"]["id"]
        result = requests.get(f"https://www.virustotal.com/api/v3/analyses/{analysis_id}", headers=headers).json()
        stats = result["data"]["attributes"]["stats"]
        return stats["malicious"] > 0 or stats["suspicious"] > 0
    except:
        return False

# === CSV-ЛОГГЕР ===
def log_to_csv(sender_id, url, is_phishing, methods):
    path = "phishing_dataset.csv"
    label = "phishing" if is_phishing else "safe"
    entry = [sender_id, url, label, ";".join(methods), datetime.utcnow().isoformat()]
    write_header = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["sender_id", "url", "label", "detected_by", "timestamp"])
        writer.writerow(entry)

# === УВЕДОМЛЕНИЕ ===
def notify_owner(message, sender_id):
    bot.send_message(chat_id=OWNER_ID, text=f"🚨 Suspicious link from {sender_id}:\n{message}")

# === ОБРАБОТЧИКИ ===
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Hi! Send me a link and I'll check it.")

def handle_message(update: Update, context: CallbackContext):
    if not update.message or not update.message.text:
        return
    user_text = update.message.text
    sender_id = update.message.from_user.id
    urls = re.findall(r'(https?://[^\s]+|www\.[^\s]+)', user_text)
    if urls:
        flagged = False
        for url in urls:
            methods = []
            if is_phishing_link(url): methods.append("heuristic")
            if check_google_safe_browsing(url): methods.append("google")
            if check_virustotal(url): methods.append("virustotal")
            if model:
                prediction = model.predict([extract_features(url)])[0]
                if prediction == "phishing": methods.append("ml_model")

            if methods:
                update.message.reply_text("⚠️ This might be a phishing link!")
                notify_owner(user_text, sender_id)
                flagged = True

            log_to_csv(sender_id, url, bool(methods), methods)

        if not flagged:
            update.message.reply_text("✅ The link looks safe.")
    else:
        update.message.reply_text("Please send a valid link.")

# === РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ===
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# === WEBHOOK ===
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

if __name__ == "__main__":
    bot.set_webhook(url=f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}")
    app.run(host="0.0.0.0", port=PORT)
