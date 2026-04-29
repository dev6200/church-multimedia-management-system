# Phase 1 Data Model: Catholic Church Songlist Management SaaS

**Feature**: `002-church-songlist-management`
**Date**: 2026-04-28
**Status**: Complete

This document defines the persistent data model: entities, fields, relationships, validation rules, and state transitions. The model is expressed in domain terms; concrete column types reflect the chosen storage (PostgreSQL 16). Identifiers are UUIDv7 for natural ordering. All timestamps are `timestamptz` and stored in UTC.

Entities are derived from the spec's `Key Entities` section and from the functional requirements that constrain them.

---

## Entity overview

```text
                 ┌──────────────────┐
                 │  UserAccount     │  (synced from Clerk on first sign-in)
                 └─────────┬────────┘
              created_by / updated_by (audit)
                           │
                           ▼
┌─────────────┐    ┌──────────────────┐    ┌──────────────────────────┐
│  Composer   │◄───┤      Song        ├───►│ SongOptionalFieldValue   │
└─────────────┘ M:N└─────────┬────────┘ 1:N└──────────┬───────────────┘
                             │ M:N                    │ N:1
                             ▼                        ▼
                  ┌────────────────────┐   ┌────────────────────────────┐
                  │  TaxonomyValue     │   │ OptionalFieldDefinition    │
                  │ (kind=Season|Mass| │   │ (kind=Link)                │
                  │  SpecialEvent)     │   │                            │
                  └────────────────────┘   └────────────────────────────┘
```

---

## 1. UserAccount

Represents an authenticated person; mirrors a Clerk user.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDv7 PK | Internal identifier |
| `clerk_user_id` | TEXT, NOT NULL, UNIQUE | Canonical reference to Clerk |
| `email` | CITEXT, NOT NULL | Lower-cased / case-insensitive; pulled from Clerk JWT, refreshed on each login |
| `display_name` | TEXT, NULLABLE | Mirrors Clerk profile |
| `role` | ENUM(`SUPER_ADMIN`,`ADMIN`,`USER`), NOT NULL, DEFAULT `USER` | RBAC role |
| `created_at` | TIMESTAMPTZ, NOT NULL | DB default `now()` |
| `updated_at` | TIMESTAMPTZ, NOT NULL | Updated on every write |
| `version` | INTEGER, NOT NULL, DEFAULT 1 | Optimistic-lock counter |

**Indexes**: `UNIQUE(clerk_user_id)`, `INDEX(email)`.

**Validation rules**:
- `email` MUST be a syntactically valid email (validated upstream by Clerk; backend trusts JWT claim).
- `role` transitions:
  - `USER → ADMIN` and `ADMIN → USER`: only by a `SUPER_ADMIN` (FR-005).
  - Any transition involving `SUPER_ADMIN` (promotion to / demotion from) is **not exposed via the application API in v1**. Super Admins are seeded only by the env allowlist on first sign-in (FR-007).
  - The system MUST refuse any operation that would leave zero `SUPER_ADMIN` accounts (FR-006). Self-demotion of the last Super Admin is therefore refused.
- `email` allowlist match (FR-007): on creation, if `lower(email) ∈ SUPER_ADMIN_EMAILS`, set `role = SUPER_ADMIN`; else `role = USER`.

**State transitions**:

```text
[absent]
   │ first authenticated request with a Clerk JWT
   ▼
USER ◄───────────────────► ADMIN          (Super Admin promotes/demotes)
   │
   └─ if email ∈ allowlist on creation: created directly as SUPER_ADMIN
SUPER_ADMIN  ── (no demotion API in v1; protected by FR-006 invariant)
```

---

## 2. Song

The core catalog entity.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDv7 PK | |
| `title` | TEXT, NOT NULL | Trimmed; no leading/trailing whitespace allowed |
| `dedup_key` | TEXT, NOT NULL, UNIQUE | SHA-256 hex of `lower(trim(title)) + '|' + sorted(set(lower(trim(composer.name)))).join(',')`. Computed in the domain layer. Enforces FR-009. |
| `created_at` | TIMESTAMPTZ, NOT NULL | |
| `updated_at` | TIMESTAMPTZ, NOT NULL | |
| `created_by` | UUID FK → `UserAccount.id`, NOT NULL | Audit (FR-032) |
| `updated_by` | UUID FK → `UserAccount.id`, NOT NULL | Audit (FR-032) |
| `version` | INTEGER, NOT NULL, DEFAULT 1 | Optimistic lock (FR-030) |

**Indexes**:
- `UNIQUE(dedup_key)` — uniqueness invariant.
- `GIN(title gin_trgm_ops)` — partial-match search on title.
- `INDEX(updated_at DESC)` — pagination by recency.

