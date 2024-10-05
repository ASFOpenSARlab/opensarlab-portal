import pathlib
from urllib.parse import quote

CWD = pathlib.Path(__file__).parent.absolute().resolve()

import httpx
import starlette.status as status
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from jinja2 import Environment, FileSystemLoader

#from .backend import crud
from app.utils import helps
from app.utils.decorator import user_type
from app.utils.logging import log

template_path = CWD / "frontend"

env = Environment(
    loader=FileSystemLoader(template_path),
    autoescape=True
)

router = APIRouter(
    prefix="/request",
)

async def get_profile_info(username: str) -> dict:

    # Get Profile data for user
    profile = await helps.get_decrypted_data_from_url(f"http://127.0.0.1/user/profile/raw/{username}")

    # Remove 'id', 'username', 'force_update'
    del profile['id']
    del profile['username']
    del profile['force_update']

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

    # Convert hard-to-read keys from DB field to easier text
    new_profile = profile.copy()
    for key, value in profile.items():
        conversion_value = friendly_conversion.get(key, None)

        if conversion_value:
            new_profile[conversion_value] = value
        del new_profile[key]

    # Remove "empty" answers to make things easier to read
    final_profile = new_profile.copy()
    for key, value in new_profile.items():

        def _del_key(profile: dict, key: str) -> None:
            if profile.get(key, None):
                del profile[key]
            return profile        

        if final_profile.get('Are you affiliated with NASA?', 'No') == 'No':
            _del_key(final_profile, 'Do you have a NASA email address?')
            _del_key(final_profile, 'What is your NASA email address?')
            _del_key(final_profile, 'What is the email address of the NASA project’s PI?')

        if final_profile.get('Do you have a NASA email address?', 'No') == 'Yes':
            _del_key(final_profile, 'What is the email address of the NASA project’s PI?')
        else:
            _del_key(final_profile, 'What is your NASA email address?')

        if not final_profile.get('What is the email address of the NASA project’s PI?', ''):
            _del_key(final_profile, 'What is the email address of the NASA project’s PI?')

        if not final_profile.get('What is your NASA email address?', ''):
            _del_key(final_profile, 'What is your NASA email address?')

        if final_profile.get('Are you affiliated with a US government-funded research program?', 'No') == 'No':
            _del_key(final_profile, 'What is your official US government email address?')

        if not final_profile.get('What is your official US government email address?', ''):
            _del_key(final_profile, 'What is your official US government email address?')

        if final_profile.get('Are you affiliated with ISRO?', 'No') == 'No':
            _del_key(final_profile, 'What is your ISRO email address, or the ISRO email address of the project PI?')

        if not final_profile.get('What is your ISRO email address, or the ISRO email address of the project PI?', ''):
            _del_key(final_profile, 'What is your ISRO email address, or the ISRO email address of the project PI?')

        if final_profile.get('Are you affiliated with a university?', 'No') == 'No':
            _del_key(final_profile, 'Are you an university faculty member?')
            _del_key(final_profile, 'Are you an university research scientist?')
            _del_key(final_profile, 'Are you an university graduate student?')

    return final_profile

@router.get('/lab/{lab_short_name}', response_class=HTMLResponse)
@user_type('user')
async def get_request_page(request: Request, lab_short_name: str) -> HTMLResponse:

    ### Get user info
    user_info = await helps.get_user_info_from_username_cookie(request)

    username = user_info.get('name', None)
    lab_access = user_info.get('lab_access', {})

    lab_meta = lab_access.get(lab_short_name, {})

    lab_country_status = lab_meta.get('lab_country_status', None)

    # If user gets to the page directly but they are prohibited, deny entry
    if lab_country_status and lab_country_status == 'prohibited':
        return RedirectResponse(f"/errors/403.html", status_code=403)

    profile_info = await get_profile_info(username)

    previous = quote(f"/user/request/lab/{lab_short_name}")

    # Render template
    user_data = {
        'username': username,
        'lab_short_name': lab_short_name,
        'profile': profile_info,
        'previous': previous
    }

    template = env.get_template("request.html.j2")
    html_content = template.render(user_data=user_data)

    return HTMLResponse(content=html_content, status_code=200)

@router.post('/lab/{lab_short_name}')
@user_type('user')
async def post_request_page(request: Request, lab_short_name: str) -> None:

    # Get Post Form data
    form = await request.form()
    form_reason_value = form.get('request-reason', '')

    ### Get user info
    user_info = await helps.get_user_info_from_username_cookie(request)
    username = user_info.get('name', None)
    country_code = user_info.get('country_code', None)
    lab_access = user_info.get('lab_access', {})

    lab_meta = lab_access.get(lab_short_name, {})

    lab_country_status = lab_meta.get('lab_country_status', None)

    # If user gets to the page directly but they are prohibited, deny entry
    if lab_country_status and lab_country_status == 'prohibited':
        return RedirectResponse(f"/errors/403.html", status_code=403)        
    ###

    # Get profile info
    profile_info = await get_profile_info(username)

    try:
        user_email_address = await helps.get_user_email_for_username(username=username)
    except Exception as e:
        log.error(f"{e}")
        RedirectResponse(f"/user/request/error", status_code=status.HTTP_303_SEE_OTHER)
    
    try:
        # Send email to admin
        user_data = {
            "lab_short_name": lab_short_name,
            "username": username, 
            "user_email_address": user_email_address,
            "profile_info": profile_info,
            "user_reason": form_reason_value,
            "ip_country_status": lab_country_status,
            "ip_country_code": country_code,
        }

        template = env.get_template("email_admin.html.j2")
        html_body = template.render(user_data=user_data)

        email = {
            "to": {
                "username": "osl-admin"
            },
            "from": {
                "username": "osl-admin"
            },
            "subject": "Lab Access Requested",
            "html_body": f"{html_body}"
        }

        await helps.send_email_in_portal_service(email)

    except Exception as e:
        log.error(f"{e}")
        RedirectResponse(f"/user/request/error", status_code=status.HTTP_303_SEE_OTHER)

    try:
        # Email user
        user_data = {
            "lab_short_name": lab_short_name,
            "username": username,
            "user_reason": form_reason_value,
        }

        template = env.get_template("email_user.html.j2")
        html_body = template.render(user_data=user_data)

        email = {
            "to": {
                "email": f"{user_email_address}"
            },
            "from": {
                "username": "osl-admin"
            },
            "subject": "Lab Access Requested",
            "html_body": f"{html_body}"
        }

        await helps.send_email_in_portal_service(email)

    except Exception as e:
        log.error(f"{e}")
        RedirectResponse(f"/user/request/error", status_code=status.HTTP_303_SEE_OTHER)

    return RedirectResponse(f"/user/request/submitted", status_code=status.HTTP_303_SEE_OTHER)

@router.get('/submitted', response_class=HTMLResponse)
#@user_type('user')
async def get_request_page(request: Request):
    return FileResponse(f"{CWD}/frontend/submitted.html")

@router.get('/error', response_class=HTMLResponse)
#@user_type('user')
async def get_request_page(request: Request):
    return FileResponse(f"{CWD}/frontend/error.html")