from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.database import Base


class DoorEvent(Base):
    __tablename__ = "door_events"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False)  # "open", "close", "trigger"
    source = Column(String, nullable=False)  # "manual", "auto", "api", "esp32"
    timestamp = Column(DateTime, default=datetime.utcnow)


class DoorState(Base):
    __tablename__ = "door_state"

    id = Column(Integer, primary_key=True, default=1)
    is_open = Column(Boolean, default=False)
    last_changed = Column(DateTime, default=datetime.utcnow)
    last_triggered = Column(DateTime, nullable=True)
