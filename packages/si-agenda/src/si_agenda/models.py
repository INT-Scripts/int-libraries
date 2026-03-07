from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class Calendar(BaseModel):
    id: str
    name: str
    category: str

class Event(BaseModel):
    id: Optional[str] = None
    calendar_id: Optional[str] = None
    name: str
    type: str # CM, TD, TP, etc.
    date: str # YYYY-MM-DD
    start_time: str # HH:MM
    end_time: str # HH:MM
    raw_time: str # HH:MM-HH:MM
    
    # Details
    details_loaded: bool = False
    status: Optional[str] = None
    author: Optional[str] = None
    trainers: Optional[List[str]] = None
    students: Optional[List[str]] = None
    projects: Optional[str] = None
    organisms: Optional[str] = None
    room: Optional[str] = None
    full_details: Optional[dict] = None # Stores raw key-value pairs from details page
