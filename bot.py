import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Activează logging-ul pentru a vedea erorile
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- ÎNLOCUIEȘTE ASTA ---
BOT_TOKEN = "8488400132:AAEJwwSWlzaZkZmRW9buIiN10weS2iPtlL4"  # <-- Pune aici Token-ul de la BotFather
ADMIN_ID = 5653038722            # <-- Pune aici ID-ul tău de la userinfobot
# -------------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Trimite un mesaj de întâmpinare când cineva pornește botul."""
    await update.message.reply_text(
        "Salut! Eu sunt un bot de contact. "
        "Trimite-mi mesajul tău și îl voi transmite administratorului."
    )


async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestionează mesajele primite de la utilizatori (non-admin)."""
    user_message = update.message
    
    # Trimite (forwardează) mesajul utilizatorului către administrator
    await context.bot.forward_message(
        chat_id=ADMIN_ID,
        from_chat_id=user_message.chat_id,
        message_id=user_message.message_id
    )
    
    await update.message.reply_text("Mesajul tău a fost trimis administratorului. Vei primi răspuns în curând.")


async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestionează răspunsurile venite de la administrator."""
    admin_message = update.message
    
    # Verificăm dacă mesajul adminului este un RĂSPUNS (Reply)
    # și dacă răspunde la un mesaj FORWARDAT
    if admin_message.reply_to_message and admin_message.reply_to_message.forward_from:
        # Aflăm ID-ul utilizatorului original din mesajul forwardat
        original_user_id = admin_message.reply_to_message.forward_from.id
        
        # Trimitem textul scris de admin către utilizatorul original
        try:
            await context.bot.send_message(
                chat_id=original_user_id,
                text=f"Răspuns de la administrator:\n\n{admin_message.text}"
            )
            # Confirmăm adminului că mesajul a fost trimis
            await admin_message.reply_text("✅ Răspuns trimis utilizatorului.")
        except Exception as e:
            logger.error(f"Eroare la trimiterea mesajului către {original_user_id}: {e}")
            await admin_message.reply_text(f"❌ Eroare la trimiterea mesajului: {e}")
            
    else:
        # Dacă adminul doar scrie botului fără să dea "Reply", îl informăm
        await admin_message.reply_text(
            "Pentru a răspunde unui utilizator, te rog folosește funcția 'Reply' "
            "direct la mesajul forwardat de la el."
        )


def main():
    """Funcția principală care pornește botul."""
    # Creăm aplicația bot-ului
    application = Application.builder().token(BOT_TOKEN).build()

    # 1. Adăugăm handler pentru comanda /start (pentru toți)
    application.add_handler(CommandHandler("start", start))

    # 2. Adăugăm handler pentru mesajele de la UTILIZATORI
    application.add_handler(MessageHandler(
        filters.TEXT & (~filters.COMMAND) & (~filters.User(chat_id=ADMIN_ID)),
        handle_user_message
    ))

    # 3. Adăugăm handler pentru mesajele de la ADMIN
    application.add_handler(MessageHandler(
        filters.TEXT & (~filters.COMMAND) & filters.User(chat_id=ADMIN_ID),
        handle_admin_reply
    ))

    # Pornim botul (rămâne activ până îl oprești cu Ctrl+C)
    print("Botul pornește...")
    application.run_polling()


if __name__ == "__main__":
    main()