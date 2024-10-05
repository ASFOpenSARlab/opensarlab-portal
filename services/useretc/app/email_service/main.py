"""
Format of payload.

username "osl-admin" substitutes the admin email in the labs.yaml/portal/stmp_verified_email

{
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


import pathlib
from email.message import EmailMessage
import smtplib
import logging
import time
from urllib.parse import quote

CWD = pathlib.Path(__file__).parent.absolute().resolve()

import requests
import httpx
from fastapi import APIRouter, Request, BackgroundTasks

from opensarlab.auth import encryptedjwt
from app.utils import helps

router = APIRouter(
    prefix="/email",
)

async def _get_run_secret(secret_name: str) -> str:
    with open(f"/run/secrets/{secret_name}", 'r') as f:
        value = f.read()
    return value

async def _get_email_info() -> dict:
    ses_usr = await _get_run_secret('ses_user')
    ses_pass = await _get_run_secret('ses_pass')
    ses_url = await _get_run_secret('ses_url')

    return {
        'user': ses_usr.strip(),
        'password': ses_pass.strip(),
        'url': ses_url.strip()
    }

async def parse_email_message(data: dict):
    msg = EmailMessage()

    ####  To
    to_email = data['to'].get('email', '')
    if type(to_email) == str:
        to_email = [to_email]

    to_username = data['to'].get('username', '')
    if type(to_username) == str:
        to_username = [to_username]

    for user in to_username:
        user_email = await helps.get_user_email_for_username(username=user)
        if user_email:
            to_email.append(user_email)
    if not to_email:
        raise Exception("No TO user specified")

    msg['To'] = ','.join(to_email)

    ####  CC
    cc = data.get('cc', None)
    if cc:
        cc_email = cc.get('email', '')
        if type(cc_email) == str:
            cc_email = [cc_email]

        cc_username = cc.get('username', '')
        if type(cc_username) == str:
            cc_username = [cc_username]

        for user in cc_username:
            user_email = await helps.get_user_email_for_username(username=user)
            if user_email:
                cc_email.append(user_email)

        msg['Cc'] = ','.join(cc_email)

    ####  BCC
    bcc = data.get('bcc', None)
    if bcc:
        bcc_email = bcc.get('email', '')
        if type(bcc_email) == str:
            bcc_email = [bcc_email]

        bcc_username = bcc.get('username', '')
        if type(bcc_username) == str:
            bcc_username = [bcc_username]

        for user in bcc_username:
            user_email = await helps.get_user_email_for_username(username=user)
            if user_email:
                bcc_email.append(user_email)

        msg['Bcc'] = ','.join(bcc_email)

    ####  FROM
    from_email = data['from'].get('email', '')
    from_username = data['from'].get('username', '')

    # If username is given for FROM, override any explicit email address.
    user_email = await helps.get_user_email_for_username(username=from_username)
    if user_email:
        from_email = user_email

    if not from_email:
        raise Exception("No FROM email specified")

    msg['From'] = from_email

    data_subject = data.get('subject', '')
    if data_subject:
        msg['Subject'] = data_subject

    msg.set_content("Your email doesn't support html?")

    data_body = data.get('html_body', '')

    if data_body:
        html_body = f"""
        <html>
            <body>
                <h1> Message from OpenScienceLab </h1>
                <section>
                    { data_body }
                </section>
                <section>
                    <hr/>
                    <p> OpenScienceLab is operated by the Alaska Satellite Facility | <a href="https://opensarlab-docs.asf.alaska.edu">OpenScienceLab documentation</a>.</p>
                </section>
            </body>
        </html>
        """
        msg.add_alternative(html_body, subtype='html')

    return msg

async def send_email(data: dict):
    try:
        msg = await parse_email_message(data)
        stmp_server = await _get_email_info()
        s = smtplib.SMTP_SSL(stmp_server['url'])
        s.login(stmp_server["user"], stmp_server["password"])
        s.send_message(msg)
        s.quit()
    except Exception as exception_msg:
        logging.error("Something went wrong with sending original email. Attempting to send notice to admin.")

        error_data = {
            "from": {
                "username": "osl-admin"
            },
            "to": {
                "username": "osl-admin"
            },
            "subject": "OpenScienceLab notification - Error in sending email",
            "html_body": f"""
                <p>There was an error in sending an email. Below is the info.

                <h2>Error</h2>
                {str(exception_msg)}

                <h2>Original email metadata</h2>
                {dict(data)}
            """
        }

        error_msg = await parse_email_message(error_data)
        stmp_server = await _get_email_info()
        s = smtplib.SMTP_SSL(stmp_server['url'])
        s.login(stmp_server["user"], stmp_server["password"])
        s.send_message(error_msg)
        s.quit()


@router.get('/check')
@router.post('/check')
async def check_user_email(request: Request) -> bool:
    return True

@router.post('/send')
async def send_user_email(request: Request, background_tasks: BackgroundTasks) -> bool:
    request_data = await request.body()
    data = encryptedjwt.decrypt(request_data)
    background_tasks.add_task(send_email, data)

    time.sleep(1)
    return True
