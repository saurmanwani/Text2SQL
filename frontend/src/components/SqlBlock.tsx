import { Check, Copy } from "lucide-react";
import { useState } from "react";

export function SqlBlock({ sql }: { sql: string }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    await navigator.clipboard.writeText(sql);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1_500);
  };

  return (
    <div className="relative overflow-auto rounded-md bg-zinc-950 p-4 text-zinc-100">
      <button onClick={copy} className="absolute right-3 top-3 text-zinc-400">
        {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
      </button>
      <pre className="pr-8 text-sm">
        <code>{sql}</code>
      </pre>
    </div>
  );
}
