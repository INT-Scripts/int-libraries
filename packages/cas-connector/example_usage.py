import os
import logging
from cas_connector import CASClient, CASLoginError, CASConnectionError
import getpass

# Configure logging to see output
logging.basicConfig(level=logging.INFO)

def main():
    # Example 1: Basic Usage with Environment Variables
    # Ensure LOGIN and PASSWORD env vars are set, or hardcode them here (not recommended for production)
    username = os.getenv("LOGIN") or input("Enter your username: ")
    password = os.getenv("PASSWORD") or getpass.getpass("Enter your password: ")
    
    if not username or not password:
        print("Please set LOGIN and PASSWORD environment variables.")
        return

    service_url = "https://agenda.imtbs-tsp.eu/Home/Index"  # Example Service
    
    client = CASClient(service_url=service_url)
    
    try:
        print(f"Attempting login to {service_url}...")
        if client.login(username=username, password=password):
            print("Login successful!")
            # Now you can use client.session to make authenticated requests
            # response = client.session.get("https://agenda.imtbs-tsp.eu/api/some/endpoint")
            # print(response.json())
        else:
             # Should not happen with new exception handling, but for safety
             print("Login failed (boolean return).")
             
    except CASLoginError as e:
        print(f"Authentication failed: {e}")
    except CASConnectionError as e:
        print(f"Network or protocol error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
