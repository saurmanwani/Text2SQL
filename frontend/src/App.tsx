import { useQuery } from "@tanstack/react-query";
import { Activity, Database } from "lucide-react";
import { Route, Routes } from "react-router-dom";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getHealth } from "@/lib/api";

function HomePage() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => getHealth(signal),
    retry: 2,
    refetchInterval: 30_000,
  });

  const statusLabel = health.isPending
    ? "checking…"
    : health.isError
      ? "unreachable"
      : health.data.status;
  const isHealthy = health.data?.status === "healthy";

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-6">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <div className="mb-4 flex size-11 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Database className="size-5" aria-hidden="true" />
          </div>
          <CardTitle>Text2SQL</CardTitle>
          <p className="text-sm text-muted-foreground">
            Ask questions of your data in plain English.
          </p>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between rounded-md border bg-muted/50 px-4 py-3">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Activity
                className={isHealthy ? "size-4 text-emerald-500" : "size-4 text-muted-foreground"}
                aria-hidden="true"
              />
              Backend: {statusLabel}
            </div>
            {health.data && (
              <span className="text-xs text-muted-foreground">v{health.data.version}</span>
            )}
          </div>
          {health.isError && (
            <p className="mt-3 text-sm text-red-600">
              Start the backend on port 8090, then refresh this page.
            </p>
          )}
        </CardContent>
      </Card>
    </main>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
    </Routes>
  );
}
