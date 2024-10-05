from datetime import datetime
from datetime import date
import pathlib
import json
from urllib.parse import unquote

CWD = pathlib.Path(__file__).parent.absolute().resolve()

import pandas as pd
import httpx
from fastapi import APIRouter, Request, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from .backend import crud
from app.utils.logging import log
from app.database.get_db import get_db
from opensarlab.auth import encryptedjwt

router = APIRouter(
    prefix="/quota",
)

@router.post('/clock/start')
async def post_user_quota_data_for_start(request: Request, db_session: Session = Depends(get_db)):
    request_data = await request.body()

    # Decrypt form data
    data = encryptedjwt.decrypt(request_data)
    await crud.update_quota_for_start(data, db=db_session)

@router.post('/clock/stop')
async def post_user_quota_data_for_stop(request: Request, db_session: Session = Depends(get_db)):
    request_data = await request.body()

    # Decrypt form data
    data = encryptedjwt.decrypt(request_data)
    await crud.update_quota_for_stop(data, db=db_session)

@router.get('/credits/username/{username}/lab/{lab_short_name}')
async def get_user_quota_credits_allocated_credits_to_user_per_lab(
    request: Request,
    username: str,
    lab_short_name: str,
    start_time: date=None,
    end_time: date=None,
    db_session: Session = Depends(get_db)) -> dict:

    username = unquote(username)
    lab_short_name = unquote(lab_short_name)

    log.warning(f"Checking quotas for {username=}, {lab_short_name=}, {start_time=}, {end_time=} ")

    #####
    # Get user quota credits currently allocated_credits
    #####
    current_monthly_allocated_credits = 0
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url=f"http://127.0.0.1/portal/hub/auth",
            data=json.dumps({ 'username': f"{username}" }),
            timeout=15
        )
        results = json.loads(response.text)
        if results['message'] == 'OK':
            user_data = encryptedjwt.decrypt(results['data'])
            if user_data:
                for labs in user_data['access'].items():
                    time_quota = labs.get(lab_short_name, {}).get('time_quota', None)
                    if time_quota:
                        current_monthly_allocated_credits = float(time_quota)

    #####
    # Get user quota credits currently used
    #####

    # Beginning at current month if start_time argument is not given
    if not start_time:
        today = datetime.today().date()
        start_time = today.replace(day=1)

    if not end_time:
        end_time = datetime.now()

    # Get quota DB data including where end_time is None
    quotas = await crud.get_quotas_used_within_time_period(
        username=username,
        lab_short_name=lab_short_name,
        begin_time=start_time,
        end_time=end_time,
        db=db_session
    )

    quotas = jsonable_encoder(quotas)

    def _str_to_datetime(str_dt: str) -> datetime:
        if str_dt:
            return datetime.strptime(str_dt, "%Y-%m-%d %H:%M:%S.%f")
        # If stop_time is not defined, then there is probably an active server. Replace None with now() to help calculate real time.
        else:
            return datetime.now()

    # Create pandas dataframe with DB data
    data_frame = pd.DataFrame(columns=['profile_name', 'cpu_hour', 'start_time', 'stop_time'])
    for quota in quotas:
        data_frame = pd.concat([
            data_frame, 
            pd.DataFrame({
                'profile_name': [quota.get('profile_name')],
                'cpu_hour': [float(quota.get('cpu_hour'))],
                'start_time': [_str_to_datetime(quota.get('start_time'))],
                'stop_time': [_str_to_datetime(quota.get('stop_time'))]
            })],
            axis=0, ignore_index=True
        )

    if data_frame.empty:
        log.warning("No quota data found within the specified time range.")
        return {
            "current_monthly_allocated_credits": current_monthly_allocated_credits,
            "total_credits_used": None,
            "estimated_hours_remaining": None
        }

    # Based on usage data, calculate various numbers
    data_frame['diff_time'] = data_frame['stop_time'] - data_frame['start_time']

    data_frame['total_hours'] = data_frame['diff_time'].apply(lambda total_hours: total_hours.total_seconds() / 3600.0)
    data_frame['credits_used'] = data_frame['total_hours'] * data_frame['cpu_hour']

    total_credits_used = float(data_frame['credits_used'].sum())

    #####
    # Get estimated quota credits remaining based on current active server
    #####

    # Get last row's cpu_hour since either this is an active server or best guess future server
    last_row = data_frame.iloc[-1:]
    cpu_hour = float(last_row['cpu_hour'])

    log.warning(f">>>>> current_monthly_allocated_credits: {current_monthly_allocated_credits}, total_credits_used: {total_credits_used}, cpu_hour: {cpu_hour}")
    estimated_hours_remaining = float(current_monthly_allocated_credits - total_credits_used) / cpu_hour

    #####
    # Return results
    #####

    return {
        "current_monthly_allocated_credits": current_monthly_allocated_credits,
        "total_credits_used": total_credits_used,
        "estimated_hours_remaining": estimated_hours_remaining
    }
