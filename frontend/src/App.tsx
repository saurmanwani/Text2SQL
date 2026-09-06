import { Navigate, Outlet, Route, Routes } from "react-router-dom";

import { Layout } from "@/components/Layout";
import { useAuth } from "@/hooks/useAuth";
import { AdminAIPage } from "@/pages/AdminAIPage";
import { AdminConnectionsPage } from "@/pages/AdminConnectionsPage";
import { AdminDashboardPage } from "@/pages/AdminDashboardPage";
import { AdminLibraryPage } from "@/pages/AdminLibraryPage";
import { AdminSchemaPage } from "@/pages/AdminSchemaPage";
import { AskPage } from "@/pages/AskPage";
import { AuthPage } from "@/pages/AuthPage";
import { HistoryPage } from "@/pages/HistoryPage";

function ProtectedRoute({ admin = false }: { admin?: boolean }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-8 text-sm">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (admin && user.role !== "admin") return <Navigate to="/" replace />;
  return <Outlet />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<AuthPage mode="login" />} />
      <Route path="/register" element={<AuthPage mode="register" />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<AskPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route element={<ProtectedRoute admin />}>
            <Route path="/admin" element={<AdminDashboardPage />} />
            <Route path="/admin/connections" element={<AdminConnectionsPage />} />
            <Route path="/admin/ai" element={<AdminAIPage />} />
            <Route path="/admin/schema/:connectionId" element={<AdminSchemaPage />} />
            <Route path="/admin/audit" element={<HistoryPage admin />} />
            <Route path="/admin/library" element={<AdminLibraryPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
