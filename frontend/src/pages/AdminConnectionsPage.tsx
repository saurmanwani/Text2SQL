import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/lib/api";

export function AdminConnectionsPage() {
  const queryClient = useQueryClient();
  const connections = useQuery({ queryKey: ["connections"], queryFn: api.connections });
  const [form, setForm] = useState({ name: "", dialect: "postgres", url: "" });
  const [snippets, setSnippets] = useState<Record<number, string>>({});
  const create = useMutation({
    mutationFn: api.createConnection,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["connections"] }),
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    create.mutate(form);
  };

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold">Database connections</h1>
      <form onSubmit={submit} className="grid gap-3 rounded-lg border p-5 md:grid-cols-4">
        <input required placeholder="Connection name" className="rounded-md border px-3 py-2" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
        <select className="rounded-md border px-3 py-2" value={form.dialect} onChange={(event) => setForm({ ...form, dialect: event.target.value })}>
          <option value="postgres">PostgreSQL</option><option value="mysql">MySQL</option><option value="sqlite">SQLite</option>
        </select>
        <input required placeholder="Database URL" className="rounded-md border px-3 py-2" value={form.url} onChange={(event) => setForm({ ...form, url: event.target.value })} />
        <button className="rounded-md bg-primary px-4 py-2 text-primary-foreground">{create.isPending ? "Testing…" : "Test & save"}</button>
        {create.error && <p className="text-sm text-red-600 md:col-span-4">{create.error.message}</p>}
      </form>
      <div className="space-y-3">
        {connections.data?.map((connection) => (
          <div key={connection.id} className="rounded-lg border p-4">
            <div className="flex items-center justify-between">
              <div><p className="font-medium">{connection.name}</p><p className="text-xs text-muted-foreground">{connection.dialect}</p></div>
              <div className="flex items-center gap-4">
                <span className="text-sm">{connection.read_only_status === "verified" ? "🟢 Read-only verified" : connection.read_only_status === "writable" ? "🟠 Writable" : "⚪ Not applicable / unknown"}</span>
                {connection.read_only_status === "writable" && <button className="text-sm underline" onClick={async () => setSnippets({ ...snippets, [connection.id]: (await api.readonlySnippet(connection.id)).sql })}>Show read-only SQL</button>}
                <Link to={`/admin/schema/${connection.id}`} className="text-sm underline">Schema access</Link>
              </div>
            </div>
            {snippets[connection.id] && <pre className="mt-3 overflow-auto rounded bg-zinc-950 p-3 text-xs text-white">{snippets[connection.id]}</pre>}
          </div>
        ))}
      </div>
    </div>
  );
}
