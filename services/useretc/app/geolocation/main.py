
import pathlib
from urllib.parse import unquote
import io
import datetime

CWD = pathlib.Path(__file__).parent.absolute().resolve()

import pandas as pd
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from .backend import crud
from app.utils.decorator import user_type
from app.utils.logging import log
from app.database.get_db import get_db
from opensarlab.auth import encryptedjwt

router = APIRouter(
    prefix="/geolocation",
)

@router.get('/all')
@user_type('admin')
async def get_all_geo_data(request: Request, format: str = 'text', db: Session = Depends(get_db)):
    """
    Serve raw data of all geolocation data
    """
    data = await crud.get_all_geodata_for_all(db=db)
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

@router.get('/latest/username/{username}')
async def get_user_geo_data(request: Request, username: str, db_session: Session = Depends(get_db)):
    username = unquote(username)
    data = await crud.get_latest_geodata_for_username(username, db=db_session)
    return encryptedjwt.encrypt(data)

@router.post('/update')
async def post_user_geo_data(request: Request, db_session: Session = Depends(get_db)):
    request_data = await request.body()
    data = encryptedjwt.decrypt(request_data)
    await crud.add_geodata(data, db=db_session)
