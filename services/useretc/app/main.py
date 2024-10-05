from fastapi import FastAPI

from profile.main import router as profile_router
from notifications.main import router as notifications_router
from access.main import router as access_router
from quota.main import router as quota_router
from email_service.main import router as email_router
from helps.main import router as helps_router
from geolocation.main import router as geolocation_router
from request.main import router as request_router

app = FastAPI(root_path="/user")

app.include_router(profile_router)
app.include_router(notifications_router)
app.include_router(access_router)
app.include_router(quota_router)
app.include_router(email_router)
app.include_router(helps_router)
app.include_router(geolocation_router)
app.include_router(request_router)
