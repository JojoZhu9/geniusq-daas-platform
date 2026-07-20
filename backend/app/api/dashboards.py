from typing import Optional

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_session
from app.errors import ApiError
from app.schemas import ChartSpec
from app.services.dashboards import (
    add_card,
    create_dashboard,
    dashboard_name_exists,
    get_dashboard,
    get_dashboard_by_share,
    list_dashboards,
    remove_card,
    rename_dashboard,
    update_layout,
)


router = APIRouter()


class DashboardInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class CardLayout(BaseModel):
    x: int = Field(ge=0, le=11)
    y: int = Field(ge=0)
    w: int = Field(ge=1, le=12)
    h: int = Field(ge=1, le=12)


class CardInput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    analysis_id: str = Field(min_length=1)
    chart: ChartSpec
    layout: CardLayout


class LayoutItem(CardLayout):
    id: str


class LayoutInput(BaseModel):
    cards: list[LayoutItem] = Field(default_factory=list)


def _missing() -> ApiError:
    return ApiError(404, "DASHBOARD_NOT_FOUND", "仪表盘不存在", "请刷新仪表盘列表")


def _validate_dashboard_name(session: Session, name: str, exclude_dashboard_id: Optional[str] = None) -> str:
    normalized = name.strip()
    if not normalized:
        raise ApiError(400, "DASHBOARD_NAME_EMPTY", "仪表盘名称不能为空", "请输入一个清晰的仪表盘名称")
    if dashboard_name_exists(session, normalized, exclude_dashboard_id=exclude_dashboard_id):
        raise ApiError(409, "DASHBOARD_NAME_DUPLICATE", "仪表盘名称已存在", "请换一个名称后重试")
    return normalized


@router.get("/dashboards")
def dashboards(session: Session = Depends(get_session)):
    return list_dashboards(session)


@router.post("/dashboards", status_code=201)
def dashboard_create(payload: DashboardInput, session: Session = Depends(get_session)):
    return create_dashboard(session, _validate_dashboard_name(session, payload.name))


@router.get("/dashboards/share/{share_id}")
def dashboard_share(share_id: str, session: Session = Depends(get_session)):
    dashboard = get_dashboard_by_share(session, share_id)
    if dashboard is None:
        raise _missing()
    return dashboard


@router.get("/dashboards/{dashboard_id}")
def dashboard_detail(dashboard_id: str, session: Session = Depends(get_session)):
    dashboard = get_dashboard(session, dashboard_id)
    if dashboard is None:
        raise _missing()
    return dashboard


@router.patch("/dashboards/{dashboard_id}")
def dashboard_rename(
    dashboard_id: str,
    payload: DashboardInput,
    session: Session = Depends(get_session),
):
    dashboard = rename_dashboard(
        session,
        dashboard_id,
        _validate_dashboard_name(session, payload.name, exclude_dashboard_id=dashboard_id),
    )
    if dashboard is None:
        raise _missing()
    return dashboard


@router.post("/dashboards/{dashboard_id}/cards", status_code=201)
def dashboard_add_card(
    dashboard_id: str,
    payload: CardInput,
    session: Session = Depends(get_session),
):
    card = add_card(
        session,
        dashboard_id,
        payload.title,
        payload.analysis_id,
        payload.chart.model_dump(),
        payload.layout.model_dump(),
    )
    if card is None:
        raise _missing()
    return card


@router.patch("/dashboards/{dashboard_id}/layout")
def dashboard_layout(
    dashboard_id: str,
    payload: LayoutInput,
    session: Session = Depends(get_session),
):
    dashboard = update_layout(
        session, dashboard_id, [card.model_dump() for card in payload.cards]
    )
    if dashboard is None:
        raise _missing()
    return dashboard


@router.delete("/dashboards/{dashboard_id}/cards/{card_id}", status_code=204)
def dashboard_remove_card(
    dashboard_id: str,
    card_id: str,
    session: Session = Depends(get_session),
):
    if not remove_card(session, dashboard_id, card_id):
        raise ApiError(404, "DASHBOARD_CARD_NOT_FOUND", "仪表盘卡片不存在", "请刷新仪表盘")
    return Response(status_code=204)
