"""Contract test for FR-031 — anonymous reads on taxonomy + optional-fields
(T058).

Per the OpenAPI contract, ``GET /api/v1/admin/taxonomies/{kind}`` and
``GET /api/v1/admin/optional-fields`` are reachable without a Bearer token
because the public catalog filter UI consumes them.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.domain.entities import OptionalFieldDefinition, OptionalFieldKind, TaxonomyValue
from src.domain.value_objects import TaxonomyKind


def _seed_season(name: str) -> TaxonomyValue:
    actor = uuid4()
    return TaxonomyValue.create(
        id=uuid4(),
        kind=TaxonomyKind.SEASON,
        name=name,
        actor_id=actor,
        now=datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc),
    )


def _seed_optional_field(label: str) -> OptionalFieldDefinition:
    actor = uuid4()
    return OptionalFieldDefinition.create(
        id=uuid4(),
        label=label,
        actor_id=actor,
        now=datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc),
        kind=OptionalFieldKind.LINK,
    )


@pytest.mark.contract
async def test_anonymous_can_list_taxonomies(client, taxonomies_store) -> None:
    advent = _seed_season("Advent")
    christmas = _seed_season("Christmas")
    taxonomies_store[advent.id] = advent
    taxonomies_store[christmas.id] = christmas

    response = await client.get("/api/v1/admin/taxonomies/seasons")
    assert response.status_code == 200
    names = sorted(item["name"] for item in response.json())
    assert names == ["Advent", "Christmas"]


@pytest.mark.contract
async def test_anonymous_can_list_optional_fields(
    client, optional_fields_store
) -> None:
    powerpoint = _seed_optional_field("PowerPoint link")
    sheet_music = _seed_optional_field("Sheet Music")
    optional_fields_store[powerpoint.id] = powerpoint
    optional_fields_store[sheet_music.id] = sheet_music

    response = await client.get("/api/v1/admin/optional-fields")
    assert response.status_code == 200
    labels = sorted(d["label"] for d in response.json())
    assert labels == ["PowerPoint link", "Sheet Music"]


@pytest.mark.contract
async def test_unknown_taxonomy_kind_returns_404(client) -> None:
    response = await client.get("/api/v1/admin/taxonomies/not_a_kind")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "not_found"
