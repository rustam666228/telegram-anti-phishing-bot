import os
import re
import json
import requests
from datetime import datetime
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, MessageHandler, Filters, CommandHandler, CallbackContext

# Настройки
TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
GSB_API_KEY = os.getenv("GSB_API_KEY")
VT_API_KEY = os.getenv("VT_API_KEY")
PORT = int(os.getenv("PORT", 8080))

bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=1)

# Эвристика
def is_phishing_link(url):
    patterns = ["login", "secure", ".xyz", ".zip", "@", "paypal", "verify"]
    return any(p in url.lower() for p in patterns)

# Google Safe Browsing
def check_google_safe_browsing(url):
    endpoint = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={GSB_API_KEY}"
    payload = {
        "client": {"clientId": "phishing-bot", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
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

# VirusTotal
def check_virustotal(url):
    headers = {"x-apikey": VT_API_KEY}
    try:
        resp = requests.post("https://www.virustotal.com/api/v3/urls", headers=headers, data={"url": url})
        if resp.status_code != 200:
            return False
        analysis_id = resp.json()["data"]["id"]
        result = requests.get(f"https://www.virustotal.com/api/v3/analyses/{analysis_id}", headers=headers).json()
        stats = result["data"]["attributes"]["stats"]
        return stats["malicious"] > 0 or stats["suspicious"] > 0
    except Exception as e:
        print("VT error:", e)
        return False

# OpenPhish
def check_openphish(url):
    try:
        response = requests.get("https://openphish.com/feed.txt", timeout=10)
        if response.status_code == 200:
            phishing_urls = response.text.splitlines()
            return any(url.strip() in entry for entry in phishing_urls)
        return False
    except Exception as e:
        print("OpenPhish error:", e)
        return False

# Уведомление
def notify_owner(message, sender_id):
    bot.send_message(chat_id=OWNER_ID, text=f"🚨 Suspicious link from {sender_id}:\n{message}")

# Логирование в JSON
def log_incident(sender_id, url, is_phishing, methods):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "sender_id": sender_id,
        "url": url,
        "result": "phishing" if is_phishing else "safe",
        "detected_by": methods
    }
    try:
        if not os.path.exists("logs.json"):
            with open("logs.json", "w") as f:
                json.dump([log_entry], f, indent=2)
        else:
            with open("logs.json", "r+") as f:
                data = json.load(f)
                data.append(log_entry)
                f.seek(0)
                json.dump(data, f, indent=2)
    except Exception as e:
        print("Logging error:", e)

# /start
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Hi! Send me a link and I will check if it's phishing.")

# Обработка
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
            if is_phishing_link(url):
                methods.append("heuristic")
            if check_google_safe_browsing(url):
                methods.append("google_safe_browsing")
            if check_virustotal(url):
                methods.append("virustotal")
            if check_openphish(url):
                methods.append("openphish")

            if methods:
                update.message.reply_text("⚠️ This might be a phishing link!")
                notify_owner(user_text, sender_id)
                flagged = True
            log_incident(sender_id, url, bool(methods), methods)

        if not flagged:
            update.message.reply_text("✅ The link looks safe.")
    else:
        update.message.reply_text("Please send a valid link.")

# Хендлеры
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
