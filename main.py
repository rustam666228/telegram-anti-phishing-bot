import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

TOKEN = os.getenv('TOKEN')
PORT = int(os.environ.get('PORT', '8443'))  # порт для Render, обычно 8080 или из переменной окружения

def start(update, context):
    update.message.reply_text("Привет! Отправь ссылку — я проверю её на фишинг.")

def handle_message(update, context):
    url = update.message.text.lower()
    if "login" in url or "secure" in url or ".xyz" in url:
        update.message.reply_text("⚠️ Это может быть фишинговая ссылка!")
    else:
        update.message.reply_text("✅ Ссылка выглядит безопасной.")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # Set webhook — сюда подставь URL, который Render даст (будет https://<твой-сервис>.onrender.com)
    WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/"  # Render задаст этот хостнейм

    # Запускаем webhook
    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=WEBHOOK_URL + TOKEN
    )
    updater.idle()

if __name__ == '__main__':
    main()
