import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/lib/api";

export function AdminLibraryPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [edits, setEdits] = useState<Record<number, string>>({});
  const examples = useQuery({
    queryKey: ["library", search],
    queryFn: () => api.library(search),
  });
  const update = useMutation({
    mutationFn: ({ id, sql }: { id: number; sql: string }) => api.updateExample(id, sql),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["library"] }),
  });
  const remove = useMutation({
    mutationFn: api.deleteExample,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["library"] }),
  });

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-semibold">Verified query library</h1>
      <input
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="Search questions"
        className="w-full max-w-md rounded-md border px-3 py-2"
      />
      <div className="space-y-4">
        {examples.data?.map((example) => (
          <div key={example.id} className="space-y-3 rounded-lg border p-4">
            <div className="flex justify-between gap-4">
              <div>
                <p className="font-medium">{example.question}</p>
                <p className="text-xs text-muted-foreground">{example.source}</p>
              </div>
              <button onClick={() => remove.mutate(example.id)} className="text-sm text-red-600">
                Delete
              </button>
            </div>
            <textarea
              value={edits[example.id] ?? example.sql}
              onChange={(event) => setEdits({ ...edits, [example.id]: event.target.value })}
              className="min-h-24 w-full rounded-md border p-3 font-mono text-sm"
            />
            <button
              onClick={() => update.mutate({ id: example.id, sql: edits[example.id] ?? example.sql })}
              className="rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground"
            >
              Validate & save
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
