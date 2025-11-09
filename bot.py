import logging
import threading
import os
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Se citesc secretele din Environment Variables ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID_STR = os.environ.get("ADMIN_ID")
# ----------------------------------------------------

# Inițializăm logger-ul
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Verificăm variabilele și convertim ADMIN_ID
if not BOT_TOKEN:
    logger.error("Eroare: BOT_TOKEN nu este setat!")
if not ADMIN_ID_STR:
    logger.error("Eroare: ADMIN_ID nu este setat!")
else:
    try:
        ADMIN_ID = int(ADMIN_ID_STR) 
    except ValueError:
        logger.error(f"Eroare: ADMIN_ID '{ADMIN_ID_STR}' nu este un număr valid!")
        ADMIN_ID = None  # Setăm ca None dacă e invalid

# --- Partea pentru serverul web (Flask) ---
app = Flask(__name__)

@app.route('/')
def hello():
    return "Botul este activ!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)
# ----------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salut! Eu sunt un bot de contact. "
        "Trimite-mi mesajul tău și îl voi transmite clientului."  # <-- SCHIMBAT AICI
    )

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message
    await context.bot.forward_message(
        chat_id=ADMIN_ID,
        from_chat_id=user_message.chat_id,
        message_id=user_message.message_id
    )
    await update.message.reply_text("Mesajul tău a fost trimis clientului. Vei primi răspuns în curând.") # <-- SCHIMBAT AICI

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestionează răspunsurile venite de la 'client' (admin)."""
    admin_message = update.message
    
    if (
        admin_message.reply_to_message 
        and admin_message.reply_to_message.forward_origin
        and admin_message.reply_to_message.forward_origin.sender_user
    ):
        original_user_id = admin_message.reply_to_message.forward_origin.sender_user.id
        
        try:
            await context.bot.send_message(
                chat_id=original_user_id,
                text=f"Răspuns de la client:\n\n{admin_message.text}" # <-- SCHIMBAT AICI
            )
            await admin_message.reply_text("✅ Răspuns trimis utilizatorului.")
        except Exception as e:
            logger.error(f"Eroare la trimiterea mesajului către {original_user_id}: {e}")
            await admin_message.reply_text(f"❌ Eroare la trimiterea mesajului: {e}")
            
    else:
        # Acest mesaj este pentru TINE (client), deci e corect să-i spună
        # cum să răspundă unui "utilizator".
        await admin_message.reply_text(
            "Pentru a răspunde unui utilizator, te rog folosește funcția 'Reply' "
            "direct la mesajul forwardat de la el."
        )

def main():
    if not BOT_TOKEN or not ADMIN_ID:
        logger.error("Botul nu poate porni. Lipsesc BOT_TOKEN sau ADMIN_ID.")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    
    application.add_handler(MessageHandler(
        filters.TEXT & (~filters.COMMAND) & (~filters.User(user_id=ADMIN_ID)),
        handle_user_message
    ))

    application.add_handler(MessageHandler(
        filters.TEXT & (~filters.COMMAND) & filters.User(user_id=ADMIN_ID),
        handle_admin_reply
    ))

    print("Botul pornește (polling)...")
    application.run_polling()


if __name__ == "__main__":
    print("Se pornește serverul web (Flask)...")
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    main()
