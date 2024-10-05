from tornado import web
import httpx

from nativeauthenticator.crypto.signing import Signer, BadSignature

from .extras.base import LocalBase


class ResetMFADeviceHandler(LocalBase):
    """Responsible for rendering the /hub/reset-mfa page, validating input to that
    page, sending reset links to users, and giving accurate feedback to users."""

    async def get(self):
        """Rendering on GET requests ("normal" visits)."""

        # 404 if users aren't allowed to reset mfa externally.
        if not self.authenticator.enable_reset_mfa:
            raise web.HTTPError(404)

        # Render page with relevant settings from the authenticator.
        html = await self.render_template(
            "reset_mfa_device.html",
            recaptcha_key=self.authenticator.recaptcha_key,
        )
        self.finish(html)

    def get_result_message(
        self,
        assume_user_is_human,
    ):
        """Helper function to discern exactly what message and alert level are
        appropriate to display as a response. Called from post() below."""

        # Error if failed captcha.
        if not assume_user_is_human:
            alert = "alert-danger"
            message = "You failed the reCAPTCHA. Please try again"
        else:
            # Default response if nothing goes wrong.
            alert = "alert-info"
            message = "Check your email for a URL link to authorize your MFA device reset. The link will expire in 60 minutes. If you haven't received an email within 10 minutes, check your email spam folder."

        return alert, message

    async def post(self):
        """Rendering on POST requests)."""

        # 404 if users aren't allowed to reset mfa externally.
        if not self.authenticator.enable_reset_mfa:
            raise web.HTTPError(404)

        if not self.authenticator.recaptcha_key:
            # If this option is not enabled, we proceed under
            # the assumption that the user is human.
            assume_user_is_human = True
        else:
            # If this option _is_ enabled, we assume the user
            # is _not_ human until we know otherwise.
            assume_user_is_human = False

            recaptcha_response = self.get_body_argument(
                "g-recaptcha-response", strip=True
            )
            if recaptcha_response != "":
                data = {
                    "secret": self.authenticator.recaptcha_secret,
                    "response": recaptcha_response,
                }
                siteverify_url = "https://www.google.com/recaptcha/api/siteverify"
                async with httpx.AsyncClient() as client:
                    validation_status = await client.post(
                        siteverify_url, data=data, timeout=1
                    )

                assume_user_is_human = validation_status.json().get("success")

                # Logging result
                if assume_user_is_human:
                    self.authenticator.log.info("Passed reCaptcha")
                else:
                    self.authenticator.log.error("Failed reCaptcha")

        if assume_user_is_human:
            # Call helper function from above for precise alert-level and message.
            alert, message = self.get_result_message(
                assume_user_is_human,
            )

            user_info = {"username": ""}
            user_from_db = None
            try:
                user_info = {
                    "username": str(
                        self.get_body_argument("username", strip=False)
                    ).lower(),
                    "password": self.get_body_argument("password", strip=False),
                }
                user_from_db = self.authenticator.get_user(user_info["username"])
                if not user_from_db and user_from_db.email:
                    raise

                url = self.authenticator.generate_mfa_device_reset_url(
                    payload=user_info
                )
            except Exception:
                alert = "alert-danger"
                message = f"User {user_info['username']} does not exist."

            if user_from_db is not None and not user_from_db.is_valid_password(
                user_info["password"]
            ):
                alert = "alert-danger"
                message = f"Password for user {user_info['username']} is incorrect."

            if alert == "alert-info":  # Not error or warning
                self.authenticator.send_mfa_device_reset_email(
                    user_from_db.email, url, user_info["username"]
                )

        html = await self.render_template(
            "reset_mfa_device.html",
            result_message=message,
            alert=alert,
            recaptcha_key=self.authenticator.recaptcha_key,
        )
        self.finish(html)
