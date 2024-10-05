from datetime import datetime
from datetime import date
from datetime import timezone as tz

from tornado import web
import httpx

from nativeauthenticator.crypto.signing import Signer, BadSignature

from .extras.base import LocalBase


class ForgetPasswordHandler(LocalBase):
    """Responsible for rendering the /hub/forget-password page, validating input to that
    page, sending reset links to users, and giving accurate feedback to users."""

    async def get(self):
        """Rendering on GET requests ("normal" visits)."""

        # 404 if users aren't allowed to reset password externally.
        if (
            not self.authenticator.enable_forget_password
            or not self.authenticator.ask_email_on_signup
        ):
            raise web.HTTPError(404)

        # Render page with relevant settings from the authenticator.
        html = await self.render_template(
            "forget-password.html",
            recaptcha_key=self.authenticator.recaptcha_key,
        )
        self.finish(html)

    def get_result_message(
        self,
        assume_user_is_human,
        confirmation_matches,
        minimum_password_length,
        password_long_enough,
    ):
        """Helper function to discern exactly what message and alert level are
        appropriate to display as a response. Called from post() below."""

        # Error if failed captcha.
        if not assume_user_is_human:
            alert = "alert-danger"
            message = "You failed the reCAPTCHA. Please try again"
        # Error if confirmation didn't match password.
        elif not confirmation_matches:
            alert = "alert-danger"
            message = "Your password did not match the confirmation. Please try again."
        # If password length is too short
        elif minimum_password_length > 0 and not password_long_enough:
            alert = "alert-danger"
            message = f"Your password needs to be {minimum_password_length} characters long. Please try again."
        else:
            # Default response if nothing goes wrong.
            alert = "alert-info"
            message = "Check your email for an URL link to authorize your password change. The link will expire in 60 minutes. If you haven't received an email within 10 minutes, check your email spam folder."

        return alert, message

    async def post(self):
        """Rendering on POST requests)."""

        # 404 if users aren't allowed to reset password externally.
        if (
            not self.authenticator.enable_forget_password
            or not self.authenticator.ask_email_on_signup
        ):
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
            password = self.get_body_argument("new_password", strip=False)
            confirmation = self.get_body_argument(
                "new_password_confirmation", strip=False
            )

            confirmation_matches = password == confirmation
            minimum_password_length = self.authenticator.minimum_password_length
            password_long_enough = len(password) >= minimum_password_length

            # Call helper function from above for precise alert-level and message.
            alert, message = self.get_result_message(
                assume_user_is_human,
                confirmation_matches,
                minimum_password_length,
                password_long_enough,
            )

            user_info = {"username": ""}
            try:
                user_info = {
                    "username": str(
                        self.get_body_argument("username", strip=False)
                    ).lower(),
                    "password": self.get_body_argument("new_password", strip=False),
                }
                user_from_db = self.authenticator.get_user(user_info["username"])
                if not user_from_db and user_from_db.email:
                    raise

                url = self.authenticator.generate_password_reset_url(payload=user_info)
            except:
                alert = "alert-danger"
                message = f"User {user_info['username']} does not exist."

            if alert == "alert-info":  # Not error or warning
                self.authenticator.send_password_reset_email(
                    user_from_db.email, url, user_info["username"]
                )

        html = await self.render_template(
            "forget-password.html",
            result_message=message,
            alert=alert,
            recaptcha_key=self.authenticator.recaptcha_key,
        )
        self.finish(html)
