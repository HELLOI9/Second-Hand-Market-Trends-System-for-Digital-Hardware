from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import PriceAlert
from app.services.notifier import send_notification

router = APIRouter(prefix="/alerts", tags=["alerts"])
DbDep = Annotated[AsyncSession, Depends(get_db)]


class AlertIn(BaseModel):
    scope_type: str
    scope_value: str | None = None
    rule_type: str
    threshold: float | None = None
    channel: str
    channel_target: str
    cooldown_hours: int = 24
    is_active: bool = True


class AlertPatch(BaseModel):
    scope_type: str | None = None
    scope_value: str | None = None
    rule_type: str | None = None
    threshold: float | None = None
    channel: str | None = None
    channel_target: str | None = None
    cooldown_hours: int | None = None
    is_active: bool | None = None


def _serialize(alert: PriceAlert) -> dict:
    return {
        "id": alert.id,
        "scope_type": alert.scope_type,
        "scope_value": alert.scope_value,
        "rule_type": alert.rule_type,
        "threshold": alert.threshold,
        "channel": alert.channel,
        "channel_target": alert.channel_target,
        "is_active": alert.is_active,
        "last_fired_at": alert.last_fired_at,
        "cooldown_hours": alert.cooldown_hours,
        "created_at": alert.created_at,
    }


@router.post("")
async def create_alert(payload: AlertIn, db: DbDep):
    alert = PriceAlert(**payload.model_dump())
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return _serialize(alert)


@router.get("")
async def list_alerts(db: DbDep, channel_target: str | None = Query(default=None)):
    stmt = select(PriceAlert).order_by(PriceAlert.created_at.desc())
    if channel_target:
        stmt = stmt.where(PriceAlert.channel_target == channel_target)
    alerts = (await db.execute(stmt)).scalars().all()
    return [_serialize(alert) for alert in alerts]


@router.patch("/{alert_id}")
async def update_alert(alert_id: int, payload: AlertPatch, db: DbDep):
    alert = await db.get(PriceAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(alert, key, value)
    await db.commit()
    await db.refresh(alert)
    return _serialize(alert)


@router.delete("/{alert_id}")
async def delete_alert(alert_id: int, db: DbDep):
    alert = await db.get(PriceAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.delete(alert)
    await db.commit()
    return {"status": "deleted"}


@router.post("/{alert_id}/test")
async def test_alert(alert_id: int, db: DbDep):
    alert = await db.get(PriceAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    ok = await send_notification(alert.channel, alert.channel_target, "价格提醒测试：订阅通道已连通")
    return {"status": "sent" if ok else "failed"}
