
"""
Reformat public ICAL calendar (where the description is in a particular format) into something easier to digest
"""

import pathlib
from datetime import datetime
import re
from urllib.parse import unquote
 
import yaml
from ics import Calendar
import httpx
from fastapi import APIRouter, HTTPException
import html2text

from app.utils.logging import log

CWD = pathlib.Path(__file__).parent.absolute().resolve()

router = APIRouter(
    prefix="/notifications",
)

async def notes(profile_arg: str, ical_arg: str) -> list:

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url=ical_arg,
                timeout=15
            )

        cal = Calendar(resp.text)
        active_events = []
        
        for event in list(cal.events):
            begin_time = event.begin.to('utc').datetime.replace(tzinfo=None)
            now_time = datetime.utcnow().replace(tzinfo=None)
            end_time = event.end.to('utc').datetime.replace(tzinfo=None)

            if begin_time <= now_time <= end_time:
                compiled = re.compile("<meta>(.*)<message>(.*)$", re.DOTALL)
                descr_to_html = html2text.html2text(event.description)

                groups = compiled.search(descr_to_html)
                
                try:
                    meta = yaml.safe_load(groups.group(1))
                    message = groups.group(2)

                    profile = [ prof.strip() for prof in meta['profile'].split(',') ]

                    if 'mute' not in meta:
                        if type(profile) is not list:
                            profile = [profile]

                        if profile_arg == 'all' or profile_arg in profile:
                            active_events.append(
                                {
                                    "title": event.name,
                                    "message": message.strip(),
                                    "type": meta['type'].strip(),
                                    "placement": meta.get('placement', 'top-full-width').strip()
                                }
                            )
                except Exception as e:
                    log.error(e)
                    message = """
There must be a description of format:

<meta>
    profile: SAR 1, Other_profile_names
    type: info, error, warning, success
    mute: true
    placement: bottom-full-width, top-full-width, top-center, top-right, bottom-right

<message>
    Your message in HTML.""" 
                    raise Exception(message)

        log.info(f"Active events to popup: {active_events}")
        return active_events

    except Exception as e:
        log.error(e)
        raise HTTPException(status_code=500, detail=f"{e}")

@router.get('/{lab_short_name}')
async def get_user_notifications(lab_short_name: str=None, profile: str=None) -> list:

    if not lab_short_name or not profile:
        return []

    lab_short_name = unquote(lab_short_name)
    profile = unquote(profile)

    with open(CWD / 'ical.yaml', 'r') as f:
        try:
            icals = yaml.safe_load(f)
        except Exception as e:
            log.error(f"ICAL yaml not proper: {e}")
            return []

    if type(icals) != dict:
        return []

    ical_url = icals.get(lab_short_name, '')
    log.info(f"ICAL url: {ical_url}, lab short name: {lab_short_name}, profile: {profile}")

    if not ical_url:
        return []

    return await notes(profile, ical_url)
