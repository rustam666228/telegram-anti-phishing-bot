
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from keep_alive import keep_alive

TOKEN = '7948228973:AAFJfZGJ0mm9prjjvosR5IVNT5aHNCkOYoI'

def start(update, context):
    update.message.reply_text("Привет! Отправь ссылку — я проверю её на фишинг.")

def handle_message(update, context):
    url = update.message.text.lower()
    if "login" in url or "secure" in url or ".xyz" in url:
        update.message.reply_text("⚠️ Это может быть фишинговая ссылка!")
    else:
        update.message.reply_text("✅ Ссылка выглядит безопасной.")

def main():
    keep_alive()
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
