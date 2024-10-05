from .extras.base import LocalBase
from .extras.decorators import admin_users_scope
from .extras.orm import UserInfo


class Reset2FAAdminHandler(LocalBase):
    @admin_users_scope
    async def get(self, slug):
        UserInfo.reset_2fa(self.db, slug)
        self.redirect(self.hub.base_url + "authorize#" + slug)
