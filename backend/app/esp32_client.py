"""
Communicates with the ESP32 over HTTP.
The ESP32 exposes:
  GET  /status   → {"door": "open"|"closed"}
  POST /trigger  → triggers the relay (simulates button press)
"""
import httpx
import logging
from app.config import ESP32_IP, ESP32_TOKEN

logger = logging.getLogger(__name__)

BASE_URL = f"http://{ESP32_IP}"
HEADERS = {"Authorization": f"Bearer {ESP32_TOKEN}"}
TIMEOUT = 5.0


async def get_door_status() -> str | None:
    """Returns 'open', 'closed', or None on error."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{BASE_URL}/status",
                headers=HEADERS,
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("door")
    except Exception as e:
        logger.error("Failed to get ESP32 status: %s", e)
        return None


async def trigger_door() -> bool:
    """Triggers the relay. Returns True on success."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BASE_URL}/trigger",
                headers=HEADERS,
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            return True
    except Exception as e:
        logger.error("Failed to trigger ESP32: %s", e)
        return False