**Validation rules**:
- `title` MUST be 1–200 characters after trim; whitespace-only rejected (FR-008).
- A song MUST have ≥1 composer (enforced via the `song_composers` join, see §3) (FR-008).
- `dedup_key` collision → reject with HTTP 409 referencing the conflicting song (FR-009).

**Lifecycle**:

```text
[create] → [exists] ─┬─► [update] → [exists]
                     └─► [delete] → [absent]    (hard delete; no soft-delete in v1)
```

Concurrent updates: each `UPDATE` is gated by `WHERE id=:id AND version=:expected`. Failure returns 409 (FR-030).

---

## 3. Composer & Song↔Composer association

Composers are normalised so the same author across multiple songs is referenced by the same row, enabling clean composer search and listing.

### 3a. Composer

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDv7 PK | |
| `name` | TEXT, NOT NULL | Display form |
| `name_norm` | CITEXT, NOT NULL, UNIQUE | `lower(trim(name))`; stable lookup key |
| `created_at` | TIMESTAMPTZ, NOT NULL | |

**Indexes**:
- `UNIQUE(name_norm)`
- `GIN(name gin_trgm_ops)` — composer name search (FR-023).

**Validation rules**:
- `name` MUST be 1–120 characters after trim.
- Composers are auto-created on first reference by name (find-or-create within a use-case transaction).

### 3b. song_composers (association table)

| Field | Type | Notes |
|---|---|---|
| `song_id` | UUID FK → `Song.id` (ON DELETE CASCADE) | |
| `composer_id` | UUID FK → `Composer.id` (ON DELETE RESTRICT) | A Composer cannot be deleted while still referenced |
| PRIMARY KEY | (`song_id`, `composer_id`) | |

**Validation rules**:
- For any song, the set of `composer_id`s MUST be non-empty (FR-008).
- The set is an **unordered set** for dedup purposes (FR-009).

---

## 4. TaxonomyValue (Seasons / Masses / Special Events)

Three independent admin-defined taxonomies (FR-015). Modelled as a single table partitioned by `kind`.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDv7 PK | |
| `kind` | ENUM(`SEASON`, `MASS`, `SPECIAL_EVENT`), NOT NULL | |
| `name` | TEXT, NOT NULL | Display |
| `name_norm` | CITEXT, NOT NULL | `lower(trim(name))` |
| `created_at`, `updated_at` | TIMESTAMPTZ | |
| `created_by`, `updated_by` | UUID FK → `UserAccount.id` | (FR-032) |
| `version` | INTEGER, NOT NULL, DEFAULT 1 | Optimistic lock |

**Indexes**:
- `UNIQUE(kind, name_norm)` — names unique within their kind, but the same name can appear in different kinds (e.g., "Christmas" could be a Season and a Special Event); confirmed allowed by FR-015.

**Validation rules**:
- `name` 1–80 characters after trim, non-empty.
- Rename: changing `name` updates `name_norm`; uniqueness re-checked.
- Delete with usages → confirm-and-detach flow (see §6).

**Seed values (FR-020)**: kind=`SEASON`: Advent, Christmas, Lent, Easter, Ordinary Time.

### 4a. song_taxonomy_values (association)

| Field | Type | Notes |
|---|---|---|
| `song_id` | UUID FK → `Song.id` (ON DELETE CASCADE) | |
| `taxonomy_value_id` | UUID FK → `TaxonomyValue.id` (ON DELETE RESTRICT) | Restricted: deletion goes through detach use case |
| PRIMARY KEY | (`song_id`, `taxonomy_value_id`) | |

A song can hold zero or more values per kind (FR-013); querying uses joins filtered on `kind`.

---

## 5. OptionalFieldDefinition & SongOptionalFieldValue

Admin-defined "optional song fields" — currently all of kind `LINK` (URL).

### 5a. OptionalFieldDefinition

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDv7 PK | |
| `label` | TEXT, NOT NULL | E.g., "PowerPoint link", "Sheet Music" |
| `label_norm` | CITEXT, NOT NULL, UNIQUE | `lower(trim(label))` |
| `kind` | ENUM(`LINK`), NOT NULL, DEFAULT `LINK` | Open enum; v1 supports only LINK |
| `created_at`, `updated_at` | TIMESTAMPTZ | |
| `created_by`, `updated_by` | UUID FK → `UserAccount.id` | (FR-032) |
| `version` | INTEGER, NOT NULL, DEFAULT 1 | |

**Indexes**: `UNIQUE(label_norm)`.

**Validation rules**:
- `label` 1–60 characters after trim.
- Rename preserves all existing per-song values (edge-case requirement) — only the label changes.

**Seed values (FR-021)**: `PowerPoint link`, `Sheet Music`, `YouTube link`, `Lyrics link`. (Rows exist; no per-song values.)

