"""
APScheduler jobs for daily picks and auto-archive.
"""

import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import DAILY_PICKS_TIME, DECAY_DAYS, NOTIFICATION_ENABLED
from database import (
    get_config, get_items_older_than, update_item_status,
    get_item_by_id
)
from claude_service import generate_daily_picks
from telegram_bot import send_telegram_message

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def send_daily_picks_notification():
    """
    Genera e invia daily picks via Telegram.
    Eseguito ogni mattina all'ora configurata.
    """
    logger.info("Running daily picks notification job")

    # Check if notifications enabled
    notification_enabled = await get_config('notification_enabled', 'true')
    if notification_enabled != 'true':
        logger.info("Notifications disabled - skipping daily picks")
        return

    # Get chat ID
    chat_id = await get_config('telegram_chat_id', '')
    if not chat_id:
        logger.warning("No chat_id configured - skipping notification")
        return

    # Generate picks
    result = await generate_daily_picks()

    if not result or not result.get('picks'):
        logger.info("No picks generated today")
        return

    # Format message
    message = f"Buongiorno! {result.get('message', '')}\n\n"
    message += "I tuoi picks di oggi:\n\n"

    for idx, pick_data in enumerate(result['picks'], 1):
        item = pick_data.get('item', {})
        title = item.get('title', 'Senza titolo')
        item_type = item.get('item_type', 'other')
        minutes = item.get('estimated_minutes', '?')
        reason = pick_data.get('reason', '')

        message += f"{idx}. {title} ({item_type})\n"
        message += f"   {minutes}min\n"
        if reason:
            message += f"   {reason}\n"
        message += "\n"

    message += f"Tempo totale: ~{result.get('total_estimated_time', 0)}min\n\n"
    message += "Vedi la dashboard per i dettagli!"

    # Send via Telegram
    await send_telegram_message(chat_id, message)
    logger.info(f"Daily picks notification sent with {len(result['picks'])} picks")


async def auto_archive_old_items():
    """
    Archivia automaticamente item pending da >N giorni.
    Eseguito ogni notte.
    """
    logger.info("Running auto-archive job")

    decay_days = int(await get_config('decay_days', str(DECAY_DAYS)))
    old_items = await get_items_older_than(decay_days, status='pending')

    if not old_items:
        logger.info("No items to auto-archive")
        return

    archived_count = 0
    for item in old_items:
        success = await update_item_status(item['id'], 'archived')
        if success:
            archived_count += 1

    logger.info(f"Auto-archived {archived_count} items")

    # Notify user if items were archived
    if archived_count > 0:
        chat_id = await get_config('telegram_chat_id', '')
        if chat_id:
            notification_enabled = await get_config('notification_enabled', 'true')
            if notification_enabled == 'true':
                await send_telegram_message(
                    chat_id,
                    f"Auto-archiviati {archived_count} item da >{decay_days} giorni.\n"
                    f"Niente stress, puoi sempre recuperarli dall'archivio!"
                )


def init_scheduler():
    """Initialize scheduler with jobs."""
    # Parse daily picks time
    try:
        hour, minute = DAILY_PICKS_TIME.split(':')
        hour = int(hour)
        minute = int(minute)
    except (ValueError, AttributeError):
        hour, minute = 8, 0  # Default to 8:00

    # Daily picks (morning)
    scheduler.add_job(
        send_daily_picks_notification,
        CronTrigger(hour=hour, minute=minute),
        id='daily_picks',
        replace_existing=True
    )
    logger.info(f"Scheduled daily picks at {hour:02d}:{minute:02d}")

    # Auto-archive (every night at 2am)
    scheduler.add_job(
        auto_archive_old_items,
        CronTrigger(hour=2, minute=0),
        id='auto_archive',
        replace_existing=True
    )
    logger.info("Scheduled auto-archive at 02:00")

    return scheduler


def start_scheduler():
    """Start the scheduler."""
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def stop_scheduler():
    """Stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
