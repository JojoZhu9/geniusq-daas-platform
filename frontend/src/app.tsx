import { Navigate, Route, Routes } from "react-router-dom";
import { PlatformShell } from "./layout/PlatformShell";
import { QueryWorkspace } from "./pages/QueryWorkspace";
import { KnowledgeWorkspace } from "./pages/KnowledgeWorkspace";
import { DashboardWorkspace } from "./pages/DashboardWorkspace";
import { RequirementMatrix } from "./pages/RequirementMatrix";
import { SharedDashboardPage } from "./pages/SharedDashboardPage";

function Placeholder({ title }: { title: string }) {
  return (
    <section className="page-section">
      <div className="page-heading"><div><small>极智 DAAS</small><h1>{title}</h1></div></div>
      <div className="panel empty-state">该工作区将在后续任务中接入真实本地 API。</div>
    </section>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="share/:shareId" element={<SharedDashboardPage />} />
      <Route element={<PlatformShell />}>
        <Route index element={<Navigate to="/query" replace />} />
        <Route path="query" element={<QueryWorkspace />} />
        <Route path="knowledge" element={<KnowledgeWorkspace />} />
        <Route path="dashboards" element={<DashboardWorkspace />} />
        <Route path="requirements" element={<RequirementMatrix />} />
      </Route>
      <Route path="*" element={<Navigate to="/query" replace />} />
    </Routes>
  );
}
