from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.errors import ApiError
from app.services.datasource import list_tables, overview, table_detail


router = APIRouter()


@router.get("/datasource/overview")
def datasource_overview(session: Session = Depends(get_session)):
    return overview(session, get_settings().database_url)


@router.get("/datasource/tables")
def datasource_tables(session: Session = Depends(get_session)):
    return list_tables(session)


@router.get("/datasource/tables/{table_name}")
def datasource_table_detail(table_name: str, session: Session = Depends(get_session)):
    detail = table_detail(session, table_name)
    if detail is None:
        raise ApiError(
            404,
            "DATASOURCE_TABLE_NOT_FOUND",
            "数据表不存在或不属于可展示的数据源范围。",
            "请刷新数据源列表后重新选择。",
        )
    return detail
