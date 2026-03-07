import sys
import os

# Add src to sys.path to allow running directly from source if not installed
sys.path.insert(0, os.path.abspath("src"))

try:
    from agendint.cli import app
except ImportError:
    print("Error: Could not import agendint. Make sure dependencies are installed.")
    print("Run: uv pip install -e .")
    sys.exit(1)

if __name__ == "__main__":
    app()
