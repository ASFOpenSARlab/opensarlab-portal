
from datetime import datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.utils.logging import log
from app.database.utils import convert_to_dict
from app.database.schema import Quota

async def update_quota_for_start(data, db: Session) -> None:

    db_entry = Quota(
        spawner_instance_id=data['spawner_instance_id'],
        username=data['username'],
        lab_short_name=data['lab_short_name'], 
        start_time=data['start_time'],
        profile_name=data['profile_name'],
        cpu_hour=data['cpu_hour'],
    )
    db.add(db_entry)
    db.commit()

async def update_quota_for_stop(data, db: Session) -> None:

    db.query(Quota).filter(
            Quota.spawner_instance_id == data['spawner_instance_id']
        ).update(
            {
                Quota.stop_time: data['stop_time']
            },
            synchronize_session=False
        )
    db.commit()

async def get_quotas_used_within_time_period(username: str, lab_short_name: str, begin_time: datetime, end_time: datetime, db: Session) -> float:
    records = db.query(
            Quota.profile_name,
            Quota.cpu_hour,
            Quota.start_time,
            Quota.stop_time
        ).filter(
            or_(
                and_(
                    Quota.lab_short_name == lab_short_name,
                    Quota.username == username,
                    Quota.start_time >= begin_time,
                    Quota.stop_time <= end_time
                ),
                and_(
                    Quota.lab_short_name == lab_short_name,
                    Quota.username == username,
                    Quota.stop_time == None
                )
            )
        ).order_by(
            Quota.lab_short_name,
            Quota.username,
            Quota.profile_name,
            Quota.start_time
        ).all()

    if not records:
        return []
    return [convert_to_dict(record) for record in records]
