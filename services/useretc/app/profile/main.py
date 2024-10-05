
import datetime
import pathlib
import json
import io
from urllib.parse import unquote

CWD = pathlib.Path(__file__).parent.resolve().absolute()

import pandas as pd
from fastapi import Depends, Request, status, APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from opensarlab.auth import encryptedjwt

from app.utils.logging import log
from app.utils.decorator import user_type
from app.database.get_db import get_db
from . import crud
from . import validate

router = APIRouter(
    prefix="/profile",
)

templates = Jinja2Templates(directory=f"{CWD}/web")

@router.get('/all')
@user_type('admin')
async def get_all_user_profiles(request: Request, format: str = 'text', db: Session = Depends(get_db)):
    """
    Serve raw data of all profiles
    """
    data = crud.get_all_profiles(db=db)
    json_data = jsonable_encoder(data)

    if format == 'encrypted':
        return encryptedjwt.encrypt(json_data)

    elif format == 'csv':
        df = pd.DataFrame(json_data)
        stream = io.StringIO()

        df.to_csv(stream, index = False)

        response = StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv"
        )
        response.headers["Content-Disposition"] = f"attachment; filename=profiles_{datetime.datetime.now()}.csv"
        return response

    else:
        return JSONResponse(json_data)

@router.get('/check/{username}')
@user_type('admin', 'user')
async def get_check_user_profile(request: Request, username: str, db: Session = Depends(get_db)) -> str:
    """
    DB check if user has already submitted form
    """
    username = unquote(username)
    status = crud.check_user_profile_username(db=db, username=username)
    return encryptedjwt.encrypt(jsonable_encoder(status))

@router.get('/raw/{username}')
async def get_raw_user_profile(request: Request, username: str, db: Session = Depends(get_db)) -> str:
    """
    Serve raw data of user's profile
    """
    username = unquote(username)
    data = crud.get_profile_by_username(db=db, username=username)
    if not data:
        data = {}
    return encryptedjwt.encrypt(data)

def _render_template(request: Request, username: str, previous: str, db: Session, err_string: str=None) -> str:

    try:
        user_profile = crud.get_profile_by_username(db=db, username=username)
    except Exception as e:
        log.error(f"Something went wrong with getting the profile from the database for {username}: {e}")
        err_string = "Something went wrong with getting your user profile info. Please contact an OpenScienceLab admin."

    # If no user profile then assume this is the first time and make defaults.
    if not user_profile:
        user_profile = {
            'force_update': True,
            'country_of_residence': '',
            'is_affliated_with_nasa_research': '',
            'has_affliated_with_nasa_research_email': '',
            'user_affliated_with_nasa_research_email': '',
            'pi_affliated_with_nasa_research_email': '',
            'is_affliated_with_gov_research': '',
            'user_affliated_with_gov_research_email': '',
            'is_affliated_with_isro_research': '',
            'user_affliated_with_isro_research_email': '',
            'is_affliated_with_university': '',
            'faculty_member_affliated_with_university': '',
            'research_member_affliated_with_university': '',
            'graduate_student_affliated_with_university': ''
        }

    friendly_conversion = {
        'country_of_residence': 'What is your current country of residence?',
        'is_affliated_with_nasa_research': 'Are you affiliated with NASA?',
        'has_affliated_with_nasa_research_email': 'Do you have a NASA email address?',
        'user_affliated_with_nasa_research_email': 'What is your NASA email address?',
        'pi_affliated_with_nasa_research_email': 'What is the email address of the NASA project’s PI?',
        'is_affliated_with_gov_research': 'Are you affiliated with a US government-funded research program?',
        'user_affliated_with_gov_research_email': 'What is your official US government email address?',
        'is_affliated_with_isro_research': 'Are you affiliated with ISRO?',
        'user_affliated_with_isro_research_email': 'What is your ISRO email address, or the ISRO email address of the project PI?',
        'is_affliated_with_university': 'Are you affiliated with a university?',
        'faculty_member_affliated_with_university': 'Are you an university faculty member?',
        'research_member_affliated_with_university': 'Are you an university research scientist?',
        'graduate_student_affliated_with_university': 'Are you an university graduate student?'
    }

    form_data = {}

    # To the cloud!!
    form_data['is_affliated_with_nasa_research'] = ['Yes', 'No']
    form_data['has_affliated_with_nasa_research_email'] = ['Yes', 'No']
    form_data['is_affliated_with_gov_research'] = ['Yes', 'No']
    form_data['is_affliated_with_isro_research'] = ['Yes', 'No']
    form_data['is_affliated_with_university'] = ['Yes', 'No']
    form_data['faculty_member_affliated_with_university'] = ['Yes', 'No']
    form_data['research_member_affliated_with_university'] = ['Yes', 'No']
    form_data['graduate_student_affliated_with_university'] = ['Yes', 'No']


    # Get list of countries
    with open(CWD / 'data/countries.json', 'r') as f:
        form_data['country_of_residence'] = json.loads(f.read())


    try:
        template = templates.TemplateResponse(
            "profile.html.j2", 
            {
                'request': request,
                'username': username,
                'user_profile': user_profile,
                'form_data': form_data,
                'err_string': err_string,
                'default_value': 'Choose...',
                'friendly_conversion': friendly_conversion,
                'previous': previous,
            }
        )
    except Exception as e:
        log.error(f"Something went wrong with getting the user profile template for {username}: {e}")
        raise


    return template

@router.post('/show/{username}')
@user_type('user')
async def post_show_user_profile(request: Request, username: str, previous: str='/portal/hub/home', db: Session = Depends(get_db)) -> str:
    """
    Post/update user's profile
    """
    username = unquote(username)
    previous = unquote(previous)

    form = await request.form()
    form = dict(form)

    err_string = None
    try:
        validate.validate_form(form)

        num_rows = crud.update_profile_by_username(db=db, username=username, profile=form)
        if num_rows == 0:
            log.warning(f"No rows updated for {username} means no user exists. Thus create one...")
            crud.create_profile(db=db, username=username, profile=form)

        return RedirectResponse(previous, status_code=status.HTTP_302_FOUND)
    
    except validate.FormValidationException as e:
        err_string = f"{e}"

    except Exception as e:
        log.error(f"Unknown error: {e}")
        err_string = f"An unknown error occurred. If this persists, contact an OpenScienceLab admin."

    return _render_template(request, username, previous, db, err_string=err_string)

@router.get('/show/{username}', response_class=HTMLResponse)
@user_type('user')
async def get_show_user_profile(request: Request, username: str, previous: str='/portal/hub/home', db: Session = Depends(get_db)) -> str:
    """
    Serve webpage of user's profile
    """
    username = unquote(username)
    previous = unquote(previous)
    return _render_template(request, username, previous, db)
