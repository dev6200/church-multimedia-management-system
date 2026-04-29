# Feature Specification: Catholic Church Songlist Management SaaS

**Feature Branch**: `002-church-songlist-management`
**Created**: 2026-04-27
**Status**: Draft
**Input**: User description: "Build a SaaS application that will manage a songlist for the catholic church. Three users in the app: Super Admin, Admin, and User. The Super Admin can promote a user to Admin. The admin manages the song list. The user can search for the songs and see their details. The admin can create/update/delete songs. The admin is required to input a song name/title and the composer(s) as the required fields. The song can be tagged based on the church's season. The season is dynamic based on what the admin specifies. This is to avoid developer intervention when updates to set values are needed. The song can be tagged to a specific mass like 1st Sunday of Ordinary Time. It can also be tagged to a special event, feasts, memorials like Immaculate Concepcion or Good Friday. These tags can be dynamic but different fields. Other fields that the admin can add dynamically are say powerpoint links, sheet music link, youtube lnk, lyrics link. Note that the songs may not have all the fields. This may fit better for a NoSQL, but raise if you think it is better. We can implement authentication by using third party like Google OAuth or Clerk. We need to implement RBAC as we have different roles. Users can view the songlist, filter them and search them. This frontend should be mobile responsive."

## Clarifications

### Session 2026-04-27

- Q: How is the very first Super Admin established at deployment time? → A: Pre-seeded by deployment config — one or more email addresses listed in env/config are auto-promoted to Super Admin on their first authenticated sign-in.
- Q: Is sign-in required to view the catalog, or can unauthenticated visitors browse? → A: Public read-only browse, search, filter, and song-detail view are allowed without sign-in; sign-in is required only for Admin / Super Admin write actions (song create/update/delete, taxonomy and field-definition management, role management).
- Q: When an Admin deletes an in-use taxonomy value or optional-field definition, what happens? → A: System shows a confirm dialog stating how many songs reference it; Admin chooses either cancel or detach (remove the reference from those songs while keeping the songs themselves). Cascade-delete of referencing songs is not offered.
- Q: Are duplicate songs allowed in the catalog? → A: The combination of title and composer set must be unique (case-insensitive, composer set compared as an unordered set). Two songs with the same title but different composers are allowed; two songs with the same title AND the same composers are rejected.
- Q: Which identity provider will be used? → A: Clerk, with Google sign-in enabled inside Clerk so end users still see "Sign in with Google". Clerk owns user records and provides the admin/dashboard surface that backs Super Admin user management.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse, search, and view songs (Priority: P1)

A church member (signed in or not) opens the songlist on a phone or laptop, searches for a song by title or composer, filters the catalog by liturgical season (e.g., "Advent"), specific mass (e.g., "1st Sunday of Ordinary Time"), or special event (e.g., "Good Friday"), and opens a song to see its full details — including any available links such as lyrics, sheet music, slide decks, or video. Sign-in is not required for this read-only flow.

**Why this priority**: This is the primary value-delivery flow for the largest audience (members of the church choir/music ministry). Without it, the catalog is invisible to its end users.

**Independent Test**: With a pre-seeded catalog of songs and tags, an unauthenticated visitor can run a search, apply at least one filter, and open a song's detail view to confirm all populated fields render correctly on both mobile and desktop widths; the same flow MUST also work for a signed-in User.

**Acceptance Scenarios**:

1. **Given** the catalog contains a song "Salve Regina" tagged with the "Advent" season, **When** the User filters by "Advent", **Then** "Salve Regina" appears in the results list.
2. **Given** the catalog contains 50 songs, **When** the User types a partial title or composer name, **Then** matching songs appear in a results list within 1 second of the user pausing typing.
3. **Given** a song has only a title, composers, and a YouTube link populated, **When** the User opens its detail view, **Then** unset optional fields are not shown and the YouTube link is presented as an actionable link.
4. **Given** the User accesses the catalog on a 360px-wide mobile screen, **When** they scroll the search results, **Then** layout, controls, and tap targets remain usable without horizontal scrolling.

