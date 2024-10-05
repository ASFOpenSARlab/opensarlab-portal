
import pathlib

CWD = pathlib.Path(__file__).parent.absolute().resolve()

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
import httpx

from app.utils.decorator import user_type
from app.utils.logging import log
from opensarlab.auth import encryptedjwt

template_path = CWD / "frontend"

router = APIRouter(
    prefix="/bulk/email",
)

# Send bulk emails
@router.get('/', response_class=HTMLResponse)
@user_type('admin')
async def bulk_email_page(request: Request):
    with open(template_path / "bulk.html", 'r') as f:
        html_content = f.read()
    return HTMLResponse(content=html_content, status_code=200)

@router.post('/send')
@user_type('admin')
async def bulk_email_send(request: Request):
    try:
        payload = await request.json()
        to_address = payload['toAddress']
        bcc_address = payload['bccAddress']
        html_body = payload['htmlBody']
        subject = payload['subject']

        email = {
            "to":{
                "email": str(to_address).split(",")
            },
            "from": {
                "username": "osl-admin"
            },
            "bcc": {
                "email": str(bcc_address).split(",")
            },
            "subject": str(subject),
            "html_body": str(html_body)

        }

        data = encryptedjwt.encrypt(email)
        url = "http://127.0.0.1/user/email/send"
        async with httpx.AsyncClient() as client:
            response = await client.post(url=url, data=data, timeout=15)
            response.raise_for_status
            return response.text

    except Exception as e:
        log.error(f"{e}")
        raise Exception(e)
