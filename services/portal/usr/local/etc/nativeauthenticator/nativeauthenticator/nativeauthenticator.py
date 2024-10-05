import dbm
import os
import re
from datetime import datetime
from datetime import timedelta
from datetime import timezone as tz
from pathlib import Path
import traceback

import bcrypt
from jupyterhub.auth import Authenticator
from sqlalchemy import inspect
from tornado import web
from traitlets import Bool
from traitlets import Integer
from traitlets import Tuple
from traitlets import Unicode

from nativeauthenticator.crypto.signing import Signer
from .handlers.authorization_area import AuthorizationAreaHandler

from .handlers.setup_2fa import Setup2FAHandler
from .handlers.reset_2fa import Reset2FAAdminHandler
from .handlers.reset_mfa_device import ResetMFADeviceHandler
from .handlers.validate_otp_handler import ValidateOPTHandler
from .handlers.change_password_admin import ChangePasswordAdminHandler
from .handlers.change_password import ChangePasswordHandler
from .handlers.forget_password import ForgetPasswordHandler
from .handlers.email_password_reset import EmailPasswordResetHandler
from .handlers.email_mfa_reset import EmailMFAResetHandler
from .handlers.discard import DiscardHandler
from .handlers.email_authorization import EmailAuthorizationHandler
from .handlers.native_login import LoginHandler
from .handlers.signup import SignUpHandler
from .handlers.toggle_authorization import ToggleAuthorizationHandler
from .handlers.deauthorization import DeauthorizationHandler
from .handlers.extras.orm import UserInfo

from portallib.misc import send_email_sync


