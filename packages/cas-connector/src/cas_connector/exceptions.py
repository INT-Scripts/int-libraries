class CASError(Exception):
    """Base exception for CAS Connector."""
    pass

class CASLoginError(CASError):
    """Raised when login fails."""
    pass

class CASConnectionError(CASError):
    """Raised when connection to CAS server fails."""
    pass
