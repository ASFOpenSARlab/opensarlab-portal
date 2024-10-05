import re

import httpx
from tornado import web

from .extras.base import LocalBase


class SignUpHandler(LocalBase):
    """Responsible for rendering the /hub/signup page, validating input to that
    page, account creation and giving accurate feedback to users."""

    async def get(self):
        """Rendering on GET requests ("normal" visits)."""

        # 404 if signup is not currently open.
        if not self.authenticator.enable_signup:
            raise web.HTTPError(404)

        # Render page with relevant settings from the authenticator.
        html = await self.render_template(
            "signup.html",
            ask_email=self.authenticator.ask_email_on_signup,
            two_factor_auth_allow=self.authenticator.allow_2fa,
            two_factor_auth_require=self.authenticator.require_2fa,
            recaptcha_key=self.authenticator.recaptcha_key,
            tos=self.authenticator.tos,
        )
        self.finish(html)

    def get_result_message(
        self,
        user,
        assume_user_is_human,
        username_already_taken,
        confirmation_matches,
        user_is_admin,
    ):
        """Helper function to discern exactly what message and alert level are
        appropriate to display as a response. Called from post() below."""

        # Error if failed captcha.
        if not assume_user_is_human:
            alert = "alert-danger"
            message = "You failed the reCAPTCHA. Please try again"
        # Error if username is taken.
        elif username_already_taken:
            alert = "alert-danger"
            message = (
                "Something went wrong!\nIt appears that this "
                "username is already in use. Please try again "
                "with a different username."
            )
        # Error if confirmation didn't match password.
        elif not confirmation_matches:
            alert = "alert-danger"
            message = "Your password did not match the confirmation. Please try again."
        # Error if user creation was not successful.
        elif not user:
            alert = "alert-danger"
            minimum_password_length = self.authenticator.minimum_password_length
            # Error if minimum password length is > 0.
            if minimum_password_length > 0:
                message = f"""
                    Something went wrong!
                    Be sure your
                    1. Username starts and ends with an alphanumeric character.
                    2. Other username characters are alphanumeric, '.', '_', or '-'.
                    3. Username does not contain the phrase 'admin'.
                    4. Password has at least {minimum_password_length} characters and is not too common.
                    """
            # Error if minimum password length is 0.
            else:
                message = f"""
                    Something went wrong!
                    Be sure your
                    1. Username starts and ends with an alphanumeric character.
                    2. Other username characters are alphanumeric, '.', '_', or '-'.
                    3. Username does not contain the phrase 'admin'.
                    4. Password has at least {minimum_password_length} characters and is not too common.
                    """
        # If user creation went through & open-signup is enabled, success.
        # If user creation went through & the user is an admin, also success.
        elif (user is not None) and (self.authenticator.open_signup or user_is_admin):
            alert = "alert-success"
            message = (
                "The signup was successful! You can now go to "
                "the home page and log in to the system."
            )
        else:
            # Default response if nothing goes wrong.
            alert = "alert-info"
            message = "Your information has been sent to the admin."

            if (user is not None) and user.login_email_sent:
                message = "The signup was successful! Check your email to authorize your access.The link will expire in 60 minutes. If you haven't received an email within 10 minutes, check your email spam folder."

        return alert, message

    async def post(self):
        """Rendering on POST requests (signup visits with data attached)."""

        # 404 if users aren't allowed to sign up.
        if not self.authenticator.enable_signup:
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

        # Collect various information for precise (error) messages.
        password = self.get_body_argument("signup_password", strip=False)
        confirmation = self.get_body_argument(
            "signup_password_confirmation", strip=False
        )
        confirmation_matches = password == confirmation

        if assume_user_is_human:
            user_info = {
                "username": self.get_body_argument("username", strip=False),
                "password": self.get_body_argument("signup_password", strip=False),
                "email": self.get_body_argument("email", "", strip=False),
                "has_2fa": False,
            }
            username_already_taken = self.authenticator.user_exists(
                user_info["username"]
            )

            username_has_valid_characters = (
                True
                if re.fullmatch(
                    "^[a-zA-Z0-9][a-zA-Z0-9_\.\-/]*[a-zA-Z0-9]$", user_info["username"]
                )
                else False
            )
            username_has_valid_characters = (
                False
                if "admin" in user_info["username"]
                else username_has_valid_characters
            )

            user_is_admin = user_info["username"] in self.authenticator.admin_users

            if (
                not username_already_taken
                and confirmation_matches
                and username_has_valid_characters
            ):
                user = self.authenticator.create_user(**user_info)
            else:
                user = None
        else:
            username_already_taken = False
            user = None

        # Call helper function from above for precise alert-level and message.
        alert, message = self.get_result_message(
            user,
            assume_user_is_human,
            username_already_taken,
            confirmation_matches,
            user_is_admin,
        )

        html = await self.render_template(
            "signup.html",
            ask_email=self.authenticator.ask_email_on_signup,
            result_message=message,
            alert=alert,
            two_factor_auth=self.authenticator.allow_2fa
            or self.authenticator.require_2fa,
            two_factor_auth_require=self.authenticator.require_2fa,
            recaptcha_key=self.authenticator.recaptcha_key,
            tos=self.authenticator.tos,
        )
        self.finish(html)
