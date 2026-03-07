# TrombINT 🕵️

Scraper for the IMT-BS/TSP Student Directory (TrombINT).

## Features
- **Async Scraping**: Uses `httpx` for fast data retrieval.
- **CAS Integration**: Supports pre-authenticated `httpx.Cookies` from `cas-connector`.
- **Advanced Search**: Filter by name, school, or graduation year.
- **Image Support**: Built-in methods for high-resolution profile picture downloads.

## Usage
### CLI
```bash
uv run trombint --name "John Doe"
```

### Library
```python
from trombint.client import TrombINT

async def main():
    # Provide cookies from CASClient
    t_client = TrombINT(cookies=cas_cookies)
    students = await t_client.get_all_students()
```
