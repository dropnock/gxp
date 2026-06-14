import { useState } from "react";
import { useCreateTenant } from "../hooks/useTenants";

interface Props {
  onSuccess: () => void;
  onCancel: () => void;
}

export function TenantCreateForm({ onSuccess, onCancel }: Props) {
  const [slug, setSlug] = useState("");
  const [name, setName] = useState("");
  const mutation = useCreateTenant();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({ slug, name }, { onSuccess });
  };

  return (
    <form onSubmit={handleSubmit} style={{ border: "1px solid #ccc", padding: 16, marginBottom: 16, borderRadius: 4 }}>
      <h2 style={{ marginTop: 0 }}>New Tenant</h2>
      <div style={{ marginBottom: 12 }}>
        <label>
          Slug (e.g. <code>dot</code>)
          <br />
          <input
            value={slug}
            onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ""))}
            required
            minLength={3}
            maxLength={63}
            pattern="[a-z0-9][a-z0-9_]{1,61}[a-z0-9]"
            placeholder="dept_of_transportation"
            style={{ width: "100%", marginTop: 4 }}
          />
        </label>
      </div>
      <div style={{ marginBottom: 12 }}>
        <label>
          Name
          <br />
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            minLength={2}
            placeholder="Department of Transportation"
            style={{ width: "100%", marginTop: 4 }}
          />
        </label>
      </div>
      {mutation.error && <p style={{ color: "red" }}>{String(mutation.error)}</p>}
      <div style={{ display: "flex", gap: 8 }}>
        <button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Provisioning…" : "Create Tenant"}
        </button>
        <button type="button" onClick={onCancel}>Cancel</button>
      </div>
      {mutation.isSuccess && (
        <p style={{ color: "green" }}>Tenant provisioning started. It will be active in a moment.</p>
      )}
    </form>
  );
}
