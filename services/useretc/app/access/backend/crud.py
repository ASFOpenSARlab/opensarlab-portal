
import math

from sqlalchemy.orm import Session

from app.utils.logging import log
from app.database.utils import convert_to_dict
from app.database.schema import Access

async def get_data_for_lab(lab_short_name: str, db: Session) -> list:
    records = db.query(
            Access.username,
            Access.lab_profiles,
            Access.active_till_dates,
            Access.time_quota,
            Access.comments
        ).filter(
            Access.lab_short_name == lab_short_name
        ).order_by(
            Access.row_id
        ).all()

    if not records:
        return []
    return [convert_to_dict(record) for record in records]

async def get_data_for_username(username: str, db: Session) -> list:
    records = db.query(
            Access.lab_short_name,
            Access.username,
            Access.row_id,
            Access.lab_profiles,
            Access.active_till_dates,
            Access.time_quota,
            Access.comments
        ).filter(
            Access.username == username
        ).order_by(
            Access.lab_short_name,
            Access.row_id,
            Access.username
        ).all()

    if not records:
        return []
    return [convert_to_dict(record) for record in records]

async def get_lab_short_names(db: Session) -> list:
    records = db.query(
            Access.lab_short_name
        ).group_by(
            Access.lab_short_name
        ).all()

    if not records:
        return []
    return [convert_to_dict(record)['lab_short_name'] for record in records]

async def update_data_for_lab(lab_short_name: str, data: list, db: Session) -> None:
    # For lab_short_name, if exists update. Otherwise, insert
    # For row -> row_id, if exists update. Otherwise, insert.
    # For other fields, always update according to row_id and lab_short_name
    for row in data:
        row_id = row['row']
        row_data = row['data']

        row_exists = db.query(Access).filter(
                Access.lab_short_name == lab_short_name,
                Access.row_id == row_id
            ).first() is not None

        if row_exists:

            # Delete row if all data is gone
            if not row['data'].get('lab_profile', math.inf) and \
                not row['data'].get('username', math.inf) and \
                not row['data'].get('time_quota', math.inf):
                pass
                #db.query(Access).filter(
                #    Access.lab_short_name == lab_short_name,
                #    Access.row_id == row_id
                #).delete()

            # update
            else:
                db.query(Access).filter(
                        Access.lab_short_name == lab_short_name,
                        Access.row_id == row_id
                    ).update(row_data)
                db.commit()

        else:
            # insert
            db_entry = Access(lab_short_name=lab_short_name, row_id=row_id, **row_data)
            db.add(db_entry)
            db.commit()
            db.refresh(db_entry)
