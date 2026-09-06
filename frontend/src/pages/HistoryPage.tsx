import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function HistoryPage({ admin = false }: { admin?: boolean }) {
  const history = useQuery({
    queryKey: [admin ? "audit" : "history"],
    queryFn: admin ? api.audit : api.history,
  });

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{admin ? "Audit log" : "Query history"}</h1>
        {admin && <button onClick={api.downloadAudit} className="rounded-md border px-3 py-2 text-sm">Export CSV</button>}
      </div>
      <div className="overflow-auto rounded-md border">
        <table className="w-full text-left text-sm">
          <thead className="bg-muted"><tr><th className="p-3">Time</th><th>Question</th><th>Outcome</th><th>Rows</th><th>Duration</th></tr></thead>
          <tbody>
            {history.data?.items.map((event) => (
              <tr key={event.id} className="border-t">
                <td className="whitespace-nowrap p-3">{new Date(event.ts).toLocaleString()}</td>
                <td className="max-w-md p-3">{event.question}</td>
                <td className="p-3">{event.outcome}</td>
                <td className="p-3">{event.row_count}</td>
                <td className="p-3">{event.duration_ms}ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
