"""
Custom exceptions for the Insights Chatbot application.
"""


class InsightsException(Exception):
    """Base exception for all application exceptions."""

    def __init__(self, message: str, code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


# File Upload Exceptions
class FileUploadError(InsightsException):
    """Base class for file upload errors."""

    def __init__(self, message: str):
        super().__init__(message, code="FILE_UPLOAD_ERROR")


class FileTooLargeError(FileUploadError):
    """File exceeds maximum size limit."""

    def __init__(self, size: int, max_size: int):
        message = f"File size ({size} bytes) exceeds maximum ({max_size} bytes)"
        super().__init__(message)
        self.code = "FILE_TOO_LARGE"


class InvalidFileFormatError(FileUploadError):
    """File format is not supported."""

    def __init__(self, filename: str, allowed_types: set):
        message = f"File {filename} is not in allowed formats: {allowed_types}"
        super().__init__(message)
        self.code = "INVALID_FILE_FORMAT"


class CorruptedDataError(FileUploadError):
    """CSV data is corrupted or unreadable."""

    def __init__(self, reason: str):
        message = f"CSV data is corrupted: {reason}"
        super().__init__(message)
        self.code = "CORRUPTED_DATA"


# Session Exceptions
class SessionError(InsightsException):
    """Base class for session management errors."""

    def __init__(self, message: str):
        super().__init__(message, code="SESSION_ERROR")


class SessionNotFoundError(SessionError):
    """Session ID does not exist."""

    def __init__(self, session_id: str):
        message = f"Session '{session_id}' not found"
        super().__init__(message)
        self.code = "SESSION_NOT_FOUND"


class SessionExpiredError(SessionError):
    """Session has expired."""

    def __init__(self, session_id: str):
        message = f"Session '{session_id}' has expired"
        super().__init__(message)
        self.code = "SESSION_EXPIRED"


# Sandbox Exceptions
class SandboxError(InsightsException):
    """Base class for sandbox execution errors."""

    def __init__(self, message: str):
        super().__init__(message, code="SANDBOX_ERROR")


class SandboxTimeoutError(SandboxError):
    """Code execution timed out."""

    def __init__(self, timeout: int):
        message = f"Code execution exceeded timeout ({timeout} seconds)"
        super().__init__(message)
        self.code = "SANDBOX_TIMEOUT"


class SandboxSecurityError(SandboxError):
    """Code contains forbidden operations."""

    def __init__(self, reason: str):
        message = f"Code contains forbidden operations: {reason}"
        super().__init__(message)
        self.code = "SANDBOX_SECURITY_ERROR"


class SandboxRuntimeError(SandboxError):
    """Code execution failed."""

    def __init__(self, error_message: str):
        message = f"Code execution failed: {error_message}"
        super().__init__(message)
        self.code = "SANDBOX_RUNTIME_ERROR"


# LLM Exceptions
class LLMError(InsightsException):
    """Base class for LLM-related errors."""

    def __init__(self, message: str):
        super().__init__(message, code="LLM_ERROR")


class LLMRateLimitError(LLMError):
    """LLM API rate limit exceeded."""

    def __init__(self):
        message = "LLM API rate limit exceeded. Please wait and try again."
        super().__init__(message)
        self.code = "LLM_RATE_LIMIT"


class LLMAPIError(LLMError):
    """LLM API call failed."""

    def __init__(self, status_code: int, response: str):
        message = f"LLM API error ({status_code}): {response}"
        super().__init__(message)
        self.code = "LLM_API_ERROR"


class InvalidAPIKeyError(LLMError):
    """LLM API key is invalid."""

    def __init__(self):
        message = "LLM API key is invalid or not set"
        super().__init__(message)
        self.code = "INVALID_API_KEY"


# Validation Exceptions
class ValidationError(InsightsException):
    """Data validation failed."""

    def __init__(self, message: str, field: str = None):
        super().__init__(message, code="VALIDATION_ERROR")
        self.field = field
