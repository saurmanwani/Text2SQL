import { useQuery } from "@tanstack/react-query";
import { Cloud, Lock } from "lucide-react";

import { api } from "@/lib/api";

export function StatusPill() {
  const status = useQuery({ queryKey: ["llm-status"], queryFn: api.llmStatus });
  if (!status.data) return <span className="text-xs text-muted-foreground">AI: checking…</span>;
  const local = status.data.provider === "ollama";
  const Icon = local ? Lock : Cloud;

  return (
    <span className="flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs">
      <Icon className="size-3" />
      {local ? "Local AI" : `Cloud · ${status.data.provider}`} · {status.data.model}
      <span className={status.data.reachable ? "text-emerald-500" : "text-amber-500"}>●</span>
    </span>
  );
}
