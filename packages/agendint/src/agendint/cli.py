import asyncio
import typer
from typing import Optional
from datetime import date, timedelta
from dotenv import load_dotenv
import os
from .client import SIClient
from .api import get_calendars, get_events, get_event_details
from .export import export_json, export_ical

app = typer.Typer(help="SI Agenda CLI - Fetch and manage your student agenda.")

async def _get_client():
    load_dotenv()
    client = SIClient()
    username = os.getenv("LOGIN")
    password = os.getenv("PASSWORD")
    
    if not username or not password:
        print("[AUTH] Credentials not found in .env, please provide them.")
        
    if not await client.login(username, password):
        raise typer.Exit(code=1)
    return client

@app.command("list")
def list_calendars():
    """List available calendars."""
    async def _run():
        client = await _get_client()
        try:
            calendars = await get_calendars(client)
            if not calendars:
                print("No calendars found.")
                return

            # Sort by category then name
            calendars.sort(key=lambda x: (x.category, x.name))
            
            print(f"{'CATEGORY':<15} | {'ID':<10} | {'NAME'}")
            print("-" * 60)
            for cal in calendars:
                print(f"{cal.category:<15} | {cal.id:<10} | {cal.name}")
                
        except Exception as e:
            print(f"Error listing calendars: {e}")
            raise typer.Exit(code=1)
    asyncio.run(_run())

@app.command("details")
def get_details(
    event_id: str = typer.Option(..., "--num-eve", help="Event ID (NumEve)"),
    date_src: str = typer.Option(..., "--dat-src", help="Source Date (YYYYMMDD)"),
    calendar_id: str = typer.Option(..., "--nom-cal", help="Calendar ID (NomCal)"),
):
    """Fetch details for a specific event."""
    async def _run():
        client = await _get_client()
        
        if len(date_src) == 8 and "-" not in date_src:
            formatted_date = f"{date_src[:4]}-{date_src[4:6]}-{date_src[6:]}"
        else:
            formatted_date = date_src

        from .models import Event
        dummy_evt = Event(
            id=event_id, 
            date=formatted_date, 
            name="Fetching...", 
            type="Unknown", 
            start_time="00:00", 
            end_time="00:00", 
            raw_time=""
        )
        
        try:
            updated_evt = await get_event_details(client, dummy_evt, calendar_id)
            if updated_evt.full_details:
                 import json
                 print(json.dumps(updated_evt.full_details, indent=4, ensure_ascii=False))
            else:
                 print("[WARN] No details found or parsed.")
                 print(updated_evt.model_dump_json(indent=4))

        except Exception as e:
            print(f"Error fetching details: {e}")
            raise typer.Exit(code=1)
    asyncio.run(_run())

