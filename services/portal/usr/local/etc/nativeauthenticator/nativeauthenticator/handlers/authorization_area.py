from .extras.base import LocalBase
from .extras.decorators import admin_users_scope
from .extras.orm import UserInfo


class AuthorizationAreaHandler(LocalBase):
    """Responsible for rendering the /hub/authorize page."""

    @admin_users_scope
    async def get(self):
        html = await self.render_template(
            "authorization-area.html",
            ask_email=self.authenticator.ask_email_on_signup,
            users=self.db.query(UserInfo).all(),
        )
        self.finish(html)
