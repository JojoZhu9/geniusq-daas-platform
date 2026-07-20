import type { FormEvent } from "react";
import type { Dashboard } from "../../../types";

type DashboardManagementBarProps = {
  dashboards: Dashboard[];
  dashboard: Dashboard | null;
  isCreatingDashboard: boolean;
  isRenamingDashboard: boolean;
  newDashboardName: string;
  renameDashboardName: string;
  onSelectDashboard: (dashboard: Dashboard | null) => void;
  onStartCreate: () => void;
  onCreate: (event?: FormEvent) => void;
  onCancelCreate: () => void;
  onNewDashboardNameChange: (value: string) => void;
  onStartRename: () => void;
  onRename: (event?: FormEvent) => void;
  onCancelRename: () => void;
  onRenameDashboardNameChange: (value: string) => void;
};

export function DashboardManagementBar({
  dashboards,
  dashboard,
  isCreatingDashboard,
  isRenamingDashboard,
  newDashboardName,
  renameDashboardName,
  onSelectDashboard,
  onStartCreate,
  onCreate,
  onCancelCreate,
  onNewDashboardNameChange,
  onStartRename,
  onRename,
  onCancelRename,
  onRenameDashboardNameChange,
}: DashboardManagementBarProps) {
  return (
    <div className="dashboard-management panel">
      {dashboards.length > 0 && (
        <label>当前仪表盘
          <select
            aria-label="选择仪表盘"
            className="dashboard-selector"
            value={dashboard?.id ?? ""}
            onChange={(event) => onSelectDashboard(dashboards.find((item) => item.id === event.target.value) ?? null)}
          >
            {dashboards.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </label>
      )}
      {isRenamingDashboard && dashboard ? (
        <form className="dashboard-create-form" onSubmit={onRename}>
          <label>
            新仪表盘名称
            <input
              aria-label="新仪表盘名称"
              value={renameDashboardName}
              onChange={(event) => onRenameDashboardNameChange(event.target.value)}
              autoFocus
            />
          </label>
          <button type="submit" className="primary-button" disabled={!renameDashboardName.trim()}>保存名称</button>
          <button type="button" className="secondary-button" onClick={onCancelRename}>取消</button>
        </form>
      ) : isCreatingDashboard ? (
        <form className="dashboard-create-form" onSubmit={onCreate}>
          <label>
            仪表盘名称
            <input
              aria-label="仪表盘名称"
              value={newDashboardName}
              onChange={(event) => onNewDashboardNameChange(event.target.value)}
              autoFocus
            />
          </label>
          <button type="submit" className="primary-button">创建</button>
          <button type="button" className="secondary-button" onClick={onCancelCreate}>取消</button>
        </form>
      ) : (
        <>
          {dashboard && <button type="button" className="secondary-button" onClick={onStartRename}>重命名仪表盘</button>}
          <button type="button" className="secondary-button" onClick={onStartCreate}>新建仪表盘</button>
        </>
      )}
    </div>
  );
}
