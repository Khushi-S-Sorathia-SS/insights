"""
Custom exceptions for the Insights application.

Hierarchy:
InsightsException
├── FileUploadError
│   ├── FileTooLargeError
│   ├── InvalidFileFormatError
│   └── CorruptedDataError
├── SessionError
│   ├── SessionNotFoundError
│   └── SessionExpiredError
├── SandboxError
│   ├── SandboxTimeoutError
│   ├── SandboxSecurityError
│   └── SandboxRuntimeError
├── LLMError
│   ├── LLMRateLimitError
│   ├── LLMAPIError
│   └── InvalidAPIKeyError
└── ValidationError
"""


class InsightsException(Exception):
    """Base exception for all application-level errors."""

    def __init__(self, message: str, code: str = "UNKNOWN_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


# ── File Upload ───────────────────────────────────────────────────────────────

class FileUploadError(InsightsException):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="FILE_UPLOAD_ERROR")


class FileTooLargeError(FileUploadError):
    def __init__(self, size: int, max_size: int) -> None:
        super().__init__(
            f"File size ({size} bytes) exceeds maximum ({max_size} bytes)"
        )
        self.code = "FILE_TOO_LARGE"


class InvalidFileFormatError(FileUploadError):
    def __init__(self, filename: str, allowed_types: set) -> None:
        super().__init__(
            f"File '{filename}' is not in allowed formats: {allowed_types}"
        )
        self.code = "INVALID_FILE_FORMAT"


class CorruptedDataError(FileUploadError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"CSV data is corrupted: {reason}")
        self.code = "CORRUPTED_DATA"


# ── Session ───────────────────────────────────────────────────────────────────

class SessionError(InsightsException):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="SESSION_ERROR")


class SessionNotFoundError(SessionError):
    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session '{session_id}' not found")
        self.code = "SESSION_NOT_FOUND"


class SessionExpiredError(SessionError):
    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session '{session_id}' has expired")
        self.code = "SESSION_EXPIRED"


# ── Sandbox ───────────────────────────────────────────────────────────────────

class SandboxError(InsightsException):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="SANDBOX_ERROR")


class SandboxTimeoutError(SandboxError):
    def __init__(self, timeout: int) -> None:
        super().__init__(f"Code execution exceeded timeout ({timeout} seconds)")
        self.code = "SANDBOX_TIMEOUT"


class SandboxSecurityError(SandboxError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Code contains forbidden operations: {reason}")
        self.code = "SANDBOX_SECURITY_ERROR"


class SandboxRuntimeError(SandboxError):
    def __init__(self, error_message: str) -> None:
        super().__init__(f"Code execution failed: {error_message}")
        self.code = "SANDBOX_RUNTIME_ERROR"


# ── LLM ──────────────────────────────────────────────────────────────────────

class LLMError(InsightsException):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="LLM_ERROR")


class LLMRateLimitError(LLMError):
    def __init__(self) -> None:
        super().__init__("LLM API rate limit exceeded. Please wait and try again.")
        self.code = "LLM_RATE_LIMIT"


class LLMAPIError(LLMError):
    def __init__(self, status_code: int, response: str) -> None:
        super().__init__(f"LLM API error ({status_code}): {response}")
        self.code = "LLM_API_ERROR"


class InvalidAPIKeyError(LLMError):
    def __init__(self) -> None:
        super().__init__("LLM API key is invalid or not set")
        self.code = "INVALID_API_KEY"


# ── Validation ────────────────────────────────────────────────────────────────

class ValidationError(InsightsException):
    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message, code="VALIDATION_ERROR")
        self.field = field