---

### User Story 2 - Admin manages the song catalog (Priority: P1)

An Admin signs in, creates a new song by entering a title and one or more composers (the only required fields), assigns relevant season / mass / special-event tags from existing taxonomy values, and populates any subset of the available optional link fields (e.g., PowerPoint link, sheet music link, YouTube link, lyrics link). The Admin can later edit any field of any song or delete a song.

**Why this priority**: Without songs in the catalog, end users have nothing to browse. This is the content-creation flow that the entire product depends on.

**Independent Test**: An Admin account can sign in, create a song with only the required fields, edit it to add tags and links, and delete it — verifying that validation enforces required fields and that changes are reflected immediately in the User-facing catalog.

**Acceptance Scenarios**:

1. **Given** an Admin is on the "create song" form, **When** they submit without a title or without at least one composer, **Then** the form rejects the submission and identifies the missing required field(s).
2. **Given** an Admin creates a song with only a title and a composer, **When** they save it, **Then** the song appears in the catalog with no tags and no optional fields populated.
3. **Given** an existing song, **When** an Admin edits its tags and adds a sheet-music link, **Then** the updated song reflects the new values to all Users on next load.
4. **Given** an existing song, **When** an Admin deletes it, **Then** it no longer appears in any User search or filter result.
5. **Given** a User is signed in without the Admin role, **When** they attempt to access any song create / edit / delete action, **Then** the action is refused.

---

### User Story 3 - Admin manages dynamic taxonomies and optional field definitions (Priority: P2)

An Admin manages three independent taxonomy lists — Seasons, Masses, and Special Events — adding, renaming, or removing values without developer involvement. Separately, an Admin manages the catalog of "optional song fields" (e.g., add a new field type "Spotify link" or rename "Sheet Music" to "Score PDF") so that the song form and detail view automatically reflect those definitions.

**Why this priority**: This is what makes the catalog adapt to the parish's evolving liturgical and media needs. It is not required to ship the first usable catalog (a fixed initial seed could carry the MVP), but it removes the long-term dependency on developers for routine content changes.

**Independent Test**: An Admin can add a new Season value, immediately tag a song with it, and confirm a User filtering by that new value sees the song. Likewise, adding a new optional field definition causes that field to appear on the song create/edit form for all subsequent edits.

**Acceptance Scenarios**:

1. **Given** the Seasons taxonomy contains "Advent, Lent, Ordinary Time", **When** an Admin adds "Easter", **Then** "Easter" becomes selectable on every song's tag picker and on the User filter UI.
2. **Given** a Mass value "3rd Sunday of Advent" is currently assigned to 4 songs, **When** an Admin attempts to delete it, **Then** the system either prevents deletion or warns about and handles the impact on those 4 songs in a way the Admin explicitly confirms.
3. **Given** an Admin renames the optional field "PowerPoint link" to "Slides link", **When** Users next view any song that has that field populated, **Then** the new label appears with the existing link value preserved.
4. **Given** an Admin adds a new optional field "Audio recording link", **When** an Admin opens any song's edit form, **Then** the new field appears as an empty optional input.

---

### User Story 4 - Super Admin manages user roles (Priority: P3)

A Super Admin views the list of registered users and promotes a User to the Admin role, or demotes an Admin back to User, so the parish music director can delegate (or revoke) catalog-management responsibilities.

**Why this priority**: Role governance matters for long-term operation, but the system can ship and run with a single admin account in the short term. It is a P3 because it is essential for healthy ongoing operation but not for first-day usefulness.

**Independent Test**: A Super Admin signs in, finds an existing User account in the user list, promotes it to Admin, and confirms that account can now perform Admin actions; then demotes it back and confirms those Admin actions are refused.

**Acceptance Scenarios**:

