import os

ESP32_IP = os.getenv("ESP32_IP", "192.168.1.100")
ESP32_TOKEN = os.getenv("ESP32_TOKEN", "change-me-to-a-secret")

PHONE_MAC = os.getenv("PHONE_MAC", "")
PHONE_IP = os.getenv("PHONE_IP", "")

NOTIFY_ENABLED = os.getenv("NOTIFY_ENABLED", "false").lower() == "true"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

DOOR_OPEN_ALERT_SECONDS = int(os.getenv("DOOR_OPEN_ALERT_SECONDS", "300"))

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./garage.db")
