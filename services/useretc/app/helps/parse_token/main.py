
import pathlib

CWD = pathlib.Path(__file__).parent.absolute().resolve()

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.utils.decorator import user_type
from app.utils.logging import log
from opensarlab.auth import encryptedjwt

template_path = CWD / "frontend"

router = APIRouter(
    prefix="/parse/token",
)

# Parse Encrypted JWT Token
@router.get('/', response_class=HTMLResponse)
@user_type('admin')
async def get_parse_token_page(request: Request):
    with open(template_path / "parse.html", 'r') as f:
        html_content = f.read()
    return HTMLResponse(content=html_content, status_code=200)

@router.post('/decrypt')
@user_type('admin')
async def get_parsed_token(request: Request):
    try:
        payload = await request.json()
        token = payload['token']
        result = encryptedjwt.decrypt(token) 
    except Exception as e:
        result = e
    return result