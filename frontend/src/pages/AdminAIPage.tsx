import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";

export function AdminAIPage() {
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey: ["ai-settings"], queryFn: api.aiSettings });
  const [form, setForm] = useState({
    llm_provider: "ollama",
    llm_model: "qwen2.5-coder:7b",
    llm_base_url: "",
    llm_api_key: "",
    cloud_summaries_enabled: false,
    pii_redaction_enabled: true,
  });
  useEffect(() => {
    if (settings.data) setForm((value) => ({ ...value, ...settings.data, llm_api_key: "" }));
  }, [settings.data]);
  const save = useMutation({
    mutationFn: api.updateAISettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-settings"] });
      queryClient.invalidateQueries({ queryKey: ["llm-status"] });
    },
  });
  const local = form.llm_provider === "ollama";

  return (
    <div className="max-w-3xl space-y-6">
      <h1 className="text-2xl font-semibold">AI and privacy</h1>
      <div className="grid gap-4 sm:grid-cols-2">
        {["ollama", "groq"].map((provider) => (
          <button key={provider} onClick={() => setForm({ ...form, llm_provider: provider })} className={`rounded-lg border p-5 text-left ${form.llm_provider === provider ? "ring-2 ring-primary" : ""}`}>
            <p className="font-medium">{provider === "ollama" ? "🔒 Local (Ollama)" : "☁️ Cloud (bring your own key)"}</p>
            <p className="mt-1 text-sm text-muted-foreground">{provider === "ollama" ? "Data stays on this machine." : "Schema is sent to your selected provider."}</p>
          </button>
        ))}
      </div>
      <div className="space-y-4 rounded-lg border p-5">
        {!local && <select value={form.llm_provider} onChange={(event) => setForm({ ...form, llm_provider: event.target.value })} className="w-full rounded-md border px-3 py-2"><option value="groq">Groq</option><option value="gemini">Gemini</option><option value="openai">OpenAI</option></select>}
        <input value={form.llm_model} onChange={(event) => setForm({ ...form, llm_model: event.target.value })} placeholder="Model" className="w-full rounded-md border px-3 py-2" />
        {!local && <input type="password" value={form.llm_api_key} onChange={(event) => setForm({ ...form, llm_api_key: event.target.value })} placeholder={settings.data?.has_api_key ? "API key saved — enter to replace" : "API key"} className="w-full rounded-md border px-3 py-2" />}
        <label className="flex gap-3 text-sm"><input type="checkbox" disabled={local} checked={!local && form.cloud_summaries_enabled} onChange={(event) => setForm({ ...form, cloud_summaries_enabled: event.target.checked })} /> Allow cloud AI to see result rows for summaries</label>
        <label className="flex gap-3 text-sm"><input type="checkbox" checked={form.pii_redaction_enabled} onChange={(event) => setForm({ ...form, pii_redaction_enabled: event.target.checked })} /> Redact emails and phones before sending</label>
        <button onClick={() => save.mutate(form)} className="rounded-md bg-primary px-4 py-2 text-primary-foreground">Save settings</button>
      </div>
    </div>
  );
}
