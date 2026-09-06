import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { AskBar } from "@/components/AskBar";
import { ResultsPanel } from "@/components/ResultsPanel";
import { useAuth } from "@/hooks/useAuth";
import { useAskQuery } from "@/hooks/useQuery";
import { api, type QueryResult } from "@/lib/api";

export function AskPage() {
  const connections = useQuery({ queryKey: ["connections"], queryFn: api.connections });
  const { user } = useAuth();
  const [connectionId, setConnectionId] = useState<number | null>(null);
  const [results, setResults] = useState<QueryResult[]>([]);
  const query = useAskQuery();

  useEffect(() => {
    if (!connectionId && connections.data?.length) setConnectionId(connections.data[0].id);
  }, [connectionId, connections.data]);

  useEffect(() => {
    if (query.data) setResults((items) => [...items, query.data]);
  }, [query.data]);

  const samples = useQuery({
    queryKey: ["samples", connectionId],
    queryFn: () => api.samples(connectionId!),
    enabled: Boolean(connectionId),
  });

  const ask = (question: string) => {
    if (connectionId) {
      const history = results
        .filter((result): result is QueryResult & { sql: string } => Boolean(result.sql))
        .slice(-3)
        .map((result) => ({ question: result.question, sql: result.sql }));
      query.mutate({ question, connectionId, history });
    }
  };

  const enableSummary = async (result: QueryResult) => {
    if (!connectionId) return;
    const confirmed = window.confirm(
      `Cloud AI will receive ${result.rows.length} rows and these column names: ${result.columns.join(", ")}. Continue?`,
    );
    if (!confirmed) return;
    const settings = await api.aiSettings();
    await api.updateAISettings({
      ...settings,
      llm_api_key: "",
      cloud_summaries_enabled: true,
    });
    ask(result.question);
  };

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-semibold tracking-tight">Ask your data</h1>
          <button onClick={() => setResults([])} className="rounded-md border px-3 py-2 text-sm">New chat</button>
        </div>
        <p className="mt-2 text-muted-foreground">Generate validated, read-only SQL.</p>
      </div>
      <AskBar
        connections={connections.data ?? []}
        connectionId={connectionId}
        onConnectionChange={setConnectionId}
        samples={samples.data?.questions ?? []}
        loading={query.isPending}
        onAsk={ask}
      />
      {query.error && <p className="text-sm text-red-600">{query.error.message}</p>}
      {results.map((result) => (
        <ResultsPanel
          key={result.audit_event_id}
          result={result}
          onFollowup={ask}
          onEnableSummary={
            user?.role === "admin" && result.summary_reason === "cloud_summaries_disabled"
              ? () => enableSummary(result)
              : undefined
          }
        />
      ))}
    </div>
  );
}
