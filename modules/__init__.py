# modules/__init__.py
from .bar import Bar
from .control_center import ControlCenter
from .launcher import Launcher
from .notification_popup import NotificationPopup
from .osd import OSD
from .powermenu import Powermenu
from .settings import Settings
from .side_panel_left import SidePanelLeft # <<<--- UPEWNIJ SIĘ, ŻE TEN IMPORT JEST POPRAWNY

__all__ = [
    "Bar",
    "ControlCenter",
    "Launcher",
    "NotificationPopup",
    "OSD",
    "Powermenu",
    "Settings",
    "SidePanelLeft", # <<<--- I ŻE JEST DODANY DO __all__
]