# CAS Connector 🛡️

A modern, asynchronous Python client for IMT-BS/TSP Central Authentication Service (CAS).

## Features
- **Async First**: Built on `httpx` for high-performance concurrency.
- **Session Sharing**: Exportable `httpx.Cookies` for integration with other libraries.
- **Robust Auth**: Handles attribute release, SAML relay, and intermediate redirects automatically.

## Installation
```bash
uv add /path/to/cas_connector
```

## Library Usage
```python
from cas_connector import CASClient

async def main():
    client = CASClient(service_url="...")
    await client.login(username="...", password="...")
    
    # Use the cookies in another library
    cookies = client.cookies
    
    # Or perform requests directly
    async with client.get_client() as async_client:
        r = await async_client.get("...")
```
