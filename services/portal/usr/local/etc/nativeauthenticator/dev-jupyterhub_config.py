import os
import secrets

import nativeauthenticator


c.JupyterHub.spawner_class = "simple"
c.JupyterHub.authenticator_class = "nativeauthenticator.NativeAuthenticator"
c.Authenticator.admin_users = {"admin"}

# Required configuration of templates location
if not isinstance(c.JupyterHub.template_paths, list):
    c.JupyterHub.template_paths = []
c.JupyterHub.template_paths.append(
    f"{os.path.dirname(nativeauthenticator.__file__)}/templates/"
)

# Below are all the available configuration options for NativeAuthenticator
# -------------------------------------------------------------------------

c.NativeAuthenticator.check_common_password = False
# c.NativeAuthenticator.minimum_password_length = 8
# c.NativeAuthenticator.allowed_failed_logins = 0
# c.NativeAuthenticator.seconds_before_next_try = 600

c.NativeAuthenticator.open_signup = False
c.NativeAuthenticator.allow_2fa = True
c.NativeAuthenticator.require_2fa = True

c.NativeAuthenticator.tos = 'I agree to the <a href="your-url" target="_blank">TOS</a>.'

# c.NativeAuthenticator.recaptcha_key = "your key"
# c.NativeAuthenticator.recaptcha_secret = "your secret"

c.NativeAuthenticator.enable_signup = True

c.NativeAuthenticator.enable_forget_password = True
c.NativeAuthenticator.password_reset_email = (
    "MY_EMAIL",
    "Change Password in the OSL Portal",
    "You have requested a change of your OSL password. To complete the process, please click here: http://localhost:8000/{reset_url}.",
)

c.NativeAuthenticator.allow_self_approval_for = None  # '^(?!.*(?:\.ir|\.cn|\.kp)$).*'
c.NativeAuthenticator.secret_key = secrets.token_hex(32)
c.NativeAuthenticator.self_approval_email = (
    "MY_EMAIL",
    "Welcome to the OSL Portal",
    "You have signed up for access to OSL. To complete the process, please click here: http://localhost:8000/{approval_url}.",
)

c.NativeAuthenticator.email_server = {
    "url": "email-smtp.us-west-2.amazonaws.com",
    "usr": "****",
    "pwd": "****",
}

# c.NativeAuthenticator.import_from_firstuse = False
# c.NativeAuthenticator.firstuse_dbm_path = "/home/user/passwords.dbm"
# c.NativeAuthenticator.delete_firstuse_db_after_import = False
