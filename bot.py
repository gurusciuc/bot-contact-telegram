import logging
import threading
import os
import re
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    CallbackQueryHandler
)

# --- LISTA TA DE CLIENȚI ---
CLIENT_NAMES = [
    "Piata.md", 
    "Sport.md", 
    "OpenNotes", 
    "GetOut.md", 
    "Jukebox.md", 
    "Preturi.md"
]
# -----------------------------

# --- Se citesc secretele din Environment Variables ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# Citim string-ul cu ID-uri (ex: "123456,987654")
ADMIN_IDS_STR = os.environ.get("ADMIN_ID")
# ----------------------------------------------------

# Inițializăm logger-ul
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Procesăm lista de ADMINI ---
ADMIN_ID_LIST = []  # Lista goală care va ține ID-urile
if not BOT_TOKEN:
    logger.error("Eroare: BOT_TOKEN nu este setat!")
if not ADMIN_IDS_STR:
    logger.error("Eroare: ADMIN_ID nu este setat!")
else:
    # Despărțim string-ul după virgulă
    id_strings = ADMIN_IDS_STR.split(',')
    for id_str in id_strings:
        try:
            # Adăugăm fiecare ID (ca număr) în listă
            ADMIN_ID_LIST.append(int(id_str.strip())) # .strip() elimină spații accidentale
        except ValueError:
            logger.error(f"Eroare: ADMIN_ID '{id_str}' nu este un număr valid!")
    
    if not ADMIN_ID_LIST:
        logger.error("Eroare: Niciun ADMIN_ID valid nu a fost găsit!")
    else:
        logger.info(f"Bot pornit. Admini încărcați: {ADMIN_ID_LIST}")
# -------------------------------


# --- Partea pentru serverul web (Flask) ---
app = Flask(__name__)

@app.route('/')
def hello():
    return "Botul este activ!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)
# ----------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Trimite meniul de selecție la comanda /start."""
    keyboard = [
        [InlineKeyboardButton(CLIENT_NAMES[0], callback_data=CLIENT_NAMES[0]),
         InlineKeyboardButton(CLIENT_NAMES[1], callback_data=CLIENT_NAMES[1])],
        [InlineKeyboardButton(CLIENT_NAMES[2], callback_data=CLIENT_NAMES[2]),
         InlineKeyboardButton(CLIENT_NAMES[3], callback_data=CLIENT_NAMES[3])],
        [InlineKeyboardButton(CLIENT_NAMES[4], callback_data=CLIENT_NAMES[4]),
         InlineKeyboardButton(CLIENT_NAMES[5], callback_data=CLIENT_NAMES[5])]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Salut! Te rog selectează clientul pentru care vrei să trimiți un mesaj:",
        reply_markup=reply_markup
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestionează apăsarea butoanelor din meniu."""
    query = update.callback_query
    await query.answer()
    client_name = query.data
    context.user_data['client_name'] = client_name
    await query.edit_message_text(
        text=f"Ai selectat: **{client_name}**.\n\nAcum poți scrie mesajul tău."
    )

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestionează mesajele text de la utilizatori."""
    client_name = context.user_data.get('client_name')
    if not client_name:
        await update.message.reply_text(
            "Te rog selectează mai întâi un client folosind comanda /start."
        )
        return

    user = update.message.from_user
    user_id = user.id
    user_name = user.full_name
    message_text = update.message.text

    admin_text = f"Mesaj NOU de la: {user_name}\n"
    admin_text += f"Pentru Client: **{client_name}**\n\n"
    admin_text += f"{message_text}\n\n"
    admin_text += f"---\n"
    admin_text += f"(UserID: {user_id})"

    sent_successfully = False
    # --- MODIFICARE AICI: Trimitem la TOȚI adminii din listă ---
    for admin_id in ADMIN_ID_LIST:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                parse_mode='Markdown'
            )
            sent_successfully = True # E de ajuns dacă a ajuns la unul
        except Exception as e:
            logger.error(f"Eroare la trimiterea mesajului către admin {admin_id}: {e}")

    if not sent_successfully:
        # Anunțăm utilizatorul doar dacă a eșuat trimiterea la TOȚI adminii
        await update.message.reply_text(
            "A apărut o eroare la trimiterea mesajului. Te rog încearcă mai târziu."
        )


async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestionează răspunsurile venite de la ORICARE admin."""
    admin_message = update.message
    
    if admin_message.reply_to_message and admin_message.reply_to_message.text:
        replied_text = admin_message.reply_to_message.text
        match = re.search(r"\(UserID: (\d+)\)", replied_text)
        
        if match:
            original_user_id = int(match.group(1))
            admin_response_text = admin_message.text
            
            try:
                await context.bot.send_message(
                    chat_id=original_user_id,
                    text=admin_response_text
                )
                await admin_message.reply_text("✅ Răspuns trimis utilizatorului.")
            except Exception as e:
                logger.error(f"Eroare la trimiterea mesajului către {original_user_id}: {e}")
                await admin_message.reply_text(f"❌ Eroare la trimiterea mesajului: {e}")
        else:
            await admin_message.reply_text(
                "Nu am găsit un UserID. Folosește 'Reply' doar la mesajele primite de la utilizatori."
            )
    else:
        await admin_message.reply_text(
            "Pentru a răspunde unui utilizator, te rog folosește funcția 'Reply' "
            "direct la mesajul primit de la el."
        )

def main():
    # Verificăm dacă lista de admini nu e goală
    if not BOT_TOKEN or not ADMIN_ID_LIST:
        logger.error("Botul nu poate porni. Lipsesc BOT_TOKEN sau o listă validă de ADMIN_ID.")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click))
    
    # --- MODIFICARE AICI: Folosim lista de admini ---
    application.add_handler(MessageHandler(
        filters.TEXT & (~filters.COMMAND) & (~filters.User(user_id=ADMIN_ID_LIST)),
        handle_user_message
    ))

    # --- MODIFICARE AICI: Folosim lista de admini ---
    application.add_handler(MessageHandler(
        filters.TEXT & (~filters.COMMAND) & filters.User(user_id=ADMIN_ID_LIST),
        handle_admin_reply
    ))

    print("Botul pornește (polling)...")
    application.run_polling()


if __name__ == "__main__":
    print("Se pornește serverul web (Flask)...")
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    main()
