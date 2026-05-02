// OptionalFieldEditor — mirror of TaxonomyValueEditor for optional-field
// definitions. FR-018 + FR-019.
"use client";

import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import type { OptionalFieldDefinition } from "@/types/api";
import { ApiError } from "@/types/api";
import { createClientApiClient } from "@/services/api/client";
import { ConfirmDetachDialog } from "@/components/molecules/ConfirmDetachDialog";

export interface OptionalFieldEditorProps {
  initialDefinitions: OptionalFieldDefinition[];
}

export function OptionalFieldEditor({
  initialDefinitions,
}: OptionalFieldEditorProps) {
  const { getToken } = useAuth();
  const router = useRouter();
  const api = useMemo(
    () => createClientApiClient(async () => (await getToken()) ?? null),
    [getToken]
  );
  const [defs, setDefs] = useState<OptionalFieldDefinition[]>(initialDefinitions);
  const [newLabel, setNewLabel] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<{
    def: OptionalFieldDefinition;
    usageCount: number;
  } | null>(null);

  async function handleAdd() {
    setError(null);
    try {
      const created = await api.optionalFields.create(newLabel.trim());
      setDefs((prev) =>
        [...prev, created].sort((a, b) => a.label.localeCompare(b.label))
      );
      setNewLabel("");
      toast.success(`${created.label} added`);
    } catch (err) {
      setError(formatErr(err));
    }
  }

  async function handleRename(d: OptionalFieldDefinition, label: string) {
    setError(null);
    try {
      const renamed = await api.optionalFields.rename(d.id, d.version, label);
      setDefs((prev) =>
        prev
          .map((x) => (x.id === d.id ? renamed : x))
          .sort((a, b) => a.label.localeCompare(b.label))
      );
      toast.success(`Renamed to ${renamed.label}`);
    } catch (err) {
      setError(formatErr(err));
    }
  }

  async function startDelete(d: OptionalFieldDefinition) {
    setError(null);
    try {
      const usage = await api.optionalFields.usage(d.id);
      setPendingDelete({ def: d, usageCount: usage.usage_count });
    } catch (err) {
      setError(formatErr(err));
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    setError(null);
    const deletedLabel = pendingDelete.def.label;
    try {
      await api.optionalFields.delete(
        pendingDelete.def.id,
        pendingDelete.def.version,
        pendingDelete.usageCount > 0
      );
      setDefs((prev) => prev.filter((x) => x.id !== pendingDelete.def.id));
      setPendingDelete(null);
      toast.success(`${deletedLabel} deleted`);
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

      {defs.map((d) => (
        <DefRow
          key={d.id}
          def={d}
          onRename={(label) => handleRename(d, label)}
          onDelete={() => startDelete(d)}
        />
      ))}

      <div className="flex items-center gap-2">
        <input
          type="text"
          value={newLabel}
          onChange={(e) => setNewLabel(e.target.value)}
          placeholder="New field label (e.g. Spotify link)"
          className="h-11 flex-1 rounded-md border border-input bg-background px-3 text-base"
        />
        <button
          type="button"
          onClick={handleAdd}
          disabled={!newLabel.trim()}
          className="inline-flex min-h-11 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
        >
          Add
        </button>
      </div>

      <ConfirmDetachDialog
        open={pendingDelete !== null}
        entityLabel={pendingDelete ? `"${pendingDelete.def.label}"` : ""}
        usageCount={pendingDelete?.usageCount ?? 0}
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
}

interface DefRowProps {
  def: OptionalFieldDefinition;
  onRename: (label: string) => void;
  onDelete: () => void;
}

function DefRow({ def, onRename, onDelete }: DefRowProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(def.label);
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
              setDraft(def.label);
              setEditing(false);
            }}
            className="text-sm text-muted-foreground"
          >
            Cancel
          </button>
        </>
      ) : (
        <>
          <span className="flex-1 text-sm">{def.label}</span>
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="text-sm text-primary"
            aria-label={`Rename ${def.label}`}
          >
            Rename
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="text-sm text-destructive"
            aria-label={`Delete ${def.label}`}
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
