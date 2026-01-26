"""
Push notification service for ThoughtCapture PWA.
Sends web push notifications using the Web Push protocol and VAPID.
"""

import json
import logging
from typing import Optional, Dict, Any, List

from config import VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_CLAIMS_EMAIL

logger = logging.getLogger(__name__)

# Try to import pywebpush, but handle if not installed
try:
    from pywebpush import webpush, WebPushException
    PUSH_AVAILABLE = bool(VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY)
except ImportError:
    PUSH_AVAILABLE = False
    logger.warning("pywebpush not installed - push notifications disabled")


async def send_push_notification(
    subscription: Dict[str, Any],
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    tag: str = "default",
    actions: Optional[List[Dict[str, str]]] = None
) -> bool:
    """
    Send a push notification to a single subscription.

    Args:
        subscription: Push subscription object with endpoint and keys
        title: Notification title
        body: Notification body text
        data: Optional additional data to send
        tag: Notification tag for grouping
        actions: Optional list of action buttons

    Returns:
        True if notification sent successfully, False otherwise
    """
    if not PUSH_AVAILABLE:
        logger.warning("Push notifications not available")
        return False

    if not subscription.get('endpoint'):
        logger.warning("Invalid subscription - no endpoint")
        return False

    payload = {
        "title": title,
        "body": body,
        "tag": tag,
        "data": data or {},
        "actions": actions or [
            {"action": "open", "title": "Apri"},
            {"action": "dismiss", "title": "Ignora"}
        ]
    }

    try:
        # Build subscription info
        subscription_info = {
            "endpoint": subscription['endpoint'],
            "keys": subscription.get('keys', {})
        }

        # Send push notification
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": VAPID_CLAIMS_EMAIL}
        )

        logger.info(f"Push notification sent: {title}")
        return True

    except WebPushException as e:
        logger.error(f"Push notification failed: {e}")

        # If subscription is expired/invalid, return False to trigger cleanup
        if e.response and e.response.status_code in [404, 410]:
            logger.warning(f"Subscription expired or invalid: {subscription.get('endpoint', 'unknown')[:50]}")
            return False

        return False
    except Exception as e:
        logger.error(f"Unexpected error sending push: {e}")
        return False


async def send_push_to_user(
    user_id: int,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    tag: str = "default"
) -> int:
    """
    Send a push notification to all subscriptions for a user.

    Args:
        user_id: User ID to send notification to
        title: Notification title
        body: Notification body text
        data: Optional additional data
        tag: Notification tag

    Returns:
        Number of notifications sent successfully
    """
    if not PUSH_AVAILABLE:
        return 0

    from auth import get_push_subscriptions, delete_push_subscription

    subscriptions = await get_push_subscriptions(user_id)
    sent_count = 0
    expired_endpoints = []

    for sub in subscriptions:
        success = await send_push_notification(
            subscription=sub,
            title=title,
            body=body,
            data=data,
            tag=tag
        )

        if success:
            sent_count += 1
        else:
            # Mark as potentially expired
            expired_endpoints.append(sub.get('endpoint'))

    # Clean up expired subscriptions
    for endpoint in expired_endpoints:
        if endpoint:
            await delete_push_subscription(user_id, endpoint)

    return sent_count


async def notify_new_item(user_id: int, item: Dict[str, Any]) -> bool:
    """
    Send notification about a new classified item.
    """
    if not PUSH_AVAILABLE:
        return False

    type_names = {
        'film': 'Film',
        'book': 'Libro',
        'concept': 'Concetto',
        'music': 'Musica',
        'art': 'Arte',
        'todo': 'Todo',
        'other': 'Altro'
    }

    item_type = item.get('type', 'other')
    type_name = type_names.get(item_type, 'Pensiero')
    title = item.get('title', 'Nuovo pensiero')

    count = await send_push_to_user(
        user_id=user_id,
        title=f"Nuovo {type_name} salvato",
        body=title[:100],
        data={
            "url": f"/",
            "item_id": item.get('id')
        },
        tag=f"item-{item.get('id', 'new')}"
    )

    return count > 0


async def notify_daily_picks(user_id: int, picks_count: int, total_time: int) -> bool:
    """
    Send notification about daily picks.
    """
    if not PUSH_AVAILABLE:
        return False

    count = await send_push_to_user(
        user_id=user_id,
        title="I tuoi pick di oggi",
        body=f"{picks_count} pensieri selezionati ({total_time} min totali)",
        data={"url": "/"},
        tag="daily-picks"
    )

    return count > 0


def get_vapid_public_key() -> str:
    """Get the VAPID public key for clients to subscribe."""
    return VAPID_PUBLIC_KEY or ""


def is_push_available() -> bool:
    """Check if push notifications are configured and available."""
    return PUSH_AVAILABLE
