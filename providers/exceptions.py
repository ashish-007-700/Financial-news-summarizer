"""Custom exceptions used by the provider fallback chain."""


class RateLimitError(Exception):
    """Raised when a provider is reachable but refuses the request due to quota."""


class ProviderConfigurationError(Exception):
    """Raised when an API key or required provider setting is missing."""


class AllProvidersExhausted(Exception):
    """Raised when every provider in a task tier fails."""