1. **Given** a registered User "alice@example.org" has the User role, **When** the Super Admin promotes her to Admin, **Then** on her next request she can perform Admin-only actions.
2. **Given** an Admin "bob@example.org", **When** the Super Admin demotes him to User, **Then** Bob's subsequent attempts to create/update/delete songs or taxonomies are refused.
3. **Given** an Admin or User is signed in, **When** they attempt to access the role-management screen, **Then** access is refused.
4. **Given** there is exactly one Super Admin in the system, **When** they attempt to demote themselves, **Then** the action is refused with a clear message that at least one Super Admin must remain.

---

### Edge Cases

- A song is created with the minimum required fields only (title + composers, no tags, no links) — it must still be findable by title/composer search.
- An Admin attempts to create a song whose title and composer set exactly match an existing song — the system must reject it and identify the conflicting song so the Admin can decide whether to edit the existing entry or change the composers.
- A song has multiple composers — every composer name must be searchable.
- A song is tagged to multiple seasons or multiple masses simultaneously (e.g., suitable for both Advent and Christmas) — filters must include it under each tag.
- A user searches for a term that matches no songs — the UI must show a clear empty-state, not an error.
- An Admin attempts to delete a taxonomy value or optional-field definition that is currently assigned to one or more songs — the system must show a confirmation dialog stating the count of referencing songs and offering only cancel or detach (remove references but keep the songs).
- Two Admins edit the same song simultaneously — the system must not silently overwrite one Admin's changes with the other's stale view.
- The very last Super Admin attempts to demote or delete themselves — the system must prevent it.
- A User loses network connectivity mid-search on mobile — the UI must surface the failure rather than appearing to hang.
- A signed-in user's role is changed (promoted/demoted) while they have the app open — their effective permissions on the next privileged action must reflect the new role.
- An optional link field is renamed by an Admin while songs reference it — existing values must be preserved under the new label. If removed, see FR-019: a confirm-and-detach flow drops the values from every referencing song.

## Requirements *(mandatory)*

### Functional Requirements

#### Authentication & Authorization

- **FR-001**: System MUST authenticate every privileged request (any Admin or Super Admin action — song create/update/delete, taxonomy management, optional-field-definition management, role management) via Clerk as the third-party identity provider, with Google sign-in enabled inside Clerk; no first-party password storage is permitted. Read-only catalog browse, search, filter, and song-detail endpoints MUST be reachable without authentication.
- **FR-002**: System MUST assign every authenticated account exactly one role from the set { Super Admin, Admin, User }.
- **FR-003**: System MUST default newly registered accounts to the User role.
- **FR-004**: System MUST enforce role-based access control on every privileged action (song create/update/delete, taxonomy management, optional-field-definition management, role management) and refuse unauthorized requests with a clear, user-visible error.
- **FR-005**: System MUST allow only Super Admins to promote a User to Admin or demote an Admin back to User.
- **FR-006**: System MUST prevent removal or demotion of the last remaining Super Admin.
- **FR-007**: System MUST establish the initial Super Admin(s) by reading a list of authorized email addresses from deployment configuration; when an account whose identity-provider email matches an entry on that list signs in for the first time, the system MUST auto-promote that account to Super Admin. Accounts whose emails are not on that list MUST default to the User role per FR-003.

#### Song Catalog (Admin)

- **FR-008**: Admins MUST be able to create a song by providing a title and at least one composer; both fields are required.
- **FR-009**: System MUST reject any song creation or update attempt that omits the title, leaves the composers list empty, or would result in two songs sharing the same title AND the same composer set (compared case-insensitively, with composers compared as an unordered set). The rejection error MUST clearly identify the conflicting existing song.
- **FR-010**: System MUST support multiple composers per song.
- **FR-011**: Admins MUST be able to update any field of any existing song, including its tags and optional link fields.
- **FR-012**: Admins MUST be able to delete any existing song.
- **FR-013**: Admins MUST be able to assign zero or more values from each of the three taxonomies (Seasons, Masses, Special Events) to a song.
- **FR-014**: Admins MUST be able to populate any subset of the defined optional link fields on a song; absent fields MUST be treated as "not provided" and not shown to Users.
- **FR-015**: System MUST treat the three taxonomies (Seasons, Masses, Special Events) as independent — values from one taxonomy MUST NOT appear in another.
- **FR-016**: System MUST validate any optional field declared as a link as a syntactically valid URL before saving.

