# models/meeting.py
from pydantic import BaseModel

class Meeting(BaseModel):
    location: str
    start_time: str
    duration_minutes: int = 30  # Default 30 minutes
