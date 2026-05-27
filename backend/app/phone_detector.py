"""
Detects if the user's phone is on the local network.
Used for auto-open on arrival.
"""
import subprocess
import logging
import platform
from app.config import PHONE_IP, PHONE_MAC

logger = logging.getLogger(__name__)


def is_phone_home() -> bool:
    """Ping the phone IP to check if it's on the network."""
    if not PHONE_IP:
        return False

    try:
        flag = "-n" if platform.system() == "Windows" else "-c"
        result = subprocess.run(
            ["ping", flag, "1", "-W", "1", PHONE_IP],
            capture_output=True,
            timeout=3,
        )
        return result.returncode == 0
    except Exception as e:
        logger.debug("Phone ping failed: %s", e)
        return False


def check_arp_for_phone() -> bool:
    """Check ARP table for phone MAC address (more reliable than ping)."""
    if not PHONE_MAC:
        return False

    try:
        result = subprocess.run(
            ["arp", "-a"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return PHONE_MAC.lower() in result.stdout.lower()
    except Exception as e:
        logger.debug("ARP check failed: %s", e)
        return False


def detect_phone() -> bool:
    """Returns True if phone is detected on the network."""
    return is_phone_home() or check_arp_for_phone()
