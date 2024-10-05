"""
Some more commonly shared snippets used withing the useretc directory
"""

import json
from urllib.parse import quote

import httpx
from fastapi import HTTPException, status, Request
from fastapi.responses import RedirectResponse

from opensarlab.auth import encryptedjwt

async def get_user_email_for_username(username: str) -> str:
    """ 
    From given username, get email address from Database. If no user or error, return ''. 
    As a special case, username "osl-admin" will return the Admin email.
    """

    if not username:
        return ''

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url=f'http://127.0.0.1/portal/hub/native-user-info?username={quote(username)}',
            timeout=15
        )
        user_info = dict(encryptedjwt.decrypt(resp.text))
        user_info_error = user_info.get('error', None)
        if user_info_error:
            raise Exception(user_info_error)
        else:
            the_email = user_info.get('email', None)

    return the_email

async def get_user_info_from_username_cookie(request: Request) -> dict:
    """
    If an user is signed in, they will have a `poral-username` cookie containing the plaintext username.
    From this we can decrypted user access info. 
    """

    # Check if cookie is present. If yes, then user is signed in
    cookie = request.cookies.get('portal-username')

    if not cookie:
        return {}
    
    cookie_username = cookie

    # Get auth from username
    async with httpx.AsyncClient() as client:
        data = json.dumps({"username": f"{cookie_username}"})
        res = await client.post('http://127.0.0.1/portal/hub/auth', data=data,  timeout=10)
        res = res.json()

    if res['message'] == 'OK':
        user_info = encryptedjwt.decrypt(res['data'])
    else:
        raise HTTPException(status_code=401)

    return user_info

async def get_decrypted_data_from_url(url: str) -> dict:
    """
    Return decrypted data from Portal service URLs
    """

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    data = encryptedjwt.decrypt(response.content)

    return data

async def send_email_in_portal_service(email: dict) -> None:
    """
    Encrypt email object and send to portal email service.

    email = {
            "to": {
                "username": [""] | "",
                "email": [""] | ""
            },
            "from": {
                "username": "",
                "email": ""
            },
            "cc": {
                "username": [""] | "",
                "email": [""] | ""
            },
            "bcc": {
                "username": [""] | "",
                "email": [""] | ""
            },
            "subject": "",
            "html_body": ""
        }
    """

    data = encryptedjwt.encrypt(email)

    url = "http://127.0.0.1/user/email/send"
    async with httpx.AsyncClient() as client:
        r = await client.post(url=url, data=data, timeout=5)
    r.raise_for_status
