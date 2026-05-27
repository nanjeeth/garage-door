"""
Sends notifications via Telegram.
"""
import httpx
import logging
from app.config import NOTIFY_ENABLED, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)


async def send_notification(message: str):
    if not NOTIFY_ENABLED:
        logger.debug("Notifications disabled, skipping: %s", message)
        return

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": f"🏠 Garage Door: {message}",
                "parse_mode": "HTML",
            })
        logger.info("Notification sent: %s", message)
    except Exception as e:
        logger.error("Failed to send notification: %s", e)
