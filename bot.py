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
        text=f"Ai selectat: **{client_name}**.\n\nAcum poți scrie mesajul tău (text, poză sau mesaj vocal)."
    )

async def handle_user_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    for admin_id in ADMIN_ID_LIST:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                parse_mode='Markdown'
            )
            sent_successfully = True
        except Exception as e:
            logger.error(f"Eroare la trimiterea mesajului către admin {admin_id}: {e}")

    if not sent_successfully:
        await update.message.reply_text(
            "A apărut o eroare la trimiterea mesajului. Te rog încearcă mai târziu."
        )
    else:
        # Confirmăm utilizatorului (optional, dar util)
        await update.message.reply_text("✅ Mesajul tău text a fost trimis.")

async def handle_user_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestionează mesajele FOTO de la utilizatori."""
    client_name = context.user_data.get('client_name')
    if not client_name:
        await update.message.reply_text(
            "Te rog selectează mai întâi un client folosind comanda /start."
        )
        return

    user = update.message.from_user
    user_id = user.id
    user_name = user.full_name
    
    photo_file_id = update.message.photo[-1].file_id # Cea mai mare rezoluție
    original_caption = update.message.caption or ""

    # Creăm noul caption pentru admin
    admin_caption = f"Poză NOUĂ de la: {user_name}\n"
    admin_caption += f"Pentru Client: **{client_name}**\n\n"
    if original_caption:
        admin_caption += f"Text original: {original_caption}\n\n"
    admin_caption += f"---\n"
    admin_caption += f"(UserID: {user_id})"

    sent_successfully = False
    for admin_id in ADMIN_ID_LIST:
        try:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=photo_file_id,
                caption=admin_caption,
                parse_mode='Markdown'
            )
            sent_successfully = True
        except Exception as e:
            logger.error(f"Eroare la trimiterea pozei către admin {admin_id}: {e}")

    if not sent_successfully:
        await update.message.reply_text(
            "A apărut o eroare la trimiterea fotografiei. Te rog încearcă mai târziu."
        )
    else:
        await update.message.reply_text("✅ Fotografia ta a fost trimisă.")

async def handle_user_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestionează mesajele VOCALE de la utilizatori."""
    client_name = context.user_data.get('client_name')
    if not client_name:
        await update.message.reply_text(
            "Te rog selectează mai întâi un client folosind comanda /start."
        )
        return

    user = update.message.from_user
    user_id = user.id
    user_name = user.full_name
    
    voice_file_id = update.message.voice.file_id

    # Creăm caption-ul pentru admin
    admin_caption = f"Mesaj VOCAL NOU de la: {user_name}\n"
    admin_caption += f"Pentru Client: **{client_name}**\n\n"
    admin_caption += f"---\n"
    admin_caption += f"(UserID: {user_id})"

    sent_successfully = False
    for admin_id in ADMIN_ID_LIST:
        try:
            await context.bot.send_voice(
                chat_id=admin_id,
                voice=voice_file_id,
                caption=admin_caption,
                parse_mode='Markdown'
            )
            sent_successfully = True
        except Exception as e:
            logger.error(f"Eroare la trimiterea mesajului vocal către admin {admin_id}: {e}")

    if not sent_successfully:
        await update.message.reply_text(
            "A apărut o eroare la trimiterea mesajului vocal. Te rog încearcă mai târziu."
        )
    else:
        await update.message.reply_text("✅ Mesajul tău vocal a fost trimis.")


async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestionează răspunsurile (text, poză, voce) venite de la ORICARE admin."""
    admin_message = update.message
    
    # Verificăm dacă adminul a dat reply la ceva
    if admin_message.reply_to_message:
        replied_message = admin_message.reply_to_message
        
        # Încercăm să găsim textul care conține UserID
        # Acesta poate fi în .text (pt mesaje text) sau .caption (pt media)
        text_to_search = replied_message.text or replied_message.caption
        
        if text_to_search:
            match = re.search(r"\(UserID: (\d+)\)", text_to_search)
            
            if match:
                original_user_id = int(match.group(1))
                
                try:
                    # Folosim copy_message pentru a trimite ORICE trimite adminul
                    # (text, poză, sticker, voce, etc.)
                    await admin_message.copy_message(
                        chat_id=original_user_id
                    )
                    await admin_message.reply_text("✅ Răspuns trimis utilizatorului.")
                
                except Exception as e:
                    logger.error(f"Eroare la trimiterea mesajului către {original_user_id}: {e}")
                    await admin_message.reply_text(f"❌ Eroare la trimiterea mesajului: {e}")
            else:
                # Adminul a dat reply, dar nu la un mesaj cu UserID
                await admin_message.reply_text(
                    "Nu am găsit un UserID în textul/caption-ul mesajului original. "
                    "Te rog folosește 'Reply' doar la mesajele primite de la utilizatori."
                )
        else:
            # Adminul a dat reply la un mesaj FĂRĂ text sau caption (ex: un sticker vechi)
            await admin_message.reply_text(
                "Acest mesaj la care ai dat reply nu conține datele utilizatorului."
            )
    else:
        # Adminul a scris un mesaj normal, nu un reply
        await admin_message.reply_text(
            "Pentru a răspunde unui utilizator, te rog folosește funcția 'Reply' "
            "direct la mesajul (text, poză, sau voce) primit de la el."
        )

def main():
    if not BOT_TOKEN or not ADMIN_ID_LIST:
        logger.error("Botul nu poate porni. Lipsesc BOT_TOKEN sau o listă validă de ADMIN_ID.")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click))
    
    # --- FILTRE PENTRU UTILIZATORI (cei care NU sunt admini) ---
    user_filter = ~filters.User(user_id=ADMIN_ID_LIST) & ~filters.COMMAND
    
    application.add_handler(MessageHandler(
        filters.TEXT & user_filter,
        handle_user_text
    ))
    application.add_handler(MessageHandler(
        filters.PHOTO & user_filter,
        handle_user_photo
    ))
    application.add_handler(MessageHandler(
        filters.VOICE & user_filter,
        handle_user_voice
    ))

    # --- FILTRU PENTRU ADMINI (oricare din listă) ---
    admin_filter = filters.User(user_id=ADMIN_ID_LIST) & ~filters.COMMAND
    
    # Adminul poate răspunde cu orice tip de mesaj
    application.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.VOICE | filters.STICKER) & admin_filter,
        handle_admin_reply
    ))

    print("Botul pornește (polling)...")
    application.run_polling()


if __name__ == "__main__":
    print("Se pornește serverul web (Flask)...")
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    main()
