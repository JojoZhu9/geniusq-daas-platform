import { Navigate, Route, Routes } from "react-router-dom";
import { PlatformShell } from "./layout/PlatformShell";
import { QueryWorkspace } from "./pages/QueryWorkspace";
import { KnowledgeWorkspace } from "./pages/KnowledgeWorkspace";
import { DashboardWorkspace } from "./pages/DashboardWorkspace";
import { DataSourceWorkspace } from "./pages/DataSourceWorkspace";
import { SettingsWorkspace } from "./pages/SettingsWorkspace";
import { SharedDashboardPage } from "./pages/SharedDashboardPage";

export function App() {
  return (
    <Routes>
      <Route path="share/:shareId" element={<SharedDashboardPage />} />
      <Route element={<PlatformShell />}>
        <Route index element={<Navigate to="/query" replace />} />
        <Route path="query" element={<QueryWorkspace />} />
        <Route path="datasource" element={<DataSourceWorkspace />} />
        <Route path="knowledge" element={<KnowledgeWorkspace />} />
        <Route path="dashboards" element={<DashboardWorkspace />} />
        <Route path="settings" element={<SettingsWorkspace />} />
      </Route>
      <Route path="*" element={<Navigate to="/query" replace />} />
    </Routes>
  );
}
