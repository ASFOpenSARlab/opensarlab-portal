from sqlalchemy.orm import Session

from app.database.schema import Profile
from app.database.utils import convert_to_dict

def check_user_profile_username(db: Session, username: str) -> bool:
    profile = db.query(Profile).filter(Profile.username == username).first()
    if not profile:
        return False
    return not profile.force_update

def get_all_profiles(db: Session) -> list:
    records = db.query(Profile).all()
    if not records:
        return []
    return [convert_to_dict(record) for record in records]

def get_profile_by_username(db: Session, username: str) -> dict:
    record = db.query(Profile).filter(Profile.username == username).first()
    if not record:
        return {}
    return convert_to_dict(record)

def create_profile(db: Session, username: str, profile: dict) -> dict:
    record = Profile(username=username, **profile)
    db.add(record)
    db.commit()
    db.refresh(record)

    if not record:
        return {}
    return convert_to_dict(record)

def update_profile_by_username(db: Session, username: str, profile: dict) -> int:
    # Since we are now updating the row, any "force_update" is satisfied.
    profile.update( {'force_update': False } )

    num_rows_updated = db.query(Profile) \
        .filter(Profile.username == username) \
        .update(profile, synchronize_session=False)
    db.commit()
    return num_rows_updated
