"""
Telegram bot handlers for ADHD Thought Capture.
"""

import asyncio
import logging
from typing import Optional

from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from config import TELEGRAM_BOT_TOKEN, DASHBOARD_URL
from database import get_config, save_config, get_user_stats, get_daily_picks_for_date
from llm_service import classify_and_enrich, classify_and_enrich_image, generate_daily_picks, get_daily_picks_with_items
from datetime import datetime

logger = logging.getLogger(__name__)

# Global bot instance for sending messages from scheduler
bot_instance: Optional[Bot] = None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start - onboarding iniziale."""
    user_id = update.effective_user.id

    # Salva chat_id in config
    await save_config('telegram_chat_id', str(user_id))

    await update.message.reply_text(
        "Ciao! Sono il tuo assistente per catturare pensieri veloci.\n\n"
        "Mandami qualsiasi cosa ti passa per la testa:\n"
        "- Titolo di un film\n"
        "- Nome di un libro\n"
        "- Un concetto da approfondire\n"
        "- Un'idea random\n\n"
        "Capisco cosa intendi e te lo organizzo.\n\n"
        "Comandi:\n"
        "/background - Imposta il tuo profilo (opzionale)\n"
        "/stats - Vedi statistiche\n"
        "/today - Suggerimenti del giorno\n"
        "/help - Mostra questo messaggio"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help - mostra aiuto."""
    await update.message.reply_text(
        "Come funziona:\n\n"
        "1. Mandami un pensiero qualsiasi\n"
        "2. Oppure mandami una foto/screenshot\n"
        "3. Lo salvo e lo classifico automaticamente\n"
        "4. Trovo link utili per approfondire\n"
        "5. Te lo ripropongo quando opportuno\n\n"
        "Comandi disponibili:\n"
        "/start - Inizia\n"
        "/background - Imposta interessi e preferenze\n"
        "/stats - Le tue statistiche\n"
        "/today - Picks di oggi\n"
        "/help - Questo messaggio\n\n"
        f"Dashboard: {DASHBOARD_URL}"
    )


