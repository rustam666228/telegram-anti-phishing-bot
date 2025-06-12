import os
import re
import requests
import pandas as pd
import base64
import json
import joblib
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, MessageHandler, Filters, CommandHandler, CallbackContext
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression

# === Пути ===
MODEL_PATH = "phishing_model.pkl"
DATASET_PATH = "phishing_dataset.csv"

# === Проверка на модель ===
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError("❌ Модель phishing_model.pkl не найдена. Запусти train_model.py для её создания.")
model = joblib.load(MODEL_PATH)
vectorizer = CountVectorizer()

# === Обучение модели ===
def retrain_model():
    try:
        df = pd.read_csv(DATASET_PATH)
        X = df["url"]
        y = df["label"]
        X_vec = vectorizer.fit_transform(X)
        new_model = LogisticRegression()
        new_model.fit(X_vec, y)
        joblib.dump(new_model, MODEL_PATH)
        print("✅ Модель переобучена.")
    except Exception as e:
        print("❌ Ошибка обучения:", e)

# === Сохранение ссылки ===
def save_to_dataset(url, label):
    try:
        if os.path.exists(DATASET_PATH):
            df = pd.read_csv(DATASET_PATH)
        else:
            df = pd.DataFrame(columns=["url", "label"])

        if url not in df["url"].values:
            df.loc[len(df)] = [url, label]
            df.to_csv(DATASET_PATH, index=False)
            print(f"✅ URL сохранён: {url} -> {label}")
            commit_to_github(DATASET_PATH)  # <--- вот здесь
        else:
            print("ℹ️ URL уже в датасете.")
    except Exception as e:
        print("❌ Ошибка при сохранении в датасет:", e)
        
# === GitHub Commit ===

GITHUB_REPO = "rustam666228/telegram-anti-phishing-bot"
GITHUB_FILE = "phishing_dataset.csv"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
def commit_to_github(file_path):
    try:
        print("📤 Подготовка коммита в GitHub...")
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }

        with open(file_path, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")

        # Получаем SHA текущего файла
        get_resp = requests.get(api_url, headers=headers)
        sha = get_resp.json().get("sha")

        data = {
            "message": "🔄 Update dataset via bot",
            "content": content,
            "branch": "main",
        }
        if sha:
            data["sha"] = sha

        commit_response = requests.put(api_url, headers=headers, data=json.dumps(data))

        if commit_response.status_code in [200, 201]:
            print("✅ Изменения загружены в GitHub.")
        else:
            print("❌ Ошибка при коммите:", commit_response.status_code)
            print("Ответ:", commit_response.text)
    except Exception as e:
        print("❌ Ошибка при коммите в GitHub:", e)

# === Сохранение в CSV и GitHub ===

def save_to_dataset(url, label):
    try:
        print("🧪 Добавление в датасет...")

        if os.path.exists(DATASET_PATH):
            df = pd.read_csv(DATASET_PATH)
        else:
            df = pd.DataFrame(columns=["url", "label"])

        if url not in df["url"].values:
            df.loc[len(df)] = [url, label]
            df.to_csv(DATASET_PATH, index=False)
            print(f"✅ URL сохранён: {url} -> {label}")
            commit_to_github(DATASET_PATH)
        else:
            print("ℹ️ URL уже есть в датасете.")
    except Exception as e:
        print("❌ Ошибка при сохранении:", e)
        
# === Переменные окружения ===
TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
GSB_API_KEY = os.getenv("GSB_API_KEY")
VT_API_KEY = os.getenv("VT_API_KEY")
PORT = int(os.getenv("PORT", 8080))

# === Инициализация ===
bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=1)

# === Проверки ===
def is_phishing_link(url):
    patterns = ["login", "secure", ".xyz", ".zip", "@", "paypal", "verify"]
    return any(p in url.lower() for p in patterns)

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

def check_openphish(url):
    try:
        response = requests.get("https://openphish.com/feed.txt", timeout=10)
        return url.strip() in response.text if response.status_code == 200 else False
    except Exception as e:
        print("OpenPhish error:", e)
        return False

def check_with_model(url):
    try:
        X = vectorizer.fit_transform([url])
        prediction = model.predict(X)
        return prediction[0] == 1
    except Exception as e:
        print("ML model error:", e)
        return False

def notify_owner(original_message, sender_id):
    bot.send_message(chat_id=OWNER_ID, text=f"🚨 Suspicious link from {sender_id}:\n{original_message}")

# === Telegram команды ===

def start(update: Update, context: CallbackContext):
    update.message.reply_text("👋 Send me a link and I will check if it's phishing.")

def retrain(update: Update, context: CallbackContext):
    retrain_model()
    update.message.reply_text("🔁 Модель переобучена!")

def handle_message(update: Update, context: CallbackContext):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    sender_id = update.message.from_user.id
    urls = re.findall(r'https?://\S+', user_text)

    if urls:
        flagged = False
        for url in urls:
            phishing_detected = (
                is_phishing_link(url)
                or check_google_safe_browsing(url)
                or check_virustotal(url)
                or check_openphish(url)
                or check_with_model(url)
            )
            if phishing_detected:
                update.message.reply_text("⚠️ This might be a phishing link!")
                notify_owner(user_text, sender_id)
                save_to_dataset(url, 1)
                flagged = True
            else:
                save_to_dataset(url, 0)
        if not flagged:
            update.message.reply_text("✅ The link looks safe.")
    else:
        update.message.reply_text("Please send a valid link.")

# === Регистрация ===
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("retrain", retrain))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# === Webhook ===
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

# === Запуск ===
if __name__ == "__main__":
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    bot.set_webhook(url=webhook_url)
    app.run(host="0.0.0.0", port=PORT)
