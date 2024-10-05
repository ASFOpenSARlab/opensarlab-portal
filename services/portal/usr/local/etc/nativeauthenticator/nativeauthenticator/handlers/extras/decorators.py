# import jupyterhub

try:
    from jupyterhub.scopes import needs_scope

    admin_users_scope = needs_scope("admin:users")
except ImportError:
    from jupyterhub.utils import admin_only

    admin_users_scope = admin_only
