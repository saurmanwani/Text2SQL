import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function AdminDashboardPage() {
  const metrics = useQuery({ queryKey: ["metrics"], queryFn: api.metrics });
  const weeks = metrics.data?.weeks ?? [];
  const points = weeks
    .map((week, index) => {
      const x = weeks.length <= 1 ? 150 : (index / (weeks.length - 1)) * 300;
      const y = 100 - (week.thumbs_up_rate ?? 0) * 100;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Admin overview</h1>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-lg border p-5"><p className="text-sm text-muted-foreground">Total queries</p><p className="text-3xl font-semibold">{metrics.data?.total_queries ?? 0}</p></div>
        <div className="rounded-lg border p-5"><p className="text-sm text-muted-foreground">Blocked queries</p><p className="text-3xl font-semibold">{metrics.data?.blocked_count ?? 0}</p></div>
      </div>
      <div className="rounded-lg border p-5">
        <h2 className="font-medium">Weekly 👍 rate</h2>
        {points ? (
          <svg viewBox="0 0 300 110" className="mt-4 h-48 w-full" role="img" aria-label="Weekly positive feedback rate">
            <line x1="0" y1="100" x2="300" y2="100" stroke="currentColor" opacity=".2" />
            <polyline points={points} fill="none" stroke="currentColor" strokeWidth="3" />
          </svg>
        ) : (
          <p className="mt-4 text-sm text-muted-foreground">Feedback trends appear after queries receive ratings.</p>
        )}
      </div>
    </div>
  );
}
