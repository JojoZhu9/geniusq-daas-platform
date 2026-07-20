import type { FormEvent } from "react";
import type { Dashboard } from "../../../types";

type DashboardManagementBarProps = {
  dashboards: Dashboard[];
  dashboard: Dashboard | null;
  isCreatingDashboard: boolean;
  newDashboardName: string;
  onSelectDashboard: (dashboard: Dashboard | null) => void;
  onStartCreate: () => void;
  onCreate: (event?: FormEvent) => void;
  onCancelCreate: () => void;
  onNewDashboardNameChange: (value: string) => void;
};

export function DashboardManagementBar({
  dashboards,
  dashboard,
  isCreatingDashboard,
  newDashboardName,
  onSelectDashboard,
  onStartCreate,
  onCreate,
  onCancelCreate,
  onNewDashboardNameChange,
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
      {isCreatingDashboard ? (
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
        <button type="button" className="secondary-button" onClick={onStartCreate}>新建仪表盘</button>
      )}
    </div>
  );
}

