import os
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- ÎNLOCUIEȘTE ASTA ---
# --- Se citesc secretele din Environment Variables ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID_STR = os.environ.get("ADMIN_ID")
# ----------------------------------------------------

# Verificăm dacă variabilele există
if not BOT_TOKEN:
    logger.error("Eroare: BOT_TOKEN nu este setat!")
if not ADMIN_ID_STR:
    logger.error("Eroare: ADMIN_ID nu este setat!")
else:
    # Convertim ADMIN_ID din text în număr, pentru că filtrele au nevoie de număr
    ADMIN_ID = int(ADMIN_ID_STR)

# --- Partea pentru serverul web (Flask) ---
# Acest server web rulează doar ca să țină serviciul Render activ
app = Flask(__name__)

@app.route('/')
def hello():
    # Când UptimeRobot vizitează adresa, va primi acest mesaj
    return "Botul este activ!"

def run_flask():
    # Rulează serverul web pe portul 0.0.0.0,
    # Render va detecta automat portul.
    app.run(host='0.0.0.0', port=8080)
# ----------------------------------------

# Activează logging-ul pentru a vedea erorile
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salut! Eu sunt un bot de contact. "
        "Trimite-mi mesajul tău și îl voi transmite administratorului."
    )

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message
    await context.bot.forward_message(
        chat_id=ADMIN_ID,
        from_chat_id=user_message.chat_id,
        message_id=user_message.message_id
    )
    await update.message.reply_text("Mesajul tău a fost trimis administratorului. Vei primi răspuns în curând.")

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_message = update.message
    if admin_message.reply_to_message and admin_message.reply_to_message.forward_from:
        original_user_id = admin_message.reply_to_message.forward_from.id
        try:
            await context.bot.send_message(
                chat_id=original_user_id,
                text=f"Răspuns de la administrator:\n\n{admin_message.text}"
            )
            await admin_message.reply_text("✅ Răspuns trimis utilizatorului.")
        except Exception as e:
            logger.error(f"Eroare la trimiterea mesajului către {original_user_id}: {e}")
            await admin_message.reply_text(f"❌ Eroare la trimiterea mesajului: {e}")
    else:
        await admin_message.reply_text(
            "Pentru a răspunde unui utilizator, te rog folosește funcția 'Reply' "
            "direct la mesajul forwardat de la el."
        )

def main():
    # Creăm aplicația bot-ului
    application = Application.builder().token(BOT_TOKEN).build()

    # Adăugăm handlerele
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(
        filters.TEXT & (~filters.COMMAND) & (~filters.User(chat_id=ADMIN_ID)),
        handle_user_message
    ))
    application.add_handler(MessageHandler(
        filters.TEXT & (~filters.COMMAND) & filters.User(chat_id=ADMIN_ID),
        handle_admin_reply
    ))

    # Pornim botul
    print("Botul pornește (polling)...")
    application.run_polling()


if __name__ == "__main__":
    # Pornim serverul Flask pe un thread separat
    print("Se pornește serverul web (Flask)...")
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    # Pornim botul pe thread-ul principal
    main()
