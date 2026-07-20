type DashboardFiltersValue = {
  year: string;
  district: string;
  metric: string;
};

type DashboardFiltersProps = {
  filters: DashboardFiltersValue;
  options: {
    years: string[];
    districts: string[];
    metrics: string[];
  };
  onChange: (filters: DashboardFiltersValue) => void;
};

export function DashboardFilters({ filters, options, onChange }: DashboardFiltersProps) {
  return (
    <div className="dashboard-filters panel" aria-label="仪表盘筛选器">
      <label>年份
        <select value={filters.year} onChange={(event) => onChange({ ...filters, year: event.target.value })}>
          <option value="">全部年份</option>
          {options.years.map((year) => <option key={year} value={year}>{year}</option>)}
        </select>
      </label>
      <label>区域
        <select value={filters.district} onChange={(event) => onChange({ ...filters, district: event.target.value })}>
          <option value="">全部区域</option>
          {options.districts.map((district) => <option key={district} value={district}>{district}</option>)}
        </select>
      </label>
      <label>指标
        <select value={filters.metric} onChange={(event) => onChange({ ...filters, metric: event.target.value })}>
          <option value="">全部指标</option>
          {options.metrics.map((metric) => <option key={metric} value={metric}>{metric}</option>)}
        </select>
      </label>
    </div>
  );
}