@app.command("fetch")
def fetch_events(
    calendar_id: str = typer.Option(..., help="ID of the calendar to fetch."),
    start: Optional[str] = typer.Option(None, help="Start date (YYYY-MM-DD)."),
    end: Optional[str] = typer.Option(None, help="End date (YYYY-MM-DD)."),
    unit: str = typer.Option("week", help="Time unit if dates not provided: day, week, month."),
    output_format: str = typer.Option("json", "--format", help="Output format: json, ical."),
    output: str = typer.Option("agenda.json", help="Output filename."),
    details: bool = typer.Option(False, help="Fetch detailed info for each event (slower)."),
    concurrency: int = typer.Option(10, help="Number of concurrent requests for details.")
):
    """Fetch events for a specific calendar."""
    async def _run():
        client = await _get_client()
        
        # Determine dates
        today = date.today()
        start_date = today
        end_date = today
        
        if start and end:
            try:
                s_parts = start.split("-")
                start_date = date(int(s_parts[0]), int(s_parts[1]), int(s_parts[2]))
                
                e_parts = end.split("-")
                end_date = date(int(e_parts[0]), int(e_parts[1]), int(e_parts[2]))
            except Exception:
                from datetime import date as date_cls
                start_date = date_cls.fromisoformat(start)
                end_date = date_cls.fromisoformat(end)
        else:
            if unit == "day":
                pass
            elif unit == "week":
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=6)
            elif unit == "month":
                start_date = today.replace(day=1)
                if today.month == 12:
                    end_date = today.replace(year=today.year+1, month=1, day=1) - timedelta(days=1)
                else:
                    end_date = today.replace(month=today.month+1, day=1) - timedelta(days=1)
                    
        print(f"[INFO] Fetching events from {start_date} to {end_date} for calendar {calendar_id}...")
        
        try:
            try:
                from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TimeRemainingColumn(),
                ) as progress:
                    task_id = progress.add_task("Fetching events...", total=None)
                    
                    def on_progress(current, total, month_date, current_events):
                        progress.update(task_id, total=total, completed=current, description=f"Fetching {month_date.strftime('%B %Y')}...")
                        if output_format.lower() == "json" and current_events:
                            export_json(current_events, output)

                    events = await get_events(client, calendar_id, start_date, end_date, progress_callback=on_progress)
            except ImportError:
                 print("Fetching events...")
                 events = await get_events(client, calendar_id, start_date, end_date)

            print(f"[INFO] Found {len(events)} events.")
            
            if details and events:
                print(f"[INFO] Fetching details for all events (concurrency={concurrency})...")
                try:
                    # In-place hydration with progress
                    from concurrent.futures import ThreadPoolExecutor, as_completed
                    
                    # SI Session init
                    await client.init_agenda_session()
                    
                    # We use a wrapper for the async call in a thread pool?
                    # Actually, better to just use asyncio.gather with semaphore for details.
                    sem = asyncio.Semaphore(concurrency)
                    async def fetch_detail_task(evt):
                        async with sem:
                            return await get_event_details(client, evt, calendar_id)

                    try:
                        from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
                        with Progress(
                            SpinnerColumn(),
                            TextColumn("[progress.description]{task.description}"),
                            BarColumn(),
                            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                            TimeRemainingColumn(),
                        ) as progress:
                            task_id = progress.add_task("Fetching details...", total=len(events))
                            
                            processed = 0
                            for fut in asyncio.as_completed([fetch_detail_task(e) for e in events]):
                                await fut
                                progress.advance(task_id)
                                processed += 1
                                if processed % 10 == 0:
                                     if output_format.lower() == "json":
                                         export_json(events, output)
                    except ImportError:
                        await asyncio.gather(*(fetch_detail_task(e) for e in events))

                except Exception as e:
                    print(f"[WARN] Error during hydration: {e}")

            if output_format.lower() == "json":
                export_json(events, output)
            elif output_format.lower() == "ical":
                 export_ical(events, output)
                
        except Exception as e:
            print(f"Error fetching events: {e}")
            raise typer.Exit(code=1)
    asyncio.run(_run())

@app.command("hydrate")
def hydrate_events(
    input_file: str = typer.Argument(..., help="Path to input JSON file with events."),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Path to save output (defaults to input file)."),
    calendar_id: Optional[str] = typer.Option(None, "--calendar-id", "-c", help="Fallback Calendar ID if missing in event."),
    concurrency: int = typer.Option(10, help="Number of concurrent requests."),
):
    """Hydrate an existing JSON agenda with full details."""
    async def _run():
        client = await _get_client()
        import json
        from .models import Event
        
        if not os.path.exists(input_file):
            print(f"[ERR] Input file {input_file} not found.")
            raise typer.Exit(code=1)
            
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            events = [Event(**e) for e in data]
            to_process = [e for e in events if not e.details_loaded]
            if not to_process:
                print("[INFO] All events already have details.")
                return

            target_output = output_file if output_file else input_file
            await client.init_agenda_session()
            
            sem = asyncio.Semaphore(concurrency)
            async def hydrate_task(evt):
                async with sem:
                    cid = evt.calendar_id or calendar_id
                    if cid:
                        return await get_event_details(client, evt, cid)

            try:
                from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TimeRemainingColumn(),
                ) as progress:
                    task_id = progress.add_task("Hydrating details...", total=len(to_process))
                    
                    processed = 0
                    for fut in asyncio.as_completed([hydrate_task(e) for e in to_process]):
                        await fut
                        progress.advance(task_id)
                        processed += 1
                        if processed % 10 == 0:
                             export_json(events, target_output)
            except ImportError:
                await asyncio.gather(*(hydrate_task(e) for e in to_process))
                         
            export_json(events, target_output)
            print(f"[SUCCESS] Hydrated events saved to {target_output}")

        except Exception as e:
            print(f"Error hydrating events: {e}")
            raise typer.Exit(code=1)
    asyncio.run(_run())

if __name__ == "__main__":
    app()
