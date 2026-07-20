from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DomainConfig:
    allowed_tables: tuple[str, ...]
    districts: tuple[str, ...]
    relative_year_offsets: tuple[tuple[tuple[str, ...], int], ...]
    chart_field_priority: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...]
    tool_labels: dict[str, str]
    field_units: dict[str, str]

