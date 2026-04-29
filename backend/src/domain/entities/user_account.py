"""UserAccount entity — data-model.md §1."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.domain.errors import LastSuperAdminError
from src.domain.value_objects import Role

__all__ = ["UserAccount"]


@dataclass(slots=True)
class UserAccount:
    """A person authenticated through Clerk.

    The role transitions are enforced by ``promote_to_admin`` /
    ``demote_to_user``. Promotion to / demotion from ``SUPER_ADMIN`` is **not**
    exposed by the API in v1 — Super Admins are seeded only by the env
    allowlist on first sign-in (FR-007). The last-super-admin invariant
    (FR-006) is enforced by the application service that owns the transaction
    (it counts remaining Super Admins inside the same UoW); the entity itself
    raises if asked to demote a Super Admin without that check having been done
    first.
    """

    id: UUID
    clerk_user_id: str
    email: str
    role: Role
    created_at: datetime
    updated_at: datetime
    version: int = 1
    display_name: str | None = None

    @classmethod
    def provision(
        cls,
        *,
        id: UUID,
        clerk_user_id: str,
        email: str,
        super_admin_emails: frozenset[str],
        display_name: str | None,
        now: datetime,
    ) -> "UserAccount":
        """Create a new account for a never-seen-before Clerk user (FR-007).

        ``super_admin_emails`` is a normalised (lower-cased) frozenset.
        """

        norm = email.strip().lower()
        role = Role.SUPER_ADMIN if norm in super_admin_emails else Role.USER
        return cls(
            id=id,
            clerk_user_id=clerk_user_id,
            email=norm,
            display_name=display_name,
            role=role,
            created_at=now,
            updated_at=now,
            version=1,
        )

    def promote_to_admin(self, *, now: datetime) -> None:
        """USER → ADMIN (FR-005). No-op if already ADMIN; refused for SUPER_ADMIN."""

        if self.role is Role.SUPER_ADMIN:
            raise ValueError("Cannot demote a Super Admin via promote/demote API in v1")
        if self.role is Role.ADMIN:
            return
        self.role = Role.ADMIN
        self.updated_at = now
        self.version += 1

    def demote_to_user(
        self,
        *,
        now: datetime,
        remaining_super_admin_count_after: int | None = None,
    ) -> None:
        """ADMIN → USER (FR-005).

        If the caller is asking to demote a Super Admin, the application
        service must pass ``remaining_super_admin_count_after`` so the
        last-super-admin invariant (FR-006) is checked atomically.
        """

        if self.role is Role.SUPER_ADMIN:
            if remaining_super_admin_count_after is None:
                raise ValueError(
                    "Demoting a Super Admin requires the post-transition count "
                    "for the FR-006 invariant"
                )
            if remaining_super_admin_count_after < 1:
                raise LastSuperAdminError(
                    "At least one Super Admin must remain (FR-006)",
                )
        if self.role is Role.USER:
            return
        self.role = Role.USER
        self.updated_at = now
        self.version += 1


@dataclass(frozen=True, slots=True)
class CurrentUser:
    """Snapshot of the authenticated caller used by interface-layer guards.

    Lives in the domain layer because it is consumed by application use cases
    that need to record audit metadata (FR-032) and check role permissions.
    """

    id: UUID
    clerk_user_id: str
    email: str
    role: Role


# Re-export so ``from src.domain.entities import CurrentUser`` works.
__all__.append("CurrentUser")
