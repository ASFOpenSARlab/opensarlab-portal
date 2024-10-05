import os

from jinja2 import ChoiceLoader
from jinja2 import FileSystemLoader
from jupyterhub.handlers import BaseHandler

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "templates")


class LocalBase(BaseHandler):
    """Base class that all handlers below extend."""

    _template_dir_registered = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not LocalBase._template_dir_registered:
            self.log.debug("Adding %s to template path", TEMPLATE_DIR)
            loader = FileSystemLoader([TEMPLATE_DIR])
            env = self.settings["jinja2_env"]
            previous_loader = env.loader
            env.loader = ChoiceLoader([previous_loader, loader])
            LocalBase._template_dir_registered = True
