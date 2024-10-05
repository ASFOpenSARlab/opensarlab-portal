from tornado import web

from .extras.base import LocalBase


class ChangePasswordHandler(LocalBase):
    """Responsible for rendering the /hub/change-password page where users can change
    their own password. Both on GET requests, when simply navigating to the site,
    and on POST requests, with the data to change the password attached."""

    @web.authenticated
    async def get(self):
        """Rendering on GET requests ("normal" visits)."""

        user = await self.get_current_user()
        html = await self.render_template(
            "change-password.html",
            user_name=user.name,
        )
        self.finish(html)

    @web.authenticated
    async def post(self):
        """Rendering on POST requests (requests with data attached)."""

        user = await self.get_current_user()
        old_password = self.get_body_argument("old_password", strip=False)
        new_password = self.get_body_argument("new_password", strip=False)
        confirmation = self.get_body_argument("new_password_confirmation", strip=False)

        correct_password_provided = self.authenticator.get_user(
            user.name
        ).is_valid_password(old_password)

        new_password_matches_confirmation = new_password == confirmation

        if not correct_password_provided:
            alert = "alert-danger"
            message = "Your current password was incorrect. Please try again."
        elif not new_password_matches_confirmation:
            alert = "alert-danger"
            message = (
                "Your new password didn't match the confirmation. Please try again."
            )
        else:
            success = self.authenticator.change_password(user.name, new_password)
            if success:
                alert = "alert-success"
                message = "Your password has been changed successfully!"
            else:
                alert = "alert-danger"
                minimum_password_length = self.authenticator.minimum_password_length
                # Error if minimum password length is > 0.
                if minimum_password_length > 0:
                    message = (
                        "Something went wrong!\n"
                        "Be sure your new password has at least"
                        f" {minimum_password_length} characters "
                        "and is not too common."
                    )
                # Error if minimum password length is 0.
                else:
                    message = (
                        "Something went wrong!\n"
                        "Be sure your new password is not too common."
                    )

        html = await self.render_template(
            "change-password.html",
            user_name=user.name,
            result_message=message,
            alert=alert,
        )
        self.finish(html)
