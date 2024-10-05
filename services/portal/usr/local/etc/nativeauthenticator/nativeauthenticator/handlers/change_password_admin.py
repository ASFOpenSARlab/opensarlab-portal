from tornado import web

from .extras.base import LocalBase
from .extras.decorators import admin_users_scope


class ChangePasswordAdminHandler(LocalBase):
    """Responsible for rendering the /hub/change-password/[someusername] page where
    admins can change any user's password. Both on GET requests, when simply
    navigating to the site, and on POST requests, with the data to change the
    password attached."""

    @admin_users_scope
    async def get(self, user_name):
        """Rendering on GET requests ("normal" visits)."""

        if not self.authenticator.user_exists(user_name):
            raise web.HTTPError(404)

        html = await self.render_template(
            "change-password-admin.html",
            user_name=user_name,
        )
        self.finish(html)

    @admin_users_scope
    async def post(self, user_name):
        """Rendering on POST requests (requests with data attached)."""

        new_password = self.get_body_argument("new_password", strip=False)
        confirmation = self.get_body_argument("new_password_confirmation", strip=False)

        new_password_matches_confirmation = new_password == confirmation

        if not new_password_matches_confirmation:
            alert = "alert-danger"
            message = (
                "The new password didn't match the confirmation. Please try again."
            )
        else:
            success = self.authenticator.change_password(user_name, new_password)
            if success:
                alert = "alert-success"
                message = f"The password for {user_name} has been changed successfully"
            else:
                alert = "alert-danger"
                minimum_password_length = self.authenticator.minimum_password_length
                # Error if minimum password length is > 0.
                if minimum_password_length > 0:
                    message = (
                        "Something went wrong!\nBe sure the new password "
                        f"for {user_name} has at least {minimum_password_length} "
                        "characters and is not too common."
                    )
                # Error if minimum password length is 0.
                else:
                    message = (
                        "Something went wrong!\nBe sure the new password "
                        f"for {user_name} is not too common."
                    )

        html = await self.render_template(
            "change-password-admin.html",
            user_name=user_name,
            result_message=message,
            alert=alert,
        )
        self.finish(html)
