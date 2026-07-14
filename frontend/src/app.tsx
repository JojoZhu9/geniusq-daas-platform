import { Navigate, Route, Routes } from "react-router-dom";
import { PlatformShell } from "./layout/PlatformShell";
import { QueryWorkspace } from "./pages/QueryWorkspace";

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
      <Route element={<PlatformShell />}>
        <Route index element={<Navigate to="/query" replace />} />
        <Route path="query" element={<QueryWorkspace />} />
        <Route path="knowledge" element={<Placeholder title="知识库管理" />} />
        <Route path="dashboards" element={<Placeholder title="我的仪表盘" />} />
        <Route path="requirements" element={<Placeholder title="需求映射" />} />
      </Route>
      <Route path="*" element={<Navigate to="/query" replace />} />
    </Routes>
  );
}
