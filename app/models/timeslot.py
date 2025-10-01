# app/models/timeslot.py

from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base

class TimeSlot(Base):
    __tablename__ = "timeslots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<TimeSlot(id={self.id}, start_time={self.start_time}, end_time={self.end_time})>"

    def is_conflicting(self, other_start: datetime, other_end: datetime) -> bool:
        """
        Check if the current timeslot conflicts with another timeslot.
        """
        return not (self.end_time <= other_start or self.start_time >= other_end)

    @staticmethod
    def create_timeslot(start_time: datetime, duration_minutes: int, description: str = None):
        """
        Helper to create a new timeslot given start time and duration.
        """
        end_time = start_time + timedelta(minutes=duration_minutes)
        return TimeSlot(start_time=start_time, end_time=end_time, description=description)
