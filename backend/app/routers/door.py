from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.esp32_client import trigger_door, get_door_status
from app.scheduler import scheduler
from app.notifier import send_notification

router = APIRouter()


def _iso_utc(dt):
    """Serialize a naive-UTC datetime as a UTC-aware ISO string (with offset),
    so clients render it in their own local timezone instead of mistaking it
    for local time."""
    return dt.replace(tzinfo=timezone.utc).isoformat() if dt else None


@router.get("/status")
async def door_status(db: Session = Depends(get_db)):
    state = db.query(models.DoorState).first()
    esp_status = await get_door_status()

    return {
        "is_open": state.is_open if state else False,
        "last_changed": _iso_utc(state.last_changed) if state else None,
        "last_triggered": _iso_utc(state.last_triggered) if state else None,
        "esp32_reachable": esp_status is not None,
        "esp32_status": esp_status,
        "auto_open_enabled": scheduler.auto_open_enabled,
    }


@router.post("/trigger")
async def trigger(db: Session = Depends(get_db)):
    success = await trigger_door()
    if not success:
        raise HTTPException(status_code=503, detail="Could not reach ESP32")

    state = db.query(models.DoorState).first()
    if state:
        state.last_triggered = datetime.utcnow()

    event = models.DoorEvent(
        action="trigger",
        source="api",
        timestamp=datetime.utcnow(),
    )
    db.add(event)
    db.commit()

    await send_notification("Door triggered from app")
    return {"success": True}


@router.get("/events")
def events(limit: int = 50, db: Session = Depends(get_db)):
    rows = (
        db.query(models.DoorEvent)
        .order_by(models.DoorEvent.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "action": r.action,
            "source": r.source,
            "timestamp": _iso_utc(r.timestamp),
        }
        for r in rows
    ]


@router.post("/auto-open/{enabled}")
def toggle_auto_open(enabled: bool):
    scheduler.auto_open_enabled = enabled
    return {"auto_open_enabled": enabled}


@router.post("/webhook")
async def esp32_webhook(payload: dict, db: Session = Depends(get_db)):
    """ESP32 calls this when door state changes (distance sensor triggered)."""
    door_status = payload.get("door")
    if door_status not in ("open", "closed"):
        raise HTTPException(status_code=400, detail="Invalid status")

    is_open = door_status == "open"
    scheduler._update_door_state(is_open, "esp32")

    action = "open" if is_open else "close"
    await send_notification(f"Door {action}ed (sensor detected)")

    return {"received": True}