### 5b. SongOptionalFieldValue

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDv7 PK | |
| `song_id` | UUID FK → `Song.id` (ON DELETE CASCADE) | |
| `definition_id` | UUID FK → `OptionalFieldDefinition.id` (ON DELETE RESTRICT) | Restricted; deletion via detach |
| `value_url` | TEXT, NOT NULL | Validated as a URL on write (FR-016) |
| `created_at`, `updated_at` | TIMESTAMPTZ | |
| UNIQUE (`song_id`, `definition_id`) | | At most one value per definition per song |

**Validation rules**:
- `value_url` MUST parse as an absolute `http://` or `https://` URL (FR-016).
- Absent rows mean "field not provided" (FR-014); not shown to Users (FR-014, FR-025).

---

## 6. "Detach" semantics for taxonomy / definition deletion (FR-019)

Deletion of a `TaxonomyValue` or `OptionalFieldDefinition` is a multi-step use case:

1. **Probe** — application service queries usage count (number of referencing songs).
2. **Confirmation contract** — frontend displays the count and offers exactly two options: cancel or detach. (Cascade-delete of songs is **not offered**.)
3. **Detach + delete** — within a single transaction:
   - For taxonomy: delete all `song_taxonomy_values` rows where `taxonomy_value_id = :id`, then delete the `TaxonomyValue` itself.
   - For optional-field definition: delete all `SongOptionalFieldValue` rows where `definition_id = :id`, then delete the definition.
   - Affected songs' `updated_at` / `updated_by` are bumped (audit trail) but their `version` is **not** incremented for this server-driven detach (otherwise concurrent edits by Admins would all conflict). Rationale: the detach is a system-mediated maintenance action; the spec's concurrency requirement (FR-030) targets human-initiated edits.
4. **No-usage delete** — same code path; usage count is zero, no detach work is performed, but Admin still confirms (FR-019 last sentence).

The FK from association tables uses `ON DELETE RESTRICT` precisely to force every deletion through this use case.

---

## 7. Audit fields summary (FR-032)

Every mutable entity (Song, TaxonomyValue, OptionalFieldDefinition, UserAccount) carries:

- `created_at`, `created_by`
- `updated_at`, `updated_by`

Composer rows (§3a) record only `created_at` because they are write-only, identity-only entities (renaming a composer is out of scope for v1; if a name needs correction, the song's composer set is edited instead, which may then orphan a composer — orphan cleanup is out of scope for v1).

---

## 8. Derived views / read models

For the User-facing catalog read path, a single SQL view (or computed in the application layer) joins:

```text
song
  ⨝ song_composers ⨝ composer
  ⨝ song_taxonomy_values ⨝ taxonomy_value (per kind)
  ⨝ song_optional_field_values ⨝ optional_field_definition
```

This is materialised on demand; the catalog scale (≤5,000 songs) does not justify a denormalised projection in v1.

---

## 9. Validation rule summary (cross-cut)

| Rule | Source FR | Layer enforced |
|---|---|---|
| Title required, ≤200 chars, trimmed | FR-008 | Domain (Song entity); DB NOT NULL + CHECK |
| ≥1 composer required | FR-008 | Domain (use case `CreateSong`); FK association non-empty checked at commit |
| Unique (title, composer set), case-insensitive, unordered | FR-009 | Domain computes `dedup_key`; DB `UNIQUE(dedup_key)` |
| Optional URL fields parse as absolute HTTP(S) | FR-016 | Domain value object `LinkUrl`; rejected before persistence |
| Taxonomy kinds independent | FR-015 | Schema (`kind` discriminator) + service layer constructs queries per kind |
| Concurrent-edit detection | FR-030 | DB `version` column + conditional UPDATE → 409 |
| Audit who/when | FR-032 | All mutating use cases require `acting_user_id`; setters in entity |
| Never zero Super Admins | FR-006 | Application service `RoleService.demote(...)` invariant check inside transaction |
| First Super Admin from email allowlist | FR-007 | `UserProvisioningService.on_first_sign_in(...)` |

---

## 10. Migration ordering (Alembic)

1. Enable `pg_trgm` extension.
2. Create enums (`user_role`, `taxonomy_kind`, `optional_field_kind`).
3. `user_accounts`.
4. `composers`.
5. `taxonomy_values`.
6. `optional_field_definitions`.
7. `songs`.
8. `song_composers`.
9. `song_taxonomy_values`.
10. `song_optional_field_values`.
11. Add trigram GIN indexes on `songs.title` and `composers.name`.
12. Seed `taxonomy_values` (kind=SEASON: Advent, Christmas, Lent, Easter, Ordinary Time) and `optional_field_definitions` (PowerPoint link, Sheet Music, YouTube link, Lyrics link). Seed migration MUST be idempotent.
