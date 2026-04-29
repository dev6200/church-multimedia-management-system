"""Unit test for ``LinkUrl.parse`` (T040 — FR-016)."""

from __future__ import annotations

import pytest

from src.domain.value_objects import LinkUrl


@pytest.mark.parametrize(
    "raw",
    [
        "https://example.org/file.pdf",
        "http://example.org",
        "https://docs.google.com/presentation/d/abc123/edit",
        "https://www.youtube.com/watch?v=abcdefg",
        "  https://example.org  ",  # surrounding whitespace trimmed
    ],
)
def test_parse_accepts_valid_http_or_https_urls(raw: str) -> None:
    parsed = LinkUrl.parse(raw)
    assert parsed.value.strip() == raw.strip()


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "ftp://example.org/file.txt",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "not a url",
        "://example.org",
        "https://",  # no host
    ],
)
def test_parse_rejects_non_http_urls(raw: str) -> None:
    with pytest.raises(ValueError):
        LinkUrl.parse(raw)
