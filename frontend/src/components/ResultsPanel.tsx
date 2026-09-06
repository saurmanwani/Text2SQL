import { useState } from "react";
import { Link } from "react-router-dom";

import { DataTable } from "@/components/DataTable";
import { FollowupChips } from "@/components/FollowupChips";
import { SqlBlock } from "@/components/SqlBlock";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { QueryResult } from "@/lib/api";

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
        <div className="flex flex-wrap gap-2 border-t pt-3 text-xs text-muted-foreground">
          <span>Tables: {result.tables_touched.join(", ") || "none"}</span>
          <span>· {result.duration_ms}ms</span>
          <span>· {result.attempts} attempt(s)</span>
        </div>
      </CardContent>
    </Card>
  );
}