#### Dynamic Taxonomies & Field Definitions (Admin)

- **FR-017**: Admins MUST be able to create, rename, and remove values within each of the three taxonomies (Seasons, Masses, Special Events) without requiring a code change or developer intervention.
- **FR-018**: Admins MUST be able to define, rename, and remove optional song-field definitions (e.g., "Sheet Music link", "YouTube link", "Lyrics link", "PowerPoint link") without requiring a code change.
- **FR-019**: When an Admin attempts to remove a taxonomy value or optional-field definition that is currently in use, the system MUST display a confirmation dialog that states the exact number of songs that reference the value and offers exactly two choices: cancel (no change), or detach (delete the value/definition and remove every reference to it from referencing songs while leaving those songs otherwise intact). Cascade-deletion of referencing songs MUST NOT be offered. Removal of a value that is not in use MUST also require an explicit confirmation but does not need the count display.
- **FR-020**: System MUST seed an initial set of common Catholic liturgical season values (e.g., Advent, Christmas, Lent, Easter, Ordinary Time) so the catalog is usable on first deployment.
- **FR-021**: System MUST seed an initial, empty-but-defined set of optional link field definitions for PowerPoint, Sheet Music, YouTube, and Lyrics so the song form is immediately useful.

#### Song Catalog (User)

- **FR-022**: Users MUST be able to view a paginated list of all songs in the catalog.
- **FR-023**: Users MUST be able to search the catalog by song title and by composer name, including partial matches.
- **FR-024**: Users MUST be able to filter the catalog by one or more values from each of the three taxonomies (Seasons, Masses, Special Events), with multiple filters combining as logical AND across taxonomies and logical OR within a taxonomy.
- **FR-025**: Users MUST be able to open any song's detail view to see its title, all composers, all assigned tags, and every optional link field that has a value populated.
- **FR-026**: System MUST present every populated link field on a song as an actionable link that opens in a new tab/window.

#### Frontend Experience

- **FR-027**: System MUST render correctly and remain usable on viewport widths from 320px through desktop sizes, with no horizontal scrolling and tap targets meeting standard mobile-accessibility sizes.
- **FR-028**: System MUST display a clear empty-state message when a search or filter combination returns no results.
- **FR-029**: System MUST surface network or server failures to the user with a clear retry path rather than appearing to hang.

#### Data integrity & operations

- **FR-030**: System MUST detect and refuse conflicting concurrent updates to the same song, prompting the second editor to refresh.
- **FR-031**: System MUST allow unauthenticated visitors to browse the catalog list, run searches, apply filters, and open any song's detail view without signing in. Authentication is required only to perform Admin or Super Admin write actions.
- **FR-032**: System MUST persist a record of who created or last modified each song and each taxonomy/field-definition value, and the time of that change, for accountability.

### Key Entities *(include if feature involves data)*

