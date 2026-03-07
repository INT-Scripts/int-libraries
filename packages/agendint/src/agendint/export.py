import json
from ics import Calendar, Event as IcsEvent
from typing import List
from .models import Event
import datetime

def export_json(events: List[Event], filename: str):
    data = [evt.model_dump() for evt in events]
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"[INFO] Exporté vers {filename}")

def export_ical(events: List[Event], filename: str):
    c = Calendar()
    for evt in events:
        e = IcsEvent()
        e.name = evt.name
        
        # Parse start/end to datetime
        # evt.date is YYYY-MM-DD
        # evt.start_time is HH:MM
        try:
            start_dt = datetime.datetime.strptime(f"{evt.date} {evt.start_time}", "%Y-%m-%d %H:%M")
            end_dt = datetime.datetime.strptime(f"{evt.date} {evt.end_time}", "%Y-%m-%d %H:%M")
            
            e.begin = start_dt
            e.end = end_dt
            
            desc = []
            if evt.type: desc.append(f"Type: {evt.type}")
            if evt.status: desc.append(f"Statut: {evt.status}")
            if evt.author: desc.append(f"Auteur: {evt.author}")
            if evt.trainers: desc.append(f"Formateurs: {', '.join(evt.trainers)}")
            if evt.room: 
                e.location = evt.room
            
            e.description = "\n".join(desc)
            
            c.events.add(e)
        except Exception as err:
            print(f"[WARN] Failed to convert event {evt.name} to iCal: {err}")

    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(c.serialize_iter())
    print(f"[INFO] Exporté vers {filename}")
