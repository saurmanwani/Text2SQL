import { ThumbsDown, ThumbsUp } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { DataTable } from "@/components/DataTable";
import { FollowupChips } from "@/components/FollowupChips";
import { SqlBlock } from "@/components/SqlBlock";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type QueryResult } from "@/lib/api";

export function ResultsPanel({
  result,
  onFollowup,
  onEnableSummary,
}: {
  result: QueryResult;
  onFollowup: (question: string) => void;
  onEnableSummary?: () => void;
}) {
  const [tab, setTab] = useState<"summary" | "sql" | "table">("summary");
  const [feedback, setFeedback] = useState("");
  const [correcting, setCorrecting] = useState(false);
  const [correctedSql, setCorrectedSql] = useState(result.sql ?? "");
  const [issue, setIssue] = useState("wrong_filter");
  const [correctedResult, setCorrectedResult] = useState<{
    columns: string[];
    rows: unknown[][];
  } | null>(null);
  const tabs = ["summary", "sql", "table"] as const;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{result.question}</CardTitle>
        <div className="flex gap-4 border-b pt-3">
          {tabs.map((item) => (
            <button
              key={item}
              onClick={() => setTab(item)}
              className={`border-b-2 px-1 pb-2 text-sm capitalize ${
                tab === item ? "border-primary" : "border-transparent text-muted-foreground"
              }`}
            >
              {item}
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        {result.unanswerable ? (
          <p className="text-sm text-amber-700">{result.unanswerable_reason}</p>
        ) : tab === "summary" ? (
          result.summary ? (
            <p className="whitespace-pre-line text-sm leading-6">{result.summary}</p>
          ) : (
            <p className="text-sm text-muted-foreground">
              Summary off — your rows stay on this machine.{" "}
              {onEnableSummary ? (
                <button onClick={onEnableSummary} className="underline">Enable cloud summaries</button>
              ) : (
                <Link to="/admin/ai" className="underline">View AI settings</Link>
              )}
            </p>
          )
        ) : tab === "sql" ? (
          <SqlBlock sql={result.sql ?? ""} />
        ) : (
          <DataTable columns={result.columns} rows={result.rows} />
        )}
        <FollowupChips questions={result.followups} onSelect={onFollowup} />
        <div className="space-y-3 border-t pt-3">
          <div className="flex items-center gap-2">
            <button
              title="Save as verified"
              onClick={async () => {
                await api.feedback({ audit_event_id: result.audit_event_id, verdict: "up" });
                setFeedback("Saved as verified example");
              }}
              className="rounded border p-2"
            >
              <ThumbsUp className="size-4" />
            </button>
            <button
              title="Correct this query"
              onClick={() => setCorrecting(true)}
              className="rounded border p-2"
            >
              <ThumbsDown className="size-4" />
            </button>
            {feedback && <span className="text-xs text-emerald-600">{feedback}</span>}
            {result.grounded_on_count > 0 && (
              <span className="rounded-full bg-muted px-2 py-1 text-xs">
                Grounded on {result.grounded_on_count} verified queries
              </span>
            )}
          </div>
          {correcting && (
            <div className="space-y-2 rounded-md border p-3">
              <select value={issue} onChange={(event) => setIssue(event.target.value)} className="rounded border px-2 py-1 text-sm">
                <option value="wrong_table">Wrong table</option><option value="wrong_filter">Wrong filter</option><option value="wrong_aggregation">Wrong aggregation</option><option value="wrong_numbers">Wrong numbers</option><option value="other">Other</option>
              </select>
              <textarea value={correctedSql} onChange={(event) => setCorrectedSql(event.target.value)} className="min-h-28 w-full rounded border p-2 font-mono text-sm" />
              <button
                onClick={async () => {
                  const response = await api.feedback({ audit_event_id: result.audit_event_id, verdict: "down", issue, corrected_sql: correctedSql });
                  setCorrectedResult({ columns: response.columns, rows: response.rows });
                  setFeedback("Correction saved as a verified example");
                  setCorrecting(false);
                }}
                className="rounded bg-primary px-3 py-2 text-sm text-primary-foreground"
              >
                Run & save as correct
              </button>
            </div>
          )}
          {correctedResult && (
            <DataTable columns={correctedResult.columns} rows={correctedResult.rows} />
          )}
        </div>
        <div className="flex flex-wrap gap-2 border-t pt-3 text-xs text-muted-foreground">
          <span>Tables: {result.tables_touched.join(", ") || "none"}</span>
          <span>· {result.duration_ms}ms</span>
          <span>· {result.attempts} attempt(s)</span>
        </div>
      </CardContent>
    </Card>
  );
}