async def background_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /background - imposta profilo utente."""
    # Check if already setting background
    if context.user_data.get('awaiting_background'):
        await update.message.reply_text(
            "Sto gia aspettando il tuo profilo! Mandami un testo con i tuoi interessi."
        )
        return

    current_bg = await get_config('user_background', '')

    message = "Parlami di te! Scrivi un testo libero con:\n"
    message += "- Interessi, passioni, ossessioni\n"
    message += "- Cose che ami\n"
    message += "- Cose che odi\n\n"
    message += "Es: 'Amo cinema d'autore, sci-fi cerebrale tipo Blade Runner, "
    message += "musica elettronica ambient, filosofia continentale. "
    message += "Odio action stupidi e pop commerciale.'\n\n"
    message += "Questo mi aiutera a capire meglio i tuoi pensieri."

    if current_bg:
        message += f"\n\nProfilo attuale:\n\"{current_bg[:200]}{'...' if len(current_bg) > 200 else ''}\""

    await update.message.reply_text(message)
    context.user_data['awaiting_background'] = True


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /stats - mostra statistiche."""
    stats = await get_user_stats()

    message = "Le tue statistiche:\n\n"
    message += f"Catturati: {stats['total_captured']}\n"
    message += f"Consumati: {stats['total_consumed']}\n"
    message += f"In coda: {stats['pending']}\n"
    message += f"Archiviati: {stats['archived']}\n"
    message += f"Streak: {stats['streak_days']} giorni\n"
    message += f"Ratio: {stats['consumption_rate']:.1f}%\n\n"
    message += f"Dashboard: {DASHBOARD_URL}"

    await update.message.reply_text(message)


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /today - mostra daily picks."""
    today = datetime.now().strftime('%Y-%m-%d')

    # Try to get existing picks
    picks_data = await get_daily_picks_with_items(today)

    if not picks_data:
        # Generate new picks
        await update.message.reply_text("Genero i suggerimenti di oggi...")
        picks_data = await generate_daily_picks()

    if not picks_data or not picks_data.get('picks'):
        await update.message.reply_text(
            "Nessun suggerimento per oggi.\n"
            "Cattura qualche pensiero e torna piu tardi!"
        )
        return

    message = f"I tuoi picks di oggi:\n\n"

    for idx, pick in enumerate(picks_data['picks'], 1):
        item = pick.get('item', {})
        title = item.get('title', 'Senza titolo')
        item_type = item.get('item_type', 'other')
        minutes = item.get('estimated_minutes', '?')

        message += f"{idx}. {title} ({item_type})\n"
        message += f"   {minutes}min\n"
        if pick.get('reason'):
            message += f"   {pick['reason']}\n"
        message += "\n"

    message += f"Tempo totale: ~{picks_data.get('total_estimated_time', 0)}min\n"

    if picks_data.get('message'):
        message += f"\n{picks_data['message']}"

    await update.message.reply_text(message)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler per messaggi generici."""

    # Se sta impostando background
    if context.user_data.get('awaiting_background'):
        background_text = update.message.text
        await save_config('user_background', background_text)
        context.user_data['awaiting_background'] = False

        await update.message.reply_text(
            "Profilo salvato! Ora capiro meglio i tuoi pensieri."
        )
        return

    # Altrimenti è un nuovo pensiero da catturare
    verbatim = update.message.text
    msg_id = update.message.message_id

    # Conferma immediata (UX: non sembra muto)
    await update.message.reply_text("Salvato")

    # Processing asincrono
    try:
        result = await classify_and_enrich(verbatim, msg_id)

        # Send enriched confirmation
        type_emoji = {
            'film': 'Film',
            'book': 'Libro',
            'concept': 'Concetto',
            'music': 'Musica',
            'art': 'Arte',
            'todo': 'Todo',
            'other': 'Altro'
        }

        response = f"{type_emoji.get(result['type'], 'Altro')}: {result['title']}\n"
        response += f"{result['estimated_minutes']}min | Priorita {result['priority']}"

        if result.get('links') and len(result['links']) > 0:
            response += f"\nLink: {result['links'][0].get('url', '')[:50]}..."

        await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Error processing thought: {e}")
        # The fallback in classify_and_enrich should handle this


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler per foto/immagini."""

    # Get the largest photo (best quality)
    photo = update.message.photo[-1]  # Last element is highest resolution
    msg_id = update.message.message_id
    caption = update.message.caption  # Optional caption

    # Conferma immediata
    await update.message.reply_text("Immagine ricevuta, analizzo...")

    try:
        # Download photo from Telegram
        photo_file = await photo.get_file()
        image_bytes = await photo_file.download_as_bytearray()

        # Determine mime type (Telegram photos are always JPEG)
        mime_type = "image/jpeg"

        # Process with Gemini
        result = await classify_and_enrich_image(
            image_bytes=bytes(image_bytes),
            mime_type=mime_type,
            caption=caption,
            msg_id=msg_id
        )

        # Send enriched confirmation
        type_emoji = {
            'film': 'Film',
            'book': 'Libro',
            'concept': 'Concetto',
            'music': 'Musica',
            'art': 'Arte',
            'todo': 'Todo',
            'other': 'Altro'
        }

        response = f"{type_emoji.get(result['type'], 'Altro')}: {result['title']}\n"
        response += f"{result['estimated_minutes']}min | Priorita {result['priority']}"

        if result.get('description'):
            response += f"\n\n{result['description'][:200]}"

        if result.get('links') and len(result['links']) > 0:
            response += f"\n\nLink: {result['links'][0].get('url', '')[:50]}..."

        await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await update.message.reply_text(
            "Non sono riuscito ad analizzare l'immagine. "
            "Prova con un'altra foto o aggiungi una descrizione testuale."
        )


async def send_telegram_message(chat_id: str, message: str):
    """Send a message to a specific chat (for scheduler)."""
    global bot_instance

    if not bot_instance:
        if not TELEGRAM_BOT_TOKEN:
            logger.error("Cannot send message: no bot token")
            return
        bot_instance = Bot(token=TELEGRAM_BOT_TOKEN)

    try:
        await bot_instance.send_message(chat_id=chat_id, text=message)
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")


def create_bot_application() -> Optional[Application]:
    """Create and configure the Telegram bot application."""
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set - bot will not start")
        return None

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("background", background_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("today", today_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Store bot instance for scheduler
    global bot_instance
    bot_instance = app.bot

    return app


async def run_bot():
    """Run the Telegram bot with polling."""
    app = create_bot_application()

    if not app:
        logger.warning("Bot not configured - skipping")
        return

    logger.info("Starting Telegram bot...")

    # Initialize and start polling
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    logger.info("Telegram bot is running")

    # Keep running until stopped
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("Stopping Telegram bot...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


async def stop_bot(app: Application):
    """Stop the Telegram bot gracefully."""
    if app and app.running:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
