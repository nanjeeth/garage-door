"""
Background jobs:
1. Poll ESP32 for door status every 5 seconds
2. Check if phone arrived on network (auto-open)
3. Alert if door left open too long
"""
import asyncio
import logging
import time
from datetime import datetime
from app.config import DOOR_OPEN_ALERT_SECONDS
from app.esp32_client import get_door_status, trigger_door
from app.phone_detector import detect_phone
from app.notifier import send_notification
from app.database import SessionLocal
from app import models

logger = logging.getLogger(__name__)


class GarageScheduler:
    def __init__(self):
        self.running = False
        self.door_is_open = False
        self.door_open_since: float | None = None
        self.phone_was_home = False
        self.auto_open_enabled = True
        self.alert_sent = False

    async def start(self):
        self.running = True
        await asyncio.to_thread(self._init_state)
        logger.info("Scheduler started")

        await asyncio.gather(
            self._poll_door_status(),
            self._poll_phone(),
            self._check_open_too_long(),
        )

    def stop(self):
        self.running = False

    def _init_state(self):
        db = SessionLocal()
        try:
            state = db.query(models.DoorState).first()
            if not state:
                state = models.DoorState(id=1, is_open=False)
                db.add(state)
                db.commit()
            self.door_is_open = state.is_open
        finally:
            db.close()

    def _update_door_state(self, is_open: bool, source: str):
        if is_open == self.door_is_open:
            return

        self.door_is_open = is_open
        action = "open" if is_open else "close"

        if is_open:
            self.door_open_since = time.time()
            self.alert_sent = False
        else:
            self.door_open_since = None

        db = SessionLocal()
        try:
            state = db.query(models.DoorState).first()
            if state:
                state.is_open = is_open
                state.last_changed = datetime.utcnow()

            event = models.DoorEvent(
                action=action,
                source=source,
                timestamp=datetime.utcnow(),
            )
            db.add(event)
            db.commit()
        finally:
            db.close()

        logger.info("Door state changed: %s (source: %s)", action, source)

    async def _poll_door_status(self):
        while self.running:
            status = await get_door_status()
            if status:
                is_open = status == "open"
                await asyncio.to_thread(self._update_door_state, is_open, "esp32")
            await asyncio.sleep(5)

    async def _poll_phone(self):
        while self.running:
            if not self.auto_open_enabled:
                await asyncio.sleep(30)
                continue

            phone_home = await asyncio.to_thread(detect_phone)

            if phone_home and not self.phone_was_home:
                logger.info("Phone detected on network — arrival!")
                if not self.door_is_open:
                    success = await trigger_door()
                    if success:
                        await send_notification("Auto-opened — welcome home!")
                        await asyncio.to_thread(self._update_door_state, True, "auto")

            self.phone_was_home = phone_home
            await asyncio.sleep(15)

    async def _check_open_too_long(self):
        while self.running:
            if (
                self.door_is_open
                and self.door_open_since
                and not self.alert_sent
            ):
                elapsed = time.time() - self.door_open_since
                if elapsed > DOOR_OPEN_ALERT_SECONDS:
                    minutes = int(elapsed // 60)
                    await send_notification(
                        f"⚠️ Door has been open for {minutes} minutes!"
                    )
                    self.alert_sent = True

            await asyncio.sleep(30)


scheduler = GarageScheduler()
