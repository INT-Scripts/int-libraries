#!/usr/bin/env python3
import os
import sys
from datetime import date, timedelta
from dotenv import load_dotenv

# Ensure the src directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from si_agenda.client import SIClient
from si_agenda.api import get_calendars, get_events, get_event_details_batch

def main():
    # 1. Load configuration
    load_dotenv()
    username = os.getenv("LOGIN")
    password = os.getenv("PASSWORD")

    if not username or not password:
        print("Please set LOGIN and PASSWORD in .env file")
        return

    # 2. Initialize Client
    client = SIClient()
    if not client.login(username, password):
        print("Login failed.")
        return

    print(f"\n[1] Authenticated successfully.")

    # 3. List Calendars
    print(f"\n[2] Fetching calendars...")
    calendars = get_calendars(client)
    for cal in calendars[:5]: # Show first 5
        print(f" - {cal.category}: {cal.name} ({cal.id})")
    
    if not calendars:
        print("No calendars found.")
        return

    # Select the first project calendar, or just the first one
    selected_cal = next((c for c in calendars if c.category == 'Projets'), calendars[0])
    print(f"\nSelected calendar: {selected_cal.name} ({selected_cal.id})")

    # 4. Fetch Events (Next 7 days)
    start_date = date.today()
    end_date = start_date + timedelta(days=7)
    
    print(f"\n[3] Fetching events from {start_date} to {end_date}...")
    events = get_events(client, selected_cal.id, start_date, end_date)
    print(f"Found {len(events)} events.")

    if not events:
        print("No events to detail.")
        return

    # 5. Hydrate Details (Batch)
    print(f"\n[4] Hydrating details for {len(events)} events...")
    # This modifies the event objects in-place
    get_event_details_batch(client, events, selected_cal.id, concurrency=5)

    # 6. Display Results
    print(f"\n[5] Agenda Details:")
    for evt in events:
        status = f"[{evt.status}]" if evt.status else ""
        room = f" @ {evt.room}" if evt.room else ""
        print(f" - {evt.date} {evt.raw_time}: {evt.name} {status}{room}")
        if evt.full_details and "Intervenants" in evt.full_details:
             print(f"   Intervenants: {evt.full_details['Intervenants']}")

if __name__ == "__main__":
    main()
