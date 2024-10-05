from functools import wraps

from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from app.utils import helps

def user_type(*allowed_users):
    def inner_decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):

            # Since the decorator wraps around a fastapi web object, it will always have a request object
            request = kwargs.get('request')
            user_info = await helps.get_user_info_from_username_cookie(request)

            if not user_info:
                return RedirectResponse('/portal/hub/logout')

            auth_username = user_info.get('name', 'None')
            auth_roles = user_info.get('roles', 'None')
            requested_username_from_url = kwargs.get('username', None)

            # If the `username` is used as an url arg, check to see if that username matches the cookie.
            # We want to make sure that users can only see their data if the `username` is in the path.
            # If not, then any authenticated user can access the url
            allowed_requested_username_from_url = True
            if requested_username_from_url and requested_username_from_url != auth_username:
                allowed_requested_username_from_url = False

            if ('admin' in allowed_users and 'admin' in auth_roles) or ('user' in allowed_users and allowed_requested_username_from_url):
                return await func(*args, **kwargs)

            raise HTTPException(status_code=401)

        return wrapper
    return inner_decorator
