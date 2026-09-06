import { Database } from "lucide-react";
import { Link, Outlet } from "react-router-dom";

import { StatusPill } from "@/components/StatusPill";
import { useAuth } from "@/hooks/useAuth";

export function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
          <Link to="/" className="flex items-center gap-2 font-semibold">
            <Database className="size-5" /> Text2SQL
          </Link>
          <div className="flex items-center gap-4">
            <StatusPill />
            <Link to="/history" className="text-sm">History</Link>
            {user?.role === "admin" && (
              <>
                <Link to="/admin" className="text-sm">Overview</Link>
                <Link to="/admin/connections" className="text-sm">Connections</Link>
                <Link to="/admin/ai" className="text-sm">AI</Link>
                <Link to="/admin/audit" className="text-sm">Audit</Link>
                <Link to="/admin/library" className="text-sm">Library</Link>
              </>
            )}
            <span className="text-xs text-muted-foreground">{user?.role}</span>
            <button onClick={logout} className="text-sm">Log out</button>
          </div>
        </div>
      </header>
      <div className="mx-auto max-w-6xl px-6 py-8">
        <Outlet />
      </div>
    </div>
  );
}
