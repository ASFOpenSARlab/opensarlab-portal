from .extras.base import LocalBase
from .extras.decorators import admin_users_scope
from .extras.orm import UserInfo


class ToggleAuthorizationHandler(LocalBase):
    """Responsible for the authorize/[someusername] page,
    which immediately redirects after toggling the
    respective user's authorization status."""

    @admin_users_scope
    async def get(self, slug):
        UserInfo.change_authorization(self.db, slug)
        self.redirect(self.hub.base_url + "authorize#" + slug)
