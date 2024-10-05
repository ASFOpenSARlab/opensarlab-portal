import datetime

from sqlalchemy.orm import Session

from app.utils.logging import log
from app.database.utils import convert_to_dict
from app.database.schema import GeoLocation

"""
username = Column(String, default=None)
ip_address = Column(String, default=None)
ip_country_status = Column(String, default=None)
country_code = Column(String, default=None)
"""

async def add_geodata(data, db: Session) -> None:
    """
    Keep one row per user. 

    Originally, the idea was to insert a new row per call. But we could easily get 10,000 rows in a couple months. 
    Since this would become burdensome, only keep one up-to-date entry.
    IP info will have to be parsed from the logs. Future DB work might allow for the original idea.
    """
    
    row_exists = db.query(GeoLocation).filter(
            GeoLocation.username == data['username']
        ).first() is not None

    if row_exists:
        db.query(GeoLocation).filter(
                GeoLocation.username == data['username']
            ).update(
                {
                    'ip_address': data['ip_address'], 
                    'ip_country_status': data['ip_country_status'],
                    'country_code': data['country_code'],
                    'timestamp': datetime.datetime.now(datetime.timezone.utc)
                }
            )
        db.commit()

    else:
        db_entry = GeoLocation(
            username=data['username'],
            ip_address=data['ip_address'], 
            ip_country_status=data['ip_country_status'],
            country_code=data['country_code'],
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        db.add(db_entry)
        db.commit()

async def get_latest_geodata_for_username(username: str, db: Session) -> dict:
    record = db.query(
            GeoLocation.username,
            GeoLocation.ip_address,
            GeoLocation.ip_country_status,
            GeoLocation.country_code,
            GeoLocation.timestamp
        ).filter(
            GeoLocation.username == username
        ).order_by(
            GeoLocation.timestamp.desc()
        ).first()

    if not record:
        return {
            'username': None,
            'ip_address': None,
            'ip_country_status': None,
            'country_code': None,
            'timestamp': None
        }

    def callback(obj):
        import datetime
        if obj.get('timestamp', None):
            obj['timestamp'] = obj['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
        return obj

    return convert_to_dict(record, callback_after=callback)

async def get_all_geodata_for_all(db: Session) -> list:
    records = db.query(
            GeoLocation.username,
            GeoLocation.ip_address,
            GeoLocation.ip_country_status,
            GeoLocation.country_code,
            GeoLocation.timestamp
        ).order_by(
            GeoLocation.timestamp
        ).all()

    if not records:
        return [{
            'username': None,
            'ip_address': None,
            'ip_country_status': None,
            'country_code': None,
            'timestamp': None
        }]

    def callback(obj):
        import datetime
        if obj.get('timestamp', None):
            obj['timestamp'] = obj['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
        return obj

    return [convert_to_dict(record, callback_after=callback) for record in records]
