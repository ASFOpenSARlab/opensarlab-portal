import pathlib
import json
from urllib.parse import quote, unquote

CWD = pathlib.Path(__file__).parent.absolute().resolve()

import httpx
import starlette.status as status
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from jinja2 import Environment, FileSystemLoader

from .backend import crud
from app.utils.decorator import user_type
from app.utils.logging import log
from app.database.get_db import get_db
from opensarlab.auth import encryptedjwt

template_path = CWD / "frontend"

env = Environment(
    loader=FileSystemLoader(template_path),
    autoescape=True
)

router = APIRouter(
    prefix="/access",
)

@router.get('/admin', response_class=HTMLResponse)
@user_type('admin')
async def get_user_access_admin_page(request: Request, db_session: Session = Depends(get_db)):
    lab_short_names = await crud.get_lab_short_names(db=db_session)
    
    lab_data = []
    profiles = []
    for lab_short_name in lab_short_names:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"http://127.0.0.1/lab/{quote(lab_short_name)}/hub/possible-profiles", 
                    timeout=15
                )
            resp = encryptedjwt.decrypt(resp.text)
            resp = json.loads(resp)
            profiles = resp['profiles'] 
        except Exception as e:
            log.error(f"Problem with getting possible-profiles: {e}")

        lab_data.append({
            "short_name": lab_short_name,
            "profiles": profiles
        })

    template = env.get_template("sheet.html.j2")
    html_content = template.render(lab_data=lab_data)

    return HTMLResponse(content=html_content, status_code=200)

@router.get('/lab/{lab_short_name}')
@user_type('admin')
async def get_user_access_data_by_lab(request: Request, lab_short_name: str, db_session: Session = Depends(get_db)) -> list:
    lab_short_name = unquote(lab_short_name)
    data = await crud.get_data_for_lab(lab_short_name, db=db_session)
    return data

@router.post('/lab/{lab_short_name}')
@user_type('admin')
async def post_user_access_data_by_lab(request: Request, lab_short_name: str, db_session: Session = Depends(get_db)) -> None:
    lab_short_name = unquote(lab_short_name)
    form = await request.form()
    data = json.loads(dict(form)['data'])
    await crud.update_data_for_lab(lab_short_name, data, db=db_session)
    return

@router.get('/username/{username}')
async def get_user_access_data_by_username(request: Request, username: str, db_session: Session = Depends(get_db)) -> str:
    username = unquote(username)
    user_data = await crud.get_data_for_username(username, db=db_session)
    return encryptedjwt.encrypt(user_data)
