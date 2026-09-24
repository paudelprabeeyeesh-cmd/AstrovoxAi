"""Developer platform package."""
from .one_command_setup import one_command_setup  # noqa: F401
from .sdk import PluginSDK, PublicAPIDocs  # noqa: F401
from .cli import AdminCLI  # noqa: F401
from .compat import BackwardCompatibility  # noqa: F401

__all__ = ["one_command_setup", "PluginSDK", "PublicAPIDocs", "AdminCLI", "BackwardCompatibility"]
