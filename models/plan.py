from pydantic import BaseModel
from typing import List
from models.meeting import Meeting

class PlanRequest(BaseModel):
    meetings: List[Meeting]
    transport_mode: str = "any"
