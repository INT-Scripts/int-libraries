from .client import CASClient
from .exceptions import CASLoginError, CASConnectionError, CASError

# Alias for backward compatibility if needed, but confusing in a new module. 
# Let's just export CASClient.
# If user wants SIClient, they can do `from cas_connector import CASClient as SIClient` or I can add it.
SIClient = CASClient

__all__ = ["CASClient", "SIClient", "CASLoginError", "CASConnectionError", "CASError"]
