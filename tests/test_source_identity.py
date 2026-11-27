"""Pure tests for source identity canonicalization."""

from app.domain.source_identity import (
    canonicalize_source_for_lookup,
    canonicalize_url,
    make_pdf_source,
    source_lookup_keys,
)

TRACKED_HTTPS = "HTTPS://Example.COM:443/docs?utm_source=news&b=2&a=1#section"
TRACKED_HTTP = "http://EXAMPLE.com:80/?gclid=g&fbclid=f&keep=1"


def test_canonicalize_url_normalizes_https_variant() -> None:
    assert canonicalize_url(TRACKED_HTTPS) == "https://example.com/docs?a=1&b=2"


def test_canonicalize_url_normalizes_http_variant() -> None:
    assert canonicalize_url(TRACKED_HTTP) == "http://example.com/?keep=1"


def test_canonicalize_url_is_idempotent_for_https() -> None:
    canonical = canonicalize_url(TRACKED_HTTPS)

    assert canonicalize_url(canonical) == canonical


def test_canonicalize_url_is_idempotent_for_http() -> None:
    canonical = canonicalize_url(TRACKED_HTTP)

    assert canonicalize_url(canonical) == canonical


def test_canonicalize_url_returns_non_url_input_stripped() -> None:
    assert canonicalize_url("  notes.pdf  ") == "notes.pdf"


def test_make_pdf_source_is_deterministic() -> None:
    assert make_pdf_source(b"abc") == (
        "pdf:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_canonicalize_source_for_lookup_passes_pdf_through() -> None:
    assert canonicalize_source_for_lookup("  pdf:abc123  ") == "pdf:abc123"


def test_canonicalize_source_for_lookup_canonicalizes_url() -> None:
    assert canonicalize_source_for_lookup(TRACKED_HTTPS) == (
        "https://example.com/docs?a=1&b=2"
    )


def test_source_lookup_keys_include_legacy_alias() -> None:
    assert source_lookup_keys(TRACKED_HTTPS) == [
        "https://example.com/docs?a=1&b=2",
        TRACKED_HTTPS,
    ]


def test_source_lookup_keys_avoid_duplicate_for_legacy_filename() -> None:
    assert source_lookup_keys("  notes.pdf  ") == ["notes.pdf"]
