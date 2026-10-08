from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from uptime_watch.db import get_session
from uptime_watch.models import Monitor
from uptime_watch.schemas import MonitorCreate, MonitorRead

router = APIRouter(prefix="/api/v1/monitors", tags=["monitors"])

SessionDep = Annotated[Session, Depends(get_session)]


def _get_or_404(session: Session, monitor_id: int) -> Monitor:
    monitor = session.get(Monitor, monitor_id)
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
