"""Shared types for the AI provider adapters."""


class ProviderError(RuntimeError):
    """
    Raised when an AI provider rejects or fails a request.

    Providers previously printed the failure to a console the user never sees
    and returned an empty stream, which surfaced as a generic "analysis
    failed" message. Carrying the provider's own wording lets the UI explain
    what actually went wrong (bad key, rate limit, unsupported parameter).
    """


class _Truncated:
    """Sentinel yielded after the last chunk when the model hit its cap."""

    __slots__ = ()

    def __repr__(self):
        return "TRUNCATED"


TRUNCATED = _Truncated()


def error_detail(response, provider_label):
    """Pull the most useful message out of a provider's error response."""
    try:
        payload = response.json()
    except ValueError:
        payload = None

    detail = None
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            detail = error.get("message")
        elif isinstance(error, str):
            detail = error
        detail = detail or payload.get("message") or payload.get("detail")

    detail = str(detail).strip() if detail else (response.text or "").strip()
    if not detail:
        detail = "no details returned"

    return f"{provider_label} request failed ({response.status_code}): {detail[:500]}"
