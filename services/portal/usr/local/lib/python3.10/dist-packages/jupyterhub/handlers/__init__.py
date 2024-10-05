from . import base
from . import login
from . import metrics
from . import pages
from . import portal_home
from . import auth
from . import native_user_info
from .base import *
from .login import *

default_handlers = []
for mod in (base, pages, login, metrics, auth, native_user_info):
    default_handlers.extend(mod.default_handlers)

# Remove unwanted handlers
for handle in default_handlers:
    if "home" in handle[0] or "spawn" in handle[0]:
        default_handlers.remove(handle)

# Add previously-conflicted handles
default_handlers.extend(portal_home.default_handlers)
