"""Custom exceptions for iTerm2 AI Command Generator."""


class AIGeneratorError(Exception):
    """Base exception class for AI Command Generator."""
    pass


class APIError(AIGeneratorError):
    """Raised when Gemini API call fails."""
    pass


class RateLimitError(APIError):
    """Raised when API rate limit is exceeded."""
    pass


class KeychainError(AIGeneratorError):
    """Raised when Keychain access fails."""
    pass


class ConfigError(AIGeneratorError):
    """Raised when configuration file is invalid or missing."""
    pass


class ValidationError(AIGeneratorError):
    """Raised when input validation fails."""
    pass
