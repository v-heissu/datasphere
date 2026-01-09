"""
Email service for weekly digest notifications.
"""

import smtplib
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import List, Dict, Any

from config import (
    EMAIL_ENABLED, EMAIL_SMTP_HOST, EMAIL_SMTP_PORT,
    EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_FROM, EMAIL_TO,
    DASHBOARD_URL
)
from database import get_db

logger = logging.getLogger(__name__)


async def get_weekly_items() -> Dict[str, Any]:
    """Fetch items from the last 7 days for the digest."""
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()

    async with get_db() as db:
        # Get all items from last week - using correct column names
        cursor = await db.execute("""
            SELECT id, verbatim_input, title, item_type, priority, status,
                   description, enrichment, estimated_minutes, created_at
            FROM items
            WHERE created_at >= ?
            ORDER BY created_at DESC
        """, (week_ago,))
        rows = await cursor.fetchall()

        items = []
        for row in rows:
            # Parse enrichment JSON
            enrichment = None
            if row[7]:
                try:
                    enrichment = json.loads(row[7]) if isinstance(row[7], str) else row[7]
                except:
                    enrichment = {}

            items.append({
                'id': row[0],
                'verbatim_input': row[1],
                'title': row[2],
                'item_type': row[3],
                'priority': row[4],
                'status': row[5],
                'description': row[6],
                'enrichment': enrichment,
                'estimated_minutes': row[8],
                'created_at': row[9]
            })

        # Get stats
        total = len(items)
        by_type = {}
        by_status = {}

        for item in items:
            item_type = item['item_type'] or 'other'
            by_type[item_type] = by_type.get(item_type, 0) + 1

            status = item['status'] or 'pending'
            by_status[status] = by_status.get(status, 0) + 1

        return {
            'items': items,
            'total': total,
            'by_type': by_type,
            'by_status': by_status
        }


def get_type_emoji(item_type: str) -> str:
    """Get emoji for item type."""
    emojis = {
        'film': '🎬',
        'book': '📚',
        'concept': '💡',
        'music': '🎵',
        'art': '🎨',
        'todo': '✓',
        'other': '📌'
    }
    return emojis.get(item_type.lower() if item_type else 'other', '📌')


def get_priority_color(priority) -> str:
    """Get color for priority."""
    if isinstance(priority, int):
        if priority >= 4:
            return '#ef4444'  # high - red
        elif priority >= 2:
            return '#f59e0b'  # medium - orange
        else:
            return '#22c55e'  # low - green
    return '#f59e0b'  # default medium


