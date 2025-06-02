# modules/bar/widgets/__init__.py
from .pill import StatusPill
from .tray import Tray
from .kb_layout import KeyboardLayout
from .battery import Battery
# from .apps import Apps # Prawdopodobnie już niepotrzebne, jeśli 'Apps' było tylko dla przypiętych
from .workspaces import Workspaces
from .running_apps_bar import RunningAppsBar # Dodaj ten import

__all__ = [
    "StatusPill",
    "Tray",
    "KeyboardLayout",
    "Battery",
    "Workspaces",
    "RunningAppsBar", # Dodaj do __all__
]