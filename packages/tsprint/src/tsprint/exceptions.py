class TSPrintError(Exception):
    """Base exception for TSPrint errors."""
    pass

class LoginError(TSPrintError):
    """Raised when authentication fails."""
    pass

class UploadError(TSPrintError):
    """Raised when file upload fails."""
    pass

class PrinterNotFoundError(TSPrintError):
    """Raised when a specified printer cannot be found."""
    pass

class JobReleaseError(TSPrintError):
    """Raised when job release fails."""
    pass