class NativeAuthenticator(Authenticator):
    COMMON_PASSWORDS = None
    recaptcha_key = Unicode(
        config=True,
        help=(
            "Your key to enable reCAPTCHA as described at "
            "https://developers.google.com/recaptcha/intro"
        ),
    ).tag(default=None)

    recaptcha_secret = Unicode(
        config=True,
        help=(
            "Your secret to enable reCAPTCHA as described at "
            "https://developers.google.com/recaptcha/intro"
        ),
    ).tag(default=None)

    tos = Unicode(
        config=True,
        help=("The HTML to present next to the Term of Service " "checkbox"),
    ).tag(default=None)

    """"""

    secret_key = Unicode(
        config=True,
        help=(
            "Secret key to cryptographically sign the "
            "self-approved URL (if allow_self_approval is utilized)"
        ),
    ).tag(default="")

    allow_self_approval_for = Unicode(
        allow_none=True,
        config=True,
        help=(
            "Use self-service authentication (rather than "
            "admin-based authentication) for users whose "
            "email match this patter. Note that this forces "
            "ask_email_on_signup to be True."
        ),
    ).tag(default=None)

    self_approval_email = Tuple(
        Unicode(),
        Unicode(),
        Unicode(),
        config=True,
        default_value=(
            "do-not-reply@my-domain.com",
            "Welcome to JupyterHub on my-domain",
            (
                "Your JupyterHub account on my-domain has been "
                "created, but it's inactive.\n"
                "If you did not create the account yourself, "
                "IGNORE this message:\n"
                "somebody is trying to use your email to get an "
                "unathorized account!\n"
                "If you did create the account yourself, navigate "
                "to {approval_url} to activate it.\n"
            ),
        ),
    )

    enable_cc_admin_email = Bool(
        allow_none=True,
        config=True,
        help=("Do send a notification email to admin after user signup."),
    ).tag(default=None)

    cc_admin_email = Tuple(
        Unicode(),
        Unicode(),
        Unicode(),
        config=True,
        default_value=(
            "do-not-reply@my-domain.com",
            "Welcome to JupyterHub on my-domain",
            (
                "A JupyterHub account on my-domain for "
                "{username} at {useremail} has been "
                "created\n"
            ),
        ),
    )

    check_common_password = Bool(
        config=True,
        help=(
            "Creates a verification of password strength "
            "when a new user makes signup"
        ),
    ).tag(default=False)

    minimum_password_length = Integer(
        config=True,
        help=("Check if the length of the password is at least this size on " "signup"),
    ).tag(default=1)

    allowed_failed_logins = Integer(
        config=True,
        help=(
            "Configures the number of failed attempts a user can have "
            "before being blocked."
        ),
    ).tag(default=0)

    seconds_before_next_try = Integer(
        config=True,
        help=(
            "Configures the number of seconds a user has to wait "
            "after being blocked. Default is 600."
        ),
    ).tag(default=600)

    enable_signup = Bool(
        config=True,
        default_value=True,
        help=("Allows every user to registry a new account"),
    )

    enable_forget_password = Bool(
        config=True,
        default_value=False,
        help=("Allows users to reset their password via an email link"),
    )

    enable_change_confirmation_email = Bool(
        config=True,
        default_value=False,
        help=("Send email to users confirming password reset"),
    )

    change_confirmation_email = Tuple(
        Unicode(),
        Unicode(),
        Unicode(),
        config=True,
        default_value=(
            "do-not-reply@my-domain.com",
            "Password has been reset",
            (
                "Your account on my-domain has been "
                "updated.\n"
                "Maybe somebody is trying to use your email to "
                "reset your password!\n"
                "Or maybe you really do want to change your account, so navigate "
                "to {reset_url} to activate it.\n"
            ),
        ),
    )

    password_reset_email = Tuple(
        Unicode(),
        Unicode(),
        Unicode(),
        config=True,
        default_value=(
            "do-not-reply@my-domain.com",
            "Resetting your password",
            (
                "Your Password on my-domain has been "
                "reset.\n"
                "Maybe somebody is trying to use your email to "
                "reset your password!\n"
                "Or maybe you really do want to reset your password, so navigate "
                "to {reset_url} to activate it.\n"
            ),
        ),
    )

    reset_mfa_email = Tuple(
        Unicode(),
        Unicode(),
        Unicode(),
        config=True,
        default_value=(
            "do-not-reply@my-domain.com",
            "Resetting your MFA Device",
            (
                "Your MFA on my-domain has been "
                "reset.\n"
                "Maybe somebody is trying to use your email to "
                "reset your MFA!\n"
                "Or maybe you really do want to reset your MFA, so navigate "
                "to {reset_url} to activate it.\n"
            ),
        ),
    )

    enable_reset_mfa = Bool(
        config=True,
        default_value=False,
        help=("Allows users to reset their MFA device via an email link"),
    )

    enable_reset_mfa_email = Bool(
        config=True,
        default_value=False,
        help=("Send email to users confirming MFA device reset"),
    )

    reset_mfa_email = Tuple(
        Unicode(),
        Unicode(),
        Unicode(),
        config=True,
        default_value=(
            "do-not-reply@my-domain.com",
            "Resetting your password",
            (
                "Your MFA configuration on my-domain has been "
                "reset.\n"
                "Maybe somebody is trying to use your email to "
                "reset your MFA!\n"
                "Or maybe you really do want to reset your MFA device, so navigate "
                "to {reset_url} to activate it.\n"
            ),
        ),
    )

    open_signup = Bool(
        config=True,
        default_value=False,
        help=(
            "Allows every user that made sign up to automatically log in "
            "the system without needing admin authorization"
        ),
    )

    ask_email_on_signup = Bool(
        default_value=False, config=True, help="Asks for email on signup"
    )

    import_from_firstuse = Bool(
        False, config=True, help="Import users from FirstUse Authenticator database"
    )

    firstuse_db_path = Unicode(
        "passwords.dbm",
        config=True,
        help="""
        Path to store the db file of FirstUse with username / pwd hash in
        """,
    )

    delete_firstuse_db_after_import = Bool(
        config=True,
        default_value=False,
        help="Deletes FirstUse Authenticator database after the import",
    )

    allow_2fa = Bool(
        config=True,
        default_value=False,
        help="Allow users to optionally enable Multi-Factor Authentication",
    )

    require_2fa = Bool(
        config=True,
        default_value=False,
        help="Require all users to enable Multi-Factor Authentication",
    )

    def __init__(self, add_new_table=True, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.login_attempts = dict()
        if add_new_table:
            self.add_new_table()

        if self.import_from_firstuse:
            self.add_data_from_firstuse()

        if self.password_reset_email:
            self.ask_email_on_signup = True

        self.setup_self_approval()

    def setup_self_approval(self):
        if self.allow_self_approval_for:
            if self.open_signup:
                self.log.error("self_approval and open_signup are conflicts!")
            self.ask_email_on_signup = True
            if len(self.secret_key) < 8:
                raise ValueError(
                    "Secret_key must be a random string of "
                    "len > 8 when using self_approval"
                )

    def add_new_table(self):
        inspector = inspect(self.db.bind)
        if "users_info" not in inspector.get_table_names():
            UserInfo.__table__.create(self.db.bind)

    def add_login_attempt(self, username):
        if not self.login_attempts.get(username):
            self.login_attempts[username] = {"count": 1, "time": datetime.now()}
        else:
            self.login_attempts[username]["count"] += 1
            self.login_attempts[username]["time"] = datetime.now()

    def can_try_to_login_again(self, username):
        login_attempts = self.login_attempts.get(username)
        if not login_attempts:
            return True

        time_last_attempt = datetime.now() - login_attempts["time"]
        if time_last_attempt.seconds > self.seconds_before_next_try:
            return True

        return False

    def is_blocked(self, username):
        logins = self.login_attempts.get(username)

        if not logins or logins["count"] < self.allowed_failed_logins:
            return False

        if self.can_try_to_login_again(username):
            return False
        return True

    def successful_login(self, username):
        if self.login_attempts.get(username):
            self.login_attempts.pop(username)

    async def authenticate(self, handler, data):
        username = self.normalize_username(data["username"])
        password = data["password"]

        user = self.get_user(username)
        if not user:
            return

        if self.allowed_failed_logins:
            if self.is_blocked(username):
                return

        validations = [user.is_authorized, user.is_valid_password(password)]
        if user.has_2fa:
            validations.append(user.is_valid_token(data.get("2fa")))

        if all(validations):
            self.successful_login(username)
            return username

        self.add_login_attempt(username)

    def is_password_common(self, password):
        common_credentials_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "common-credentials.txt"
        )
        if not self.COMMON_PASSWORDS:
            with open(common_credentials_file) as f:
                self.COMMON_PASSWORDS = set(f.read().splitlines())
        return password in self.COMMON_PASSWORDS

    def is_password_strong(self, password):
        checks = [len(password) >= self.minimum_password_length]

        if self.check_common_password:
            checks.append(not self.is_password_common(password))

        return all(checks)

    def get_user(self, username):
        return UserInfo.find(self.db, self.normalize_username(username))

    def get_authed_users(self):
        try:
            allowed = self.allowed_users
        except AttributeError:
            try:
                # Deprecated for jupyterhub >= 1.2
                allowed = self.whitelist
            except AttributeError:
                # Not present at all in jupyterhub < 0.9
                allowed = {}

        authed = set()
        for info in UserInfo.all_users(self.db):
            user = self.get_user(info.username)
            if user is not None:
                if user.is_authorized:
                    authed.update(set({info.username}))

        return authed.union(allowed.union(self.admin_users))

    def user_exists(self, username):
        return self.get_user(username) is not None

    def create_user(self, username, password, **kwargs):
        username = self.normalize_username(username)

        if self.user_exists(username) or not self.validate_username(username):
            return

        if not self.is_password_strong(password):
            return

        if not self.enable_signup:
            return

        encoded_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        infos = {"username": username, "password": encoded_password}
        infos.update(kwargs)

        # Pre-authorized users (admins, or any users during open signup)
        pre_authorized = self.open_signup or username in self.get_authed_users()

        if pre_authorized:
            infos.update({"is_authorized": True})

        try:
            user_info = UserInfo(**infos)
        except AssertionError:
            return

        # Don't send authorization emails to pre-authorized users.
        if self.allow_self_approval_for and not pre_authorized:
            match = re.match(self.allow_self_approval_for, user_info.email)
            if match:
                url = self.generate_approval_url(username)
                self.send_approval_email(user_info.email, url)
                user_info.login_email_sent = True

        self.db.add(user_info)
        self.db.commit()

        if self.enable_cc_admin_email:
            self.generate_cc_admin_email(username, user_info.email)

        return user_info

    def generate_cc_admin_email(self, username, useremail):
        try:
            payload = {
                "from": {"email": self.cc_admin_email[0]},
                "to": {"email": self.cc_admin_email[0]},
                "subject": self.cc_admin_email[1],
                "html_body": self.cc_admin_email[2].format(
                    username=username, useremail=useremail
                ),
            }
            send_email_sync(payload)
        except Exception as e:
            self.log.error(
                f"Something went wrong with cc admin email: {e}, {traceback.format_exc()}"
            )
            raise web.HTTPError(
                503,
                reason="Eemail could not be sent. Please contact the JupyterHub admin about this.",
            )

    def generate_approval_url(self, username, when=None):
        if when is None:
            when = datetime.now(tz.utc) + timedelta(minutes=60)
        s = Signer(self.secret_key, salt="andpeppersinghiphop")
        u = s.sign_object({"username": username, "expire": when.isoformat()})

        self.log.warning(
            f"Signup confirmation link hash created for username '{username}': {u}"
        )

        return "/confirm/" + u

    def send_approval_email(self, dest, url):
        try:
            payload = {
                "from": {"email": self.self_approval_email[0]},
                "to": {"email": dest},
                "subject": self.self_approval_email[1],
                "html_body": self.self_approval_email[2].format(approval_url=url),
            }
            send_email_sync(payload)
        except Exception as e:
            self.log.error(
                f"Something went wrong with approval email: {e}, {traceback.format_exc()}"
            )
            raise web.HTTPError(
                503,
                reason="Self-authorization email could not "
                + "be sent. Please contact the JupyterHub "
                + "admin about this.",
            )

    def generate_password_reset_url(self, payload: dict, when=None) -> str:
        if when is None:
            when = datetime.now(tz.utc) + timedelta(minutes=60)
        s = Signer(self.secret_key, salt="andpeppersinghiphop")
        payload.update({"expire": when.isoformat()})
        u = s.sign_object(payload)

        username = payload.get("username", None)
        if username:
            self.log.warning(
                f"Reset confirmation link hash created for username '{username}': {u}"
            )

        return "/confirm-password/" + u

    def send_password_reset_email(self, dest: str, url: str, username: str):
        try:
            payload = {
                "to": {"email": dest},
                "from": {"email": self.password_reset_email[0]},
                "subject": self.password_reset_email[1],
                "html_body": self.password_reset_email[2].format(
                    reset_url=url, username=username
                ),
            }
            send_email_sync(payload)
        except Exception as e:
            self.log.error(
                f"Something went wrong with password reset email: {e}, {traceback.format_exc()}"
            )
            raise web.HTTPError(
                503,
                reason="Password reset email could not "
                + "be sent. Please contact the JupyterHub "
                + "admin about this.",
            )

    def generate_mfa_device_reset_url(self, payload: dict, when=None) -> str:
        if when is None:
            when = datetime.now(tz.utc) + timedelta(minutes=60)
        s = Signer(self.secret_key, salt="andpeppersinghiphop")
        payload.update({"expire": when.isoformat()})
        u = s.sign_object(payload)

        username = payload.get("username", None)
        if username:
            self.log.warning(
                f"MFA Device Reset confirmation link hash created for username '{username}': {u}"
            )

        return "/confirm-mfa-reset/" + u

    def send_mfa_device_reset_email(self, dest: str, url: str, username: str):
        try:
            payload = {
                "to": {"email": dest},
                "from": {"email": self.reset_mfa_email[0]},
                "subject": self.reset_mfa_email[1],
                "html_body": self.reset_mfa_email[2].format(
                    reset_url=url, username=username
                ),
            }
            send_email_sync(payload)
        except Exception as e:
            self.log.error(
                f"Something went wrong with mfa device reset email: {e}, {traceback.format_exc()}"
            )
            raise web.HTTPError(
                503,
                reason="MFA device reset email could not "
                + "be sent. Please contact the JupyterHub "
                + "admin about this.",
            )

    def send_change_confirmation_email(self, username: str):
        try:
            payload = {
                "to": {"username": username},
                "from": {"email": self.change_confirmation_email[0]},
                "subject": self.change_confirmation_email[1],
                "html_body": self.change_confirmation_email[2].format(
                    username=username
                ),
            }
            send_email_sync(payload)
        except Exception as e:
            self.log.error(
                f"Something went wrong with change confirmation email: {e}, {traceback.format_exc()}"
            )
            raise web.HTTPError(
                503,
                reason="Change confirmation email could not "
                + "be sent. Please contact the JupyterHub "
                + "admin about this.",
            )

    def get_unauthed_amount(self):
        unauthed = 0
        for info in UserInfo.all_users(self.db):
            user = self.get_user(info.username)
            if user is not None:
                if info.username not in self.get_authed_users():
                    unauthed += 1

        return unauthed

    def change_password(self, username, new_password):
        user = self.get_user(username)

        criteria = [
            user is not None,
            self.is_password_strong(new_password),
        ]
        if not all(criteria):
            return

        user.password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
        self.db.commit()
        return True

    def validate_username(self, username):
        invalid_chars = [",", " ", "/"]
        if any((char in username) for char in invalid_chars):
            return False
        # The word `admin` cannot be in any usernames
        if "admin" in username:
            return False
        return super().validate_username(username)

    def get_handlers(self, app):
        native_handlers = [
            (r"/login", LoginHandler),
            (r"/signup", SignUpHandler),
            (r"/setup-mfa", Setup2FAHandler),
            (r"/reset-mfa", ResetMFADeviceHandler),
            (r"/reset-mfa/([^/]*)", Reset2FAAdminHandler),
            (r"/validate-totp", ValidateOPTHandler),
            (r"/discard/([^/]*)", DiscardHandler),
            (r"/authorize", AuthorizationAreaHandler),
            (r"/authorize/([^/]*)", ToggleAuthorizationHandler),
            (r"/deauthorize", DeauthorizationHandler),
            # the following /confirm/ must be like in generate_approval_url()
            (r"/confirm/([^/]*)", EmailAuthorizationHandler),
            (r"/change-password", ChangePasswordHandler),
            (r"/change-password/([^/]+)", ChangePasswordAdminHandler),
            (r"/forget-password", ForgetPasswordHandler),
            (r"/confirm-password/([^/]*)", EmailPasswordResetHandler),
            (r"/confirm-mfa-reset/([^/]*)", EmailMFAResetHandler),
        ]
        return native_handlers

    def delete_user(self, user):
        user_info = self.get_user(user.name)
        if user_info is not None:
            self.db.delete(user_info)
            self.db.commit()
        return super().delete_user(user)

    def delete_dbm_db(self):
        db_path = Path(self.firstuse_db_path)
        db_dir = db_path.cwd()
        db_name = db_path.name
        db_complete_path = str(db_path.absolute())

        # necessary for BSD implementation of dbm lib
        if os.path.exists(os.path.join(db_dir, db_name + ".db")):
            os.remove(db_complete_path + ".db")
        else:
            os.remove(db_complete_path)

    def add_data_from_firstuse(self):
        with dbm.open(self.firstuse_db_path, "c", 0o600) as db:
            for user in db.keys():
                password = db[user].decode()
                new_user = self.create_user(user.decode(), password)
                if not new_user:
                    error = (
                        f"User {user} was not created. Check password "
                        "restrictions or username problems before trying "
                        "again."
                    )
                    raise ValueError(error)

        if self.delete_firstuse_db_after_import:
            self.delete_dbm_db()
