# SI Agenda Scraper 📅

Modern asynchronous scraper for SI Ecoles (IMT-BS / Télécom SudParis).

## Features
- **Full Sync**: Integrated with `cas-connector` for zero-reauthentication scraping.
- **Hydration**: Rapidly fetch basic event data, then hydrate details concurrently.
- **Export**: Built-in support for iCal (.ics) and JSON formats.
- **Progress**: Callbacks for integration with CLI progress bars (like `rich`).

## Usage
### CLI
```bash
uv run si-agenda list
uv run si-agenda fetch --calendar-id PRJ67059
```

### Library
```python
from si_agenda.client import SIClient
from si_agenda.api import get_events

async def main():
    si_client = SIClient(cookies=cas_cookies)
    events = await get_events(si_client, "PRJ67059", start_date, end_date)
```
