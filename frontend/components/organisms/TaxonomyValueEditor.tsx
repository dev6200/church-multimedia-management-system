// TaxonomyValueEditor — Client. List existing values + add/rename/delete inline.
// Surfaces the confirm-detach dialog (FR-019) when delete needs detach.
"use client";

import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import type { TaxonomyKind, TaxonomyValue } from "@/types/api";
import { ApiError } from "@/types/api";
import { createClientApiClient } from "@/services/api/client";
import { ConfirmDetachDialog } from "@/components/molecules/ConfirmDetachDialog";

export interface TaxonomyValueEditorProps {
  kind: TaxonomyKind;
  initialValues: TaxonomyValue[];
}

export function TaxonomyValueEditor({
  kind,
  initialValues,
}: TaxonomyValueEditorProps) {
  const { getToken } = useAuth();
  const router = useRouter();
  const api = useMemo(
    () => createClientApiClient(async () => (await getToken()) ?? null),
    [getToken]
  );
  const [values, setValues] = useState<TaxonomyValue[]>(initialValues);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<{
    value: TaxonomyValue;
    usageCount: number;
  } | null>(null);

  async function handleAdd() {
    setError(null);
    try {
      const created = await api.taxonomies.create(kind, newName.trim());
      setValues((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)));
      setNewName("");
      toast.success(`${created.name} added`);
    } catch (err) {
      setError(formatErr(err));
    }
  }

  async function handleRename(v: TaxonomyValue, name: string) {
    setError(null);
    try {
      const renamed = await api.taxonomies.rename(kind, v.id, v.version, name);
      setValues((prev) =>
        prev
          .map((x) => (x.id === v.id ? renamed : x))
          .sort((a, b) => a.name.localeCompare(b.name))
      );
      toast.success(`Renamed to ${renamed.name}`);
    } catch (err) {
      setError(formatErr(err));
    }
  }

  async function startDelete(v: TaxonomyValue) {
    setError(null);
    try {
      const usage = await api.taxonomies.usage(kind, v.id);
      setPendingDelete({ value: v, usageCount: usage.usage_count });
    } catch (err) {
      setError(formatErr(err));
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    setError(null);
    const deletedName = pendingDelete.value.name;
    try {
      await api.taxonomies.delete(
        kind,
        pendingDelete.value.id,
        pendingDelete.value.version,
        pendingDelete.usageCount > 0
      );
      setValues((prev) => prev.filter((x) => x.id !== pendingDelete.value.id));
      setPendingDelete(null);
      toast.success(`${deletedName} deleted`);
      router.refresh();
    } catch (err) {
      setError(formatErr(err));
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {error ? (
        <p
          role="alert"
          className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive"
        >
          {error}
        </p>
      ) : null}

      <div className="flex flex-col gap-2">
        {values.map((v) => (
          <ValueRow
            key={v.id}
            value={v}
            onRename={(name) => handleRename(v, name)}
            onDelete={() => startDelete(v)}
          />
        ))}
        {values.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No values yet — add one below.
          </p>
        ) : null}
      </div>

      <div className="flex items-center gap-2">
        <input
          type="text"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="Add a new value"
          className="h-11 flex-1 rounded-md border border-input bg-background px-3 text-base"
        />
        <button
          type="button"
          onClick={handleAdd}
          disabled={!newName.trim()}
          className="inline-flex min-h-11 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
        >
          Add
        </button>
      </div>

      <ConfirmDetachDialog
        open={pendingDelete !== null}
        entityLabel={pendingDelete ? `"${pendingDelete.value.name}"` : ""}
        usageCount={pendingDelete?.usageCount ?? 0}
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
}

interface ValueRowProps {
  value: TaxonomyValue;
  onRename: (name: string) => void;
  onDelete: () => void;
}

function ValueRow({ value, onRename, onDelete }: ValueRowProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value.name);
  return (
    <div className="flex items-center gap-2 rounded-md border border-border p-2">
      {editing ? (
        <>
          <input
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="h-9 flex-1 rounded border border-input bg-background px-2 text-sm"
          />
          <button
            type="button"
            onClick={() => {
              onRename(draft.trim());
              setEditing(false);
            }}
            className="text-sm text-primary"
          >
            Save
          </button>
          <button
            type="button"
            onClick={() => {
              setDraft(value.name);
              setEditing(false);
            }}
            className="text-sm text-muted-foreground"
          >
            Cancel
          </button>
        </>
      ) : (
        <>
          <span className="flex-1 text-sm">{value.name}</span>
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="text-sm text-primary"
            aria-label={`Rename ${value.name}`}
          >
            Rename
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="text-sm text-destructive"
            aria-label={`Delete ${value.name}`}
          >
            Delete
          </button>
        </>
      )}
    </div>
  );
}

function formatErr(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return "Something went wrong";
}