def build_html_email(data: Dict[str, Any]) -> str:
    """Build beautiful HTML email for weekly digest."""
    items = data['items']
    total = data['total']
    by_type = data['by_type']
    by_status = data['by_status']

    # Build type stats HTML
    type_stats_html = ""
    for item_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
        emoji = get_type_emoji(item_type)
        type_stats_html += f"""
            <div style="display: inline-block; margin: 4px 8px 4px 0; padding: 6px 12px; background: #374151; border-radius: 20px; font-size: 13px;">
                {emoji} {item_type.title()}: <strong>{count}</strong>
            </div>
        """

    # Build items HTML (top 15 items)
    items_html = ""
    for item in items[:15]:
        emoji = get_type_emoji(item['item_type'])
        priority_color = get_priority_color(item['priority'])
        verbatim = item['verbatim_input'] or ''
        title = item['title'] or verbatim[:50] + ('...' if len(verbatim) > 50 else '')
        status_badge = '✓' if item['status'] == 'consumed' else '○'
        status_color = '#22c55e' if item['status'] == 'consumed' else '#6b7280'

        # Get link from enrichment
        link_html = ""
        if item['enrichment'] and isinstance(item['enrichment'], dict):
            links = item['enrichment'].get('links', [])
            if links and len(links) > 0:
                link_html = f' <a href="{links[0].get("url", "")}" style="color: #60a5fa; text-decoration: none;">🔗</a>'

        created = datetime.fromisoformat(item['created_at']).strftime('%d/%m') if item['created_at'] else ''

        items_html += f"""
            <tr>
                <td style="padding: 12px 8px; border-bottom: 1px solid #374151;">
                    <span style="color: {status_color}; margin-right: 8px;">{status_badge}</span>
                    {emoji}
                </td>
                <td style="padding: 12px 8px; border-bottom: 1px solid #374151;">
                    <span style="color: #f3f4f6;">{title}</span>{link_html}
                    <br>
                    <span style="color: #9ca3af; font-size: 12px;">"{verbatim[:80]}{'...' if len(verbatim) > 80 else ''}"</span>
                </td>
                <td style="padding: 12px 8px; border-bottom: 1px solid #374151; text-align: center;">
                    <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: {priority_color};"></span>
                </td>
                <td style="padding: 12px 8px; border-bottom: 1px solid #374151; color: #9ca3af; font-size: 12px;">
                    {created}
                </td>
            </tr>
        """

    # Status summary
    consumed = by_status.get('consumed', 0)
    pending = by_status.get('pending', 0)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #111827; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">

            <!-- Header -->
            <div style="background: linear-gradient(135deg, #1f2937 0%, #374151 100%); border-radius: 16px; padding: 32px; margin-bottom: 20px; text-align: center;">
                <h1 style="margin: 0 0 8px 0; color: #f3f4f6; font-size: 28px; font-weight: 700;">
                    🧠 Weekly Brain Dump
                </h1>
                <p style="margin: 0; color: #9ca3af; font-size: 14px;">
                    Il tuo recap settimanale • {datetime.now().strftime('%d %B %Y')}
                </p>
            </div>

            <!-- Stats Cards -->
            <div style="display: flex; gap: 12px; margin-bottom: 20px;">
                <div style="flex: 1; background: #1f2937; border-radius: 12px; padding: 20px; text-align: center;">
                    <div style="font-size: 32px; font-weight: 700; color: #60a5fa;">{total}</div>
                    <div style="color: #9ca3af; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Catturati</div>
                </div>
                <div style="flex: 1; background: #1f2937; border-radius: 12px; padding: 20px; text-align: center;">
                    <div style="font-size: 32px; font-weight: 700; color: #22c55e;">{consumed}</div>
                    <div style="color: #9ca3af; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Completati</div>
                </div>
                <div style="flex: 1; background: #1f2937; border-radius: 12px; padding: 20px; text-align: center;">
                    <div style="font-size: 32px; font-weight: 700; color: #f59e0b;">{pending}</div>
                    <div style="color: #9ca3af; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">In attesa</div>
                </div>
            </div>

            <!-- Types -->
            <div style="background: #1f2937; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                <h3 style="margin: 0 0 12px 0; color: #f3f4f6; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">
                    Per Tipo
                </h3>
                <div>
                    {type_stats_html}
                </div>
            </div>

            <!-- Items Table -->
            <div style="background: #1f2937; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                <h3 style="margin: 0 0 16px 0; color: #f3f4f6; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">
                    Ultimi Pensieri
                </h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tbody>
                        {items_html}
                    </tbody>
                </table>
                {f'<p style="color: #9ca3af; font-size: 12px; margin-top: 16px; text-align: center;">...e altri {total - 15} elementi</p>' if total > 15 else ''}
            </div>

            <!-- CTA Button -->
            <div style="text-align: center; margin-bottom: 20px;">
                <a href="{DASHBOARD_URL}" style="display: inline-block; background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); color: white; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 14px;">
                    Apri Dashboard →
                </a>
            </div>

            <!-- Footer -->
            <div style="text-align: center; color: #6b7280; font-size: 12px;">
                <p style="margin: 0;">
                    ADHD Thought Capture System<br>
                    Cattura. Classifica. Consuma.
                </p>
            </div>

        </div>
    </body>
    </html>
    """

    return html


def build_text_email(data: Dict[str, Any]) -> str:
    """Build plain text fallback for email."""
    items = data['items']
    total = data['total']
    by_status = data['by_status']

    consumed = by_status.get('consumed', 0)
    pending = by_status.get('pending', 0)

    text = f"""
🧠 WEEKLY BRAIN DUMP
Il tuo recap settimanale • {datetime.now().strftime('%d %B %Y')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 STATISTICHE
• Catturati: {total}
• Completati: {consumed}
• In attesa: {pending}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 ULTIMI PENSIERI

"""

    for item in items[:15]:
        emoji = get_type_emoji(item['item_type'])
        status = '✓' if item['status'] == 'consumed' else '○'
        verbatim = item['verbatim_input'] or ''
        title = item['title'] or verbatim[:50]
        text += f"{status} {emoji} {title}\n"
        text += f"   \"{verbatim[:60]}{'...' if len(verbatim) > 60 else ''}\"\n\n"

    if total > 15:
        text += f"\n...e altri {total - 15} elementi\n"

    text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 Apri Dashboard: {DASHBOARD_URL}

--
ADHD Thought Capture System
Cattura. Classifica. Consuma.
"""

    return text


async def send_weekly_digest() -> bool:
    """Send the weekly digest email."""
    if not EMAIL_ENABLED:
        logger.info("Email not enabled, skipping weekly digest")
        return False

    if not all([EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_FROM, EMAIL_TO]):
        logger.error("Email configuration incomplete")
        return False

    try:
        # Get weekly data
        data = await get_weekly_items()

        if data['total'] == 0:
            logger.info("No items this week, skipping digest")
            return False

        # Build email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🧠 Weekly Brain Dump • {data['total']} pensieri catturati"
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO

        # Attach both plain text and HTML versions
        text_content = build_text_email(data)
        html_content = build_html_email(data)

        msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        # Send email
        with smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.send_message(msg)

        logger.info(f"Weekly digest sent successfully to {EMAIL_TO}")
        return True

    except Exception as e:
        logger.error(f"Failed to send weekly digest: {e}")
        return False
