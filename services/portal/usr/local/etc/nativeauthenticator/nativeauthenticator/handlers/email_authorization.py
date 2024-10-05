from datetime import date
from datetime import datetime
from datetime import timezone as tz

from nativeauthenticator.crypto.signing import Signer, BadSignature

from .extras.base import LocalBase
from .extras.orm import UserInfo


class EmailAuthorizationHandler(LocalBase):
    """Responsible for the confirm/[someusername] validation of
    cryptographic URLs for the self-serve-approval feature."""

    async def get(self, slug):
        """Called on GET requests. The slug is given in the URL after /confirm/.
        It's a long-ish string of letters encoding which user this authorization
        link is for and until when it is valid, cryptographically signed by the
        secret key given in the configuration file. This is done to make the
        approval URL not-reverse-engineer-able."""

        self.log.warning(f"Signup confirmation url clicked: {slug}")

        slug_validation_successful = False
        message = "Invalid URL. Pleae contact the administrator."

        if self.authenticator.allow_self_approval_for:
            try:
                data = EmailAuthorizationHandler.validate_slug(
                    slug, self.authenticator.secret_key
                )
                slug_validation_successful = True
            except ValueError as e:
                self.log.error(f"Password authorization slug validation failed. {e}")
            except Exception as e:
                self.log.error(
                    f"Unknown error in validating authorization password slug. {e}"
                )

        if slug_validation_successful:
            username = data["username"]
            self.log.warning(
                f"Signup confirmation validated for username '{username}': {slug}"
            )
            usr = UserInfo.find(self.db, username)

            if not usr.is_authorized:
                UserInfo.change_authorization(self.db, username)
                message = f"{username} has been authorized!"
            else:
                message = f"{username} was already authorized."

        html = await self.render_template(
            "my_message.html",
            message=message,
        )
        self.finish(html)

    # static method so it can be easily tested without initializate the class
    @staticmethod
    def validate_slug(slug, key):
        """This function makes sure the given slug is
        not expired and has a valid signature."""

        s = Signer(key, salt="andpeppersinghiphop")
        try:
            obj = s.unsign_object(slug)
        except BadSignature as e:
            raise ValueError(e)

        # the following it is not supported in earlier versions of python
        # obj["expire"] = datetime.fromisoformat(obj["expire"])

        # format="%Y-%m-%dT%H:%M:%S.%f"
        datestr, timestr = obj["expire"].split("T")

        # before the T
        year_month_day = datestr.split("-")
        dateobj = date(
            int(year_month_day[0]), int(year_month_day[1]), int(year_month_day[2])
        )

        # after the T
        # manually parsing iso-8601 times with a colon in the timezone
        # since the strptime does not support it
        if timestr[-3] == ":":
            timestr = timestr[:-3] + timestr[-2:]
        timeobj = datetime.strptime(timestr, "%H:%M:%S.%f%z").timetz()

        obj["expire"] = datetime.combine(dateobj, timeobj)

        time_now = datetime.now(tz.utc)
        expired = obj["expire"]
        if time_now > expired:
            raise ValueError(
                f"The URL has expired. Now: {time_now}, Expired: {expired}"
            )

        return obj
