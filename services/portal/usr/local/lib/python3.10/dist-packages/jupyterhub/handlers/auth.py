import json
import traceback
from ipaddress import ip_address as ipa

from tornado import web
from tornado.escape import json_decode
from .base import BaseHandler

from portallib.user import PortalUser
from opensarlab.auth import encryptedjwt

import logging


class AuthHandler(BaseHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def _get_data(self, username: str, update_ip_location: bool = False) -> dict:
        """
        return:

        {
            'groups': list[str],
            'admin': bool,
            'kind': 'user',
            'roles': ['user', 'admin'],
            'name': '{username}',
            'has_2fa': 1 || 0,
            'force_user_profile_update': bool,
            'ip_country_status': 'unrestricted' || 'limited' || 'prohibited',
            'country_code': str,
            'lab_access': {
                '{lab_short_name}': {
                    'lab_profiles': list[str],
                    'time_quota': None,
                    'lab_country_status': 'unrestricted' || 'limited',
                    'can_user_access_lab': bool,
                    'can_user_see_lab_card': bool,
                },
            },
            'access': [
                {
                    '{lab_short_name}': {
                        'lab_profiles': list[str],
                    }
                }
            ]
        }

        """
        portal_user = PortalUser(username)

        if update_ip_location:
            ## If X-localhost is 'set', always update the geolocation.
            ## Otherwise, if ip_add is within any private network, don't update
            ## This meant to be used from a browser request. Otherwise, non-person IPs will be picked up.

            portal_ip_country_status = self.request.headers.get(
                "X-Portal-Ip-Country-Status", "unknown"
            )
            country_code = self.request.headers.get("X-Geoip2-Iso-Code", "ZZ")
            ip_add = self.request.headers.get("X-Real-IP", None)
            is_localdev = self.request.headers.get("X-localdev", None)

            if ipa(ip_add).is_private and not is_localdev:
                self.log.warning(
                    f"IP Address {ip_add} belonging to {username=} is private and X-LocalDev header is {is_localdev}. Not updating DB."
                )
            else:
                self.log.warning(
                    f"Update entry to geolocation DB table: {username=}, {portal_ip_country_status=}, {country_code=}, {ip_add=}, {is_localdev=}"
                )
                await portal_user.update_user_geolocation_with_geolocation_api(
                    portal_ip_country_status, country_code, ip_add
                )

        hub_data: dict = await portal_user.get_user_data_from_hub_api()

        user_profile: dict = await portal_user.get_user_profile_data_from_profile_api()

        hub_data["force_user_profile_update"] = user_profile.get("force_update", True)

        # Always grab latest ip info for username
        geolocation_data: dict = (
            await portal_user.get_latest_user_geolocation_from_geolocation_api()
        )
        country_code: str = geolocation_data.get("country_code", None)
        hub_data["country_code"] = country_code

        hub_data["lab_access"] = await portal_user.get_user_data_from_access_api(
            country_code
        )

        if not hub_data["has_2fa"]:
            hub_data["lab_access"] = {}

        ## TODO: Remove this when all the lab deployments no longer use 'access'
        hub_data["access"] = [
            {k: v}
            for k, v in hub_data["lab_access"].items()
            if v["can_user_access_lab"] == True
        ]
        ####

        logging.warn(f"************************------------- {hub_data}")

        return hub_data

    async def post(self):
        """
        *For non-browser user*

        Get user data for current JupyterHub user.
        """

        try:
            data = {}

            request_body = json_decode(self.request.body)
            username = request_body["username"]
            if not username:
                user = await self.get_current_user()
                if not user:
                    raise Exception("Auth: portal user: Username not given")
                username = user.name

            if username:
                try:
                    data = await self._get_data(
                        username=username, update_ip_location=False
                    )
                except Exception as e:
                    raise Exception(f"Auth: portal user: {e}")

            if data:
                data = encryptedjwt.encrypt(data)
                self.write(json.dumps({"data": data, "message": "OK"}))

            else:
                self.write(json.dumps({"data": "", "message": "No data"}))

        except Exception as e:
            self.write(
                json.dumps(
                    {
                        "data": "",
                        "message": f"ERROR: {str(e)}, {traceback.format_exc()}",
                    }
                )
            )

    async def get(self):
        """
        *For browser use.*

        Get user info of current JupyterHub user.

        If next_url redirect path is not given, redirect to base url.
        If user does not exist, redirect to login page.
        If user data is bad, throw 500
        Create 'jupyterhub-portal-jwt' cookie.
        """
        next_url = self.get_argument("next_url", "WHERE_ARE_YOU_GOING")
        next_url = web.escape.url_escape(next_url)

        if not next_url:
            self.log.error("Auth: No argument 'next_url' given.")
            self.redirect(self.base_url, permanent=False)
            return

        user = await self.get_current_user()

        if not user:
            next = web.escape.url_escape(f"/portal/hub/auth?next_url={next_url}")
            self.log.error(f"Auth: No 'user' found. Redirecting to {next}")
            self.redirect(f"/portal/hub/login?next={next}", permanent=False)
            return

        username = user.name

        if not username:
            next = web.escape.url_escape(f"/portal/hub/auth?next_url={next_url}")
            self.log.error(f"Auth: No 'username' found. Redirecting to {next}")
            self.redirect(f"/portal/hub/login?next={next}", permanent=False)
            return

        try:
            data = await self._get_data(username=username, update_ip_location=True)
        except Exception as e:
            self.log.error(f"Auth: portal user: {e}")
            raise web.HTTPError(500, "Bad user data")

        try:
            jwt_token = encryptedjwt.encrypt(data)
            if not jwt_token:
                self.log.error("Auth: No jwt created.")
                self.redirect(self.base_url, permanent=False)
                return
        except Exception as e:
            self.log.error(e)
            raise web.HTTPError(500, "Bad JWT")

        try:
            self._set_cookie(
                f"jupyterhub-portal-jwt",
                jwt_token,
                encrypted=False,
                path="/",
                expires_days=7,
            )
        except Exception as e:
            self.log.error(e)
            raise web.HTTPError(403, "Bad jwt cookie value")

        next_url = web.escape.url_unescape(next_url)
        self.redirect(next_url)


default_handlers = [(r"/auth", AuthHandler)]
