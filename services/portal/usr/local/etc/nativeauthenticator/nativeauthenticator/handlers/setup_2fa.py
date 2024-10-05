import tornado.web
import tornado.escape
import pyotp

from .extras.base import LocalBase
from .mfa import generate_mfa_qrcode


class Setup2FAHandler(LocalBase):
    @tornado.web.authenticated
    async def get(self):
        user = await self.get_current_user()
        authed_user = self.authenticator.get_user(user.name)
        secret = pyotp.random_base32()

        authentication_methods = {
            "Authenticator App": authed_user.has_2fa,
            "Hardware Key": False,
        }

        issuer_name = "OpenScienceLab"
        if "test" in self.request.host:
            issuer_name = issuer_name + "-Test"
        if self.request.host == "localhost" or self.request.host == "127.0.0.1":
            issuer_name = issuer_name + "-Local"

        html = await self.render_template(
            "setup_2fa.html",
            next=tornado.escape.url_escape(self.get_argument("next", default="")),
            username=authed_user.username,
            mfa_configured=authed_user.has_2fa,
            authentication_methods=authentication_methods,
            two_factor_auth_value=secret,
            two_factor_auth_qr_code=generate_mfa_qrcode(
                authed_user.username, secret, issuer_name
            ),
        )
        self.finish(html)

    @tornado.web.authenticated
    async def post(self):
        data = tornado.escape.json_decode(self.request.body)
        update = data.get("update", "")
        new_secret = data.get("secret", "")

        user = await self.get_current_user()
        authed_user = self.authenticator.get_user(user.name)

        if update:
            authed_user.has_2fa = True
            authed_user.otp_secret = new_secret
            self.authenticator.db.commit()
        else:
            self.set_status(400)  # Bad Request

        updated_user = self.authenticator.get_user(user.name)
        update_successful = False
        if updated_user.has_2fa and updated_user.otp_secret == new_secret:
            update_successful = True

        self.set_header("Content-Type", "application/json")
        self.write({"update_successful": update_successful})
