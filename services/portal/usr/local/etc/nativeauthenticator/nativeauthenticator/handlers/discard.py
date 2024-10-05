from .extras.base import LocalBase
from .extras.decorators import admin_users_scope


class DiscardHandler(LocalBase):
    """Responsible for the /hub/discard/[someusername] page
    that immediately redirects after discarding a user
    from the database."""

    @admin_users_scope
    async def get(self, user_name):
        user = self.authenticator.get_user(user_name)
        if user is not None:
            if not user.is_authorized:
                # Delete user from NativeAuthenticator db table (users_info)
                user = type("User", (), {"name": user_name})
                self.authenticator.delete_user(user)

                # Also delete user from jupyterhub registry, if present
                if self.users.get(user_name) is not None:
                    self.users.delete(user_name)

        self.redirect(self.hub.base_url + "authorize")