- **User Account**: A person authenticated via the third-party identity provider. Holds a role (Super Admin, Admin, or User), an email/identity reference from the provider, and a display name.
- **Song**: A liturgical song. Required attributes: title, composers (one or more). Optional attributes: zero or more tags from each taxonomy (Seasons, Masses, Special Events), zero or more populated optional link fields. Carries audit metadata (created-by, updated-by, timestamps). Identity invariant: the combination (title, composer set) is unique across the catalog (case-insensitive, composer set compared as an unordered set).
- **Season**: A value in the Seasons taxonomy (e.g., "Advent", "Lent"). Admin-defined.
- **Mass**: A value in the Masses taxonomy (e.g., "1st Sunday of Ordinary Time"). Admin-defined.
- **Special Event**: A value in the Special Events taxonomy (e.g., "Good Friday", "Immaculate Conception", "Christmas Eve Vigil"). Admin-defined.
- **Optional Field Definition**: A definition of an optional song attribute (e.g., "PowerPoint link", "Sheet Music link", "YouTube link", "Lyrics link"). Admin-defined; describes the label and the value's expected form (link / URL).
- **Optional Field Value**: A per-song, per-definition value that holds the actual link URL when populated; absent when the song does not provide that field.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Any visitor (signed in or not) can find a specific song that exists in the catalog (by title, composer, or any single tag filter) in under 30 seconds, on either mobile or desktop, without consulting documentation.
- **SC-002**: 95% of search and filter operations return results visible to the user within 1 second of input being submitted, for a catalog of up to 5,000 songs.
- **SC-003**: An Admin can create a fully tagged song (title, composers, at least one tag in each taxonomy, at least one populated optional link) in under 2 minutes from opening the create form.
- **SC-004**: 100% of songs in the catalog at any moment have a non-empty title and at least one composer (validation invariant).
- **SC-005**: An Admin can introduce a new tag value or a new optional link field type and use it on a song without requiring a deployment, build, restart, or code change.
- **SC-006**: 0 cases of unauthorized access succeed: no User can perform any Admin action, and no Admin can perform any Super Admin action, when verified against an automated permission audit covering every privileged endpoint.
- **SC-007**: The application renders without horizontal scroll and with usable tap targets on every supported viewport width from 320px upward, verified across the catalog list, song detail, and admin forms.
- **SC-008**: At least 90% of new Admins, after a 5-minute walkthrough, successfully complete song creation, song edit, and tag-value addition tasks without further help.

## Assumptions

- The product is single-tenant for v1: it serves one parish / one Catholic church community. Multi-parish or multi-tenant deployment is out of scope and would require a separate spec.
- All "links" provided in optional song fields are externally hosted URLs (e.g., a Google Slides URL, a YouTube URL, a Drive PDF URL). The system stores only the URLs and does not host, transcode, or proxy media files.
- Read access to the catalog is public: anonymous visitors and signed-in Users alike can browse, search, filter, and view song details. Neither can create songs, edit songs, manage tags, or manage roles. The User role exists today only as the default role for newly registered accounts and as the target of Super Admin promotion to Admin; it currently confers no read capabilities beyond what an anonymous visitor already has.
- Admins have full read/write authority over songs, taxonomies, and optional-field definitions, but they cannot manage user roles.
- Super Admins inherit all Admin capabilities plus exclusive access to user-role management.
- Authentication and identity are fully delegated to Clerk (with Google sign-in enabled inside Clerk); the application does not store passwords or run a forgot-password flow itself. The Clerk-issued user ID is the canonical reference for every account record. The Super Admin's user-list / promote-demote UI is allowed to delegate to Clerk's hosted dashboard or to wrap Clerk's user-management API; either is acceptable.
- The catalog scale for v1 is up to ~5,000 songs and a few thousand registered users; performance criteria are stated against that envelope.
- "Mobile responsive" means the same web application adapts to mobile viewports; a separate native iOS/Android app is out of scope for v1.
- Audit history is kept at the level of "who last changed it and when" (lightweight tracking). Full revision history with rollback is out of scope for v1.
- Recommendation for the planning phase: a relational database is likely the better fit despite the user's NoSQL hypothesis, because the dynamic taxonomies, optional-field definitions, and per-song optional values are naturally modelled as related lookup tables with referential-integrity guarantees that the deletion / rename / "in use" rules above depend on. A document store would still work but pushes integrity enforcement into the application layer. This decision should be revisited and locked in during `/speckit.plan`.
