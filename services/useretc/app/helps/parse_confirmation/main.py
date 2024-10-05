
import pathlib
import re

CWD = pathlib.Path(__file__).parent.absolute().resolve()

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from opensarlab.auth import encryptedjwt

from app.utils.decorator import user_type
from app.utils.logging import log
from app.utils.crypto.signing import Signer, BadSignature

template_path = CWD / "frontend"

router = APIRouter(
    prefix="/parse/confirmation",
)

# Parse Encoded confirmation link from use signup and password reset
@router.get('/', response_class=HTMLResponse)
@user_type('admin')
async def get_parse_confirmation_page(request: Request):
    with open(template_path / "parse.html", 'r') as f:
        html_content = f.read()
    return HTMLResponse(content=html_content, status_code=200)

@router.post('/decrypt')
@user_type('admin')
async def get_parsed_confirmation(request: Request):
    try:
        payload = await request.json()
        token = payload['token']

        # Do decoding here
        sso_token = encryptedjwt.get_sso_token_from_file().strip()
        secret_key = sso_token.encode('utf-8').hex()[0:10]

        s = Signer(secret_key, salt='andpeppersinghiphop')
        try:
            obj = s.unsign_object(token)
        except BadSignature as e:
            raise ValueError(e)

        result = str(obj)

        # obsucate passwords
        result = re.sub(r"(?<='password'\: ').*(?=',)", lambda match: '*****', result)

    except Exception as e:
        result = e
    return result