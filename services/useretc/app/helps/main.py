import pathlib

CWD = pathlib.Path(__file__).parent.absolute().resolve()

from fastapi import APIRouter

from .bulk_email.main import router as bulk_email_router
from .parse_token.main import router as parse_token_router
from .parse_confirmation.main import router as parse_confirmation_router

router = APIRouter(
    prefix="/helps",
)

router.include_router(bulk_email_router)
router.include_router(parse_token_router)
router.include_router(parse_confirmation_router)
