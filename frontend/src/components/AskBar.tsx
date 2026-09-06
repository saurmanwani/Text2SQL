import { Send } from "lucide-react";
import { type FormEvent, useState } from "react";

import type { Connection } from "@/lib/api";

interface AskBarProps {
  connections: Connection[];
  connectionId: number | null;
  onConnectionChange: (id: number) => void;
  samples: string[];
  loading: boolean;
  onAsk: (question: string) => void;
}

export function AskBar(props: AskBarProps) {
  const [question, setQuestion] = useState("");

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (question.trim() && props.connectionId) props.onAsk(question.trim());
  };

  return (
    <div className="space-y-4">
      <form onSubmit={submit} className="rounded-xl border bg-card p-3 shadow-sm">
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask a question about your data…"
          className="min-h-24 w-full resize-none bg-transparent p-2 outline-none"
        />
        <div className="flex items-center justify-between gap-3">
          <select
            value={props.connectionId ?? ""}
            onChange={(event) => props.onConnectionChange(Number(event.target.value))}
            className="rounded-md border bg-background px-3 py-2 text-sm"
          >
            {props.connections.map((connection) => (
              <option key={connection.id} value={connection.id}>
                {connection.name}
              </option>
            ))}
          </select>
          <button
            disabled={!question.trim() || !props.connectionId || props.loading}
            className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
          >
            <Send className="size-4" />
            {props.loading ? "Running…" : "Ask"}
          </button>
        </div>
      </form>
      <div className="flex flex-wrap gap-2">
        {props.samples.map((sample) => (
          <button
            key={sample}
            onClick={() => {
              setQuestion(sample);
              props.onAsk(sample);
            }}
            className="rounded-full border px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted"
          >
            {sample}
          </button>
        ))}
      </div>
    </div>
  );
}
