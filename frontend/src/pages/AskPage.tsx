import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { AskBar } from "@/components/AskBar";
import { ResultsPanel } from "@/components/ResultsPanel";
import { useAuth } from "@/hooks/useAuth";
import { useAskQuery } from "@/hooks/useQuery";
import { api } from "@/lib/api";

export function AskPage() {
  const connections = useQuery({ queryKey: ["connections"], queryFn: api.connections });
  const { user } = useAuth();
  const [connectionId, setConnectionId] = useState<number | null>(null);
  const query = useAskQuery();

  useEffect(() => {
    if (!connectionId && connections.data?.length) setConnectionId(connections.data[0].id);
  }, [connectionId, connections.data]);

  const samples = useQuery({
    queryKey: ["samples", connectionId],
    queryFn: () => api.samples(connectionId!),
    enabled: Boolean(connectionId),
  });

  const ask = (question: string) => {
    if (connectionId) query.mutate({ question, connectionId });
  };

  const enableSummary = async () => {
    if (!query.data || !connectionId) return;
    const confirmed = window.confirm(
      `Cloud AI will receive ${query.data.rows.length} rows and these column names: ${query.data.columns.join(", ")}. Continue?`,
    );
    if (!confirmed) return;
    const settings = await api.aiSettings();
    await api.updateAISettings({
      ...settings,
      llm_api_key: "",
      cloud_summaries_enabled: true,
    });
    ask(query.data.question);
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Ask your data</h1>
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
      {query.data && (
        <ResultsPanel
          result={query.data}
          onFollowup={ask}
          onEnableSummary={
            user?.role === "admin" && query.data.summary_reason === "cloud_summaries_disabled"
              ? enableSummary
              : undefined
          }
        />
      )}
    </div>
  );
}
