from jupyterhub.handlers.login import LoginHandler

from tornado.escape import url_escape
from tornado.httputil import url_concat
from .extras.base import LocalBase


class LoginHandler(LoginHandler, LocalBase):
    """Responsible for rendering the /hub/login page."""

    def _render(self, login_error=None, username=None):
        """For 'normal' rendering."""

        return self.render_template(
            "native-login.html",
            next=url_escape(self.get_argument("next", default="")),
            username=username,
            login_error=login_error,
            custom_html=self.authenticator.custom_html,
            login_url=self.settings["login_url"],
            enable_signup=self.authenticator.enable_signup,
            enable_forget_password=self.authenticator.enable_forget_password,
            enable_reset_mfa=self.authenticator.enable_reset_mfa,
            ask_email_on_signup=self.authenticator.ask_email_on_signup,
            two_factor_auth=self.authenticator.allow_2fa
            or self.authenticator.require_2fa,
            authenticator_login_url=url_concat(
                self.authenticator.login_url(self.hub.base_url),
                {"next": self.get_argument("next", "")},
            ),
        )

    async def post(self):
        """Rendering on POST requests (requests with data attached)."""

        # parse the arguments dict
        data = {}
        for arg in self.request.arguments:
            data[arg] = self.get_argument(arg, strip=False)

        auth_timer = self.statsd.timer("login.authenticate").start()
        user = await self.login_user(data)
        auth_timer.stop(send=False)

        if user:
            # register current user for subsequent requests to user
            # (e.g. logging the request)
            self._jupyterhub_user = user
            self.redirect(self.get_next_url(user))
        else:
            # default error mesage on unsuccessful login
            error = "Invalid username or password."

            # check is user exists and has correct password,
            # and is just not authorised
            username = data["username"]
            user = self.authenticator.get_user(username)
            if user is not None:
                if user.is_valid_password(data["password"]) and not user.is_authorized:
                    error = (
                        f"User {username} has not been authorized "
                        "by an administrator yet."
                    )
                elif user.is_valid_password(data["password"]) and user.has_2fa:
                    error = "Incorrect MFA code."

            html = await self._render(login_error=error, username=username)
            self.finish(html)
