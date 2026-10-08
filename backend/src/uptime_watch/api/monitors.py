from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from uptime_watch.db import get_session
from uptime_watch.models import Monitor
from uptime_watch.schemas import MonitorCreate, MonitorPage, MonitorRead, MonitorUpdate

router = APIRouter(prefix="/api/v1/monitors", tags=["monitors"])

SessionDep = Annotated[Session, Depends(get_session)]

# The id is a Postgres INTEGER; anything outside it cannot exist and would be a DataError.
MAX_ID = 2_147_483_647


def _get_or_404(session: Session, monitor_id: int) -> Monitor:
    monitor = session.get(Monitor, monitor_id) if 1 <= monitor_id <= MAX_ID else None
    if monitor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Monitor not found")
    return monitor


def _commit_or_409(session: Session) -> None:
    # The only constraint a client can violate is the unique URL.
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "A monitor for this URL already exists"
        ) from None


@router.post("", status_code=status.HTTP_201_CREATED, response_model=MonitorRead)
def create_monitor(body: MonitorCreate, session: SessionDep) -> Monitor:
    monitor = Monitor(
        name=body.name,
        url=str(body.url),
        interval_seconds=body.interval_seconds,
        paused=body.paused,
    )
    session.add(monitor)
    _commit_or_409(session)
    session.refresh(monitor)
    return monitor


@router.get("/{monitor_id}", response_model=MonitorRead)
def get_monitor(monitor_id: int, session: SessionDep) -> Monitor:
    return _get_or_404(session, monitor_id)


@router.get("", response_model=MonitorPage)
def list_monitors(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MonitorPage:
    total = session.scalar(select(func.count()).select_from(Monitor)) or 0
    monitors = session.scalars(
        select(Monitor).order_by(Monitor.id).limit(limit).offset(offset)
    ).all()
    return MonitorPage(
        items=[MonitorRead.model_validate(m) for m in monitors],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch("/{monitor_id}", response_model=MonitorRead)
def update_monitor(monitor_id: int, body: MonitorUpdate, session: SessionDep) -> Monitor:
    monitor = _get_or_404(session, monitor_id)
    changes = body.model_dump(exclude_unset=True)
    if "url" in changes:
        changes["url"] = str(body.url)
    for field, value in changes.items():
        setattr(monitor, field, value)
    _commit_or_409(session)
    session.refresh(monitor)
    return monitor


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_monitor(monitor_id: int, session: SessionDep) -> Response:
    session.delete(_get_or_404(session, monitor_id))
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
