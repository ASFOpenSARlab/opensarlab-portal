import datetime

from sqlalchemy import Boolean, Column, Integer, String, DateTime, Float
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///database/files/useretc.db"
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

####
#
# If needed run the following:
#
#   ALTER TABLE access ADD COLUMN active_till_dates VARCHAR;
#
#   ALTER TABLE profile ADD COLUMN is_affliated_with_nasa_research VARCHAR;
#   ALTER TABLE profile ADD COLUMN has_affliated_with_nasa_research_email VARCHAR;
#   ALTER TABLE profile ADD COLUMN user_affliated_with_nasa_research_email VARCHAR;
#   ALTER TABLE profile ADD COLUMN pi_affliated_with_nasa_research_email VARCHAR;
#   ALTER TABLE profile ADD COLUMN is_affliated_with_gov_research VARCHAR;
#   ALTER TABLE profile ADD COLUMN user_affliated_with_gov_research_email VARCHAR;
#   ALTER TABLE profile ADD COLUMN is_affliated_with_isro_research VARCHAR;
#   ALTER TABLE profile ADD COLUMN user_affliated_with_isro_research_email VARCHAR;
#   ALTER TABLE profile ADD COLUMN is_affliated_with_university VARCHAR;
#   ALTER TABLE profile ADD COLUMN faculty_member_affliated_with_university VARCHAR;
#   ALTER TABLE profile ADD COLUMN research_member_affliated_with_university VARCHAR;
#   ALTER TABLE profile ADD COLUMN graduate_student_affliated_with_university VARCHAR;
#
##

class Profile(Base):
    __tablename__ = "profile"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)

    ## These are deprecated
    career_stages = Column(String)
    migrating_to_cloud = Column(String)
    field_of_study = Column(String)
    field_of_study_other = Column(String)
    how_did_you_hear_about_us = Column(String)
    how_did_you_hear_about_us_other = Column(String)
    belong_to_organization = Column(String)
    ####

    country_of_residence = Column(String)
    is_affliated_with_nasa_research = Column(String)
    has_affliated_with_nasa_research_email = Column(String)
    user_affliated_with_nasa_research_email = Column(String)
    pi_affliated_with_nasa_research_email = Column(String)
    is_affliated_with_gov_research = Column(String)
    user_affliated_with_gov_research_email = Column(String)
    is_affliated_with_isro_research = Column(String)
    user_affliated_with_isro_research_email = Column(String)
    is_affliated_with_university = Column(String)
    faculty_member_affliated_with_university = Column(String)
    research_member_affliated_with_university = Column(String)
    graduate_student_affliated_with_university = Column(String)

    force_update = Column(Boolean, default=True)

class Access(Base):
    __tablename__ = "access"

    id = Column(Integer, primary_key=True, index=True)

    lab_short_name =Column(String)
    row_id = Column(Integer)
    username = Column(String)
    lab_profiles = Column(String)
    time_quota = Column(String)
    active_till_dates = Column(String)
    comments = Column(String)

class Quota(Base):
    __tablename__ = 'quota'

    id = Column(Integer, primary_key=True, index=True)

    spawner_instance_id = Column(String, default=None)
    lab_short_name = Column(String, default=None)
    username = Column(String, default=None)
    profile_name = Column(String, default=None)
    cpu_hour = Column(String, default=None)
    start_time = Column(String, default=None)
    stop_time = Column(String, default=None)

class GeoLocation(Base):
    __tablename__ = 'geolocation'

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String, default=None)
    ip_address = Column(String, default=None)
    ip_country_status = Column(String, default=None)
    country_code = Column(String, default=None)

    timestamp = Column(DateTime, default=None)
