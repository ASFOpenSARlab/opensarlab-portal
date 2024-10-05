import os
import json
from ipaddress import ip_address as ipa

import yaml
from tornado import web
from tornado.httpclient import AsyncHTTPClient

from .base import BaseHandler

from portallib.user import PortalUser
from portallib.misc import is_deployment_healthy
from opensarlab.auth import encryptedjwt


class My401Exception(Exception):
    pass


class My500Exception(Exception):
    pass


class PortalHomeHandler(BaseHandler):
    """Render the user's home page."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.portal_domain = os.environ.get("OPENSCIENCELAB_PORTAL_DOMAIN", "127.0.0.1")
        if not self.portal_domain:
            raise My401Exception("No portal domain")

        # Get config lab info for page
        with open("/usr/local/etc/labs.yaml", "r") as f:
            lab_config = yaml.load(f, Loader=yaml.FullLoader)
        self.all_labs_in_config = lab_config["labs"]

    @web.authenticated
    async def get(self):

        user = await self.get_current_user()
        if not user:
            self.redirect(self.base_url, permanent=False)
            return
        username = user.name

        portal_ip_country_status = self.request.headers.get(
            "X-Portal-Ip-Country-Status", "unknown"
        )
        country_code = self.request.headers.get("X-Geoip2-Iso-Code", "ZZ")
        ip_add = self.request.headers.get("X-Real-IP", None)
        is_localdev = self.request.headers.get("X-localdev", None)

        pu = PortalUser(username)

        ## If X-localhost is 'set', always update the geolocation.
        ## Otherwise, if ip_add is within any private network, don't update
        ## This meant to be used from a browser request. Otherwise, non-person IPs will be picked up.
        if ipa(ip_add).is_private and not is_localdev:
            self.log.warning(
                f"IP Address {ip_add} belonging to {username=} is private and X-LocalDev header is {is_localdev}. Not updating DB."
            )
        else:
            self.log.warning(
                f"Update entry to geolocation DB table: {username=}, {portal_ip_country_status=}, {country_code=}, {ip_add=}, {is_localdev=}"
            )
            await pu.update_user_geolocation_with_geolocation_api(
                portal_ip_country_status, country_code, ip_add
            )

        ###########################

        # Get updated user data from portal
        try:
            body = json.dumps({"username": f"{username}"})
            response = await AsyncHTTPClient().fetch(
                f"{self.portal_domain}/portal/hub/auth", body=body, method="POST"
            )

            if not response.code == 200:
                self.log.error(
                    f"Auth response code is not 200. Code: {response.code}, {response['message']}"
                )
                raise My401Exception()

            response = json.loads(response.body)
            if "ERROR" in response["message"]:
                self.log.error(f"{response['message']}")
                raise My401Exception()

        except Exception as e:
            self.log.error(f"Something went wrong with retrieving authentication. {e}")
            raise My401Exception()

        try:
            encrypted_jwt_data = response["data"]
            user_data = encryptedjwt.decrypt(encrypted_jwt_data)
        except Exception as e:
            self.log.error(f"PortalAuth Login JWT decryption went wrong: {e}")
            raise My401Exception(
                "Something went wrong with jwt authentication. Contact the administrator."
            )

        # If user profile is not set or is set for update, redirect to profile page
        if user_data.get("force_user_profile_update", False):
            self.redirect(f"/user/profile/show/{username}", permanent=False)
            return

        mylabs = []

        user_data_access: dict = user_data.get("lab_access", {})
        config_labs = {lab["short_name"]: lab for lab in self.all_labs_in_config}

        is_global_lab_country_status_limited = False
        all_lab_card_seen = []

        for config_lab_short_name in config_labs:
            config_lab_meta = config_labs.get(config_lab_short_name, {})

            access_lab_meta: dict = user_data_access.get(config_lab_short_name, {})
            can_user_see_lab_card: bool = access_lab_meta.get(
                "can_user_see_lab_card", False
            )
            can_user_access_lab: bool = access_lab_meta.get(
                "can_user_access_lab", False
            )
            lab_country_status: str = access_lab_meta.get(
                "lab_country_status", "unknown"
            )

            if lab_country_status in ["limited", "prohibited"]:
                is_global_lab_country_status_limited = True

            is_lab_deployment_healthy: bool = await is_deployment_healthy(
                config_lab_short_name
            )
            all_lab_card_seen.append(can_user_see_lab_card)

            if (
                lab_country_status in ("unrestricted", "limited")
                and can_user_see_lab_card
            ):
                mylabs.append(
                    {
                        "short_lab_name": config_lab_short_name,
                        "description": config_lab_meta.get("description", "Welcome!!"),
                        "friendly_name": config_lab_meta.get(
                            "friendly_name", "FRIENDLY_LAB_NAME_HERE"
                        ),
                        "goto_button_url": f"/lab/{config_lab_short_name}/hub/home",
                        "is_lab_deployment_healthy": is_lab_deployment_healthy,
                        "about_page_url": config_lab_meta.get("about_page_url", None),
                        "logo": config_lab_meta.get("logo", None),
                        "about_page_button_label": config_lab_meta.get(
                            "about_page_button_label", "Info"
                        ),
                        "can_user_access_lab": can_user_access_lab,
                        "can_user_see_lab_card": can_user_see_lab_card,
                    }
                )

        country_code = user_data.get("country_code", "ZZ")
        is_mfa_enabled = user_data.get("has_2fa", False)

        html = await self.render_template(
            "portal.html.j2",
            mylabs=mylabs,
            username=username,
            country_code=country_code,
            is_global_lab_country_status_limited=is_global_lab_country_status_limited,
            is_mfa_enabled=is_mfa_enabled,
        )
        self.finish(html)


default_handlers = [(r"/home", PortalHomeHandler)]
