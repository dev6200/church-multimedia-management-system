"""Unit test for ``DedupKey.compute`` (T039 — FR-009).

Asserts the documented invariants:
- case-insensitive on title and composer names
- whitespace-trimmed
- composer set is unordered (sorted internally before hashing)
- different (title, composer set) combos hash differently
"""

from __future__ import annotations

import pytest

from src.domain.value_objects import DedupKey


def test_dedup_key_is_case_insensitive_on_title() -> None:
    a = DedupKey.compute("Salve Regina", ["Anonymous"])
    b = DedupKey.compute("salve regina", ["Anonymous"])
    assert a == b


def test_dedup_key_is_case_insensitive_on_composers() -> None:
    a = DedupKey.compute("Salve Regina", ["Pierluigi da Palestrina"])
    b = DedupKey.compute("Salve Regina", ["pierluigi DA palestrina"])
    assert a == b


def test_dedup_key_trims_whitespace() -> None:
    a = DedupKey.compute("  Salve Regina  ", ["  Palestrina "])
    b = DedupKey.compute("Salve Regina", ["Palestrina"])
    assert a == b


def test_dedup_key_is_composer_order_insensitive() -> None:
    a = DedupKey.compute("Mass in B Minor", ["Bach", "Mendelssohn"])
    b = DedupKey.compute("Mass in B Minor", ["Mendelssohn", "Bach"])
    assert a == b


def test_dedup_key_is_composer_set_dedup() -> None:
    a = DedupKey.compute("Mass in B Minor", ["Bach", "Mendelssohn"])
    b = DedupKey.compute("Mass in B Minor", ["Bach", "BACH", "Mendelssohn"])
    assert a == b


def test_dedup_key_different_titles_hash_differently() -> None:
    a = DedupKey.compute("Ave Maria", ["Schubert"])
    b = DedupKey.compute("Ave Verum", ["Schubert"])
    assert a != b


def test_dedup_key_different_composer_sets_hash_differently() -> None:
    a = DedupKey.compute("Ave Maria", ["Schubert"])
    b = DedupKey.compute("Ave Maria", ["Gounod"])
    assert a != b


def test_dedup_key_rejects_empty_title() -> None:
    with pytest.raises(ValueError):
        DedupKey.compute("   ", ["Schubert"])


def test_dedup_key_rejects_empty_composer_set() -> None:
    with pytest.raises(ValueError):
        DedupKey.compute("Ave Maria", [])
