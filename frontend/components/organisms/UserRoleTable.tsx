// UserRoleTable — Super Admin user list with inline role-change selects.
// Disables the demote/promote control for the only Super Admin in the list
// (defence-in-depth — server enforces FR-006 authoritatively).
"use client";

import { useAuth } from "@clerk/nextjs";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import type { Role, UserAccount } from "@/types/api";
import { ApiError } from "@/types/api";
import { createClientApiClient } from "@/services/api/client";
import { RoleBadge } from "@/components/atoms/RoleBadge";
import { RoleSelect } from "@/components/molecules/RoleSelect";

export interface UserRoleTableProps {
  initialUsers: UserAccount[];
}

function humanRole(r: Role): string {
  return r === "USER" ? "User" : r === "ADMIN" ? "Admin" : "Super Admin";
}

export function UserRoleTable({ initialUsers }: UserRoleTableProps) {
  const { getToken } = useAuth();
  const api = useMemo(
    () => createClientApiClient(async () => (await getToken()) ?? null),
    [getToken]
  );
  const [users, setUsers] = useState<UserAccount[]>(initialUsers);
  const [busyIds, setBusyIds] = useState<ReadonlySet<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const superAdminCount = users.filter((u) => u.role === "SUPER_ADMIN").length;

  async function setRole(
    user: UserAccount,
    next: Exclude<Role, "SUPER_ADMIN">
  ) {
    setError(null);
    setBusyIds((prev) => new Set(prev).add(user.id));
    try {
      const updated = await api.users.setRole(user.id, user.version, next);
      setUsers((prev) => prev.map((u) => (u.id === user.id ? updated : u)));
      toast.success(`${user.email} is now ${humanRole(updated.role)}`);
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("Something went wrong");
    } finally {
      setBusyIds((prev) => {
        const next = new Set(prev);
        next.delete(user.id);
        return next;
      });
    }
  }

  return (
    <div className="flex flex-col gap-3">
      {error ? (
        <p
          role="alert"
          className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive"
        >
          {error}
        </p>
      ) : null}

      <table className="w-full table-auto text-left text-sm">
        <thead className="text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="py-2">Email</th>
            <th className="py-2">Role</th>
            <th className="py-2">Action</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => {
            const isLastSuperAdmin =
              u.role === "SUPER_ADMIN" && superAdminCount === 1;
            return (
              <tr key={u.id} className="border-t border-border" data-testid={`user-row-${u.id}`}>
                <td className="py-3 align-middle">
                  <div className="font-medium">{u.email}</div>
                  {u.display_name ? (
                    <div className="text-xs text-muted-foreground">
                      {u.display_name}
                    </div>
                  ) : null}
                </td>
                <td className="py-3 align-middle">
                  <RoleBadge role={u.role} />
                </td>
                <td className="py-3 align-middle">
                  {u.role === "SUPER_ADMIN" ? (
                    <span
                      className="text-xs text-muted-foreground"
                      data-testid={`super-admin-locked-${u.id}`}
                    >
                      {isLastSuperAdmin
                        ? "Last Super Admin — cannot be demoted"
                        : "Super Admin (managed via env allowlist)"}
                    </span>
                  ) : (
                    <RoleSelect
                      value={u.role as Exclude<Role, "SUPER_ADMIN">}
                      onChange={(next) => setRole(u, next)}
                      disabled={busyIds.has(u.id)}
                      ariaLabel={`Set role for ${u.email}`}
                    />
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
