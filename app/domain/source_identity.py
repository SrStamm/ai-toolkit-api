"""Pure helpers for canonical document source identities."""

from hashlib import sha256
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_QUERY_KEYS = frozenset({"fbclid", "gclid", "gbraid", "wbraid"})


def _is_tracking_param(key: str) -> bool:
    """Return True when a query parameter is a known tracking parameter."""
    lowered = key.lower()
    return lowered in TRACKING_QUERY_KEYS or lowered.startswith("utm_")


def canonicalize_url(raw: str) -> str:
    """Canonicalize an HTTP(S) URL for use as a stable source key.

    Args:
        raw: Candidate URL or arbitrary source string.

    Returns:
        The canonical URL, or the stripped input when it is not an HTTP(S) URL.
    """
    stripped = raw.strip()
    try:
        parts = urlsplit(stripped)
    except ValueError:
        return stripped

    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"}:
        return stripped

    netloc = parts.netloc.lower()
    default_port = ":80" if scheme == "http" else ":443"
    if netloc.endswith(default_port):
        netloc = netloc[: -len(default_port)]

    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not _is_tracking_param(key)
    ]
    return urlunsplit((scheme, netloc, parts.path or "/", urlencode(sorted(query_pairs)), ""))


def make_pdf_source(content: bytes) -> str:
    """Build a content-based source key for uploaded PDF bytes."""
    return f"pdf:{sha256(content).hexdigest()}"


def canonicalize_source_for_lookup(raw: str) -> str:
    """Return the canonical lookup key for a PDF, URL, or legacy filename."""
    stripped = raw.strip()
    if stripped.lower().startswith("pdf:"):
        return stripped
    return canonicalize_url(stripped)


def source_lookup_keys(raw: str) -> list[str]:
    """Return canonical key first, then the raw key for legacy aliases."""
    stripped = raw.strip()
    canonical = canonicalize_source_for_lookup(stripped)
    if canonical == stripped:
        return [canonical]
    return [canonical, stripped]
