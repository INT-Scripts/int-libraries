# TSPrint 🖨️

Python client and CLI for the PaperCut printing service (FollowMe).

## Features
- **Web Print**: Upload PDFs with printer selection (Color/B&W).
- **Physical Printers**: List actual machines available for releasing jobs.
- **Job Release**: Check pending jobs and release them to available printers.
- **Automation**: One-command `upload & release` flow.

## Usage
### CLI
```bash
uv run tsprint list-webprint
uv run tsprint auto my_document.pdf
```

### Library
```python
from tsprint.client import TSPrintClient

client = TSPrintClient("user", "pass")
client.login()
client.upload_file("doc.pdf")
```
