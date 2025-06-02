# modules/bar/bar.py
from ignis.widgets import Widget
from ignis.app import IgnisApp
from ignis.services.hyprland import HyprlandService
from ignis.services.applications import ApplicationsService
from .widgets import StatusPill, Tray, KeyboardLayout, Battery, Workspaces, RunningAppsBar

app = IgnisApp.get_default()
hyprland = HyprlandService.get_default()
applications_service = ApplicationsService.get_default()

class Bar(Widget.Window):
    __gtype_name__ = "Bar"

    def __init__(self, monitor: int):
        self.monitor_id = monitor # Przechowujemy ID monitora dla tego konkretnego paska

        side_panel_left_toggle_button = Widget.Button(
            child=Widget.Icon(image="menu-symbolic", pixel_size=24),
            # Przekazujemy ID monitora do metody przełączającej
            on_click=lambda _, m=self.monitor_id: self._toggle_side_panel_left(m),
            css_classes=["bar-button", "unset"]
        )

        app_list_left_toggle_button = Widget.Button(
            child=Widget.Icon(image="apps-symbolic", pixel_size=24),
            # Przekazujemy ID monitora do metody otwierającej launcher
            on_click=lambda _, m=self.monitor_id: self._open_app_launcher_in_left_side_panel(m),
            css_classes=["bar-button", "unset"]
        )

        running_apps_bar = RunningAppsBar()

        super().__init__(
            anchor=["left", "top", "right"],
            exclusivity="exclusive",
            monitor=self.monitor_id, # Ustawiamy monitor dla samego paska
            namespace=f"ignis_BAR_{self.monitor_id}",
            layer="top",
            kb_mode="none",
            child=Widget.CenterBox(
                css_classes=["bar-widget"],
                start_widget=Widget.Box(
                    child=[
                        side_panel_left_toggle_button,
                        app_list_left_toggle_button,
                        running_apps_bar,
                    ],
                    spacing=5
                ),
                center_widget=Widget.Box(child=[Workspaces()]),
                end_widget=Widget.Box(
                    child=[
                        Tray(),
                        KeyboardLayout(),
                        Battery(),
                        StatusPill(self.monitor_id) # StatusPill też dostaje ID monitora
                    ],
                    spacing=5
                ),
            ),
            css_classes=["unset"],
        )

    def _toggle_side_panel_left(self, monitor_id: int):
        # print(f"Toggle SidePanelLeft requested for monitor: {monitor_id}")
        try:
            panel_window = app.get_window("ignis_SIDE_PANEL_LEFT") #
            if panel_window.props.visible and panel_window.props.monitor == monitor_id:
                app.close_window("ignis_SIDE_PANEL_LEFT") #
            else:
                panel_window.props.monitor = monitor_id # Ustaw monitor przed pokazaniem
                app.open_window("ignis_SIDE_PANEL_LEFT") #
        except Exception as e:
            print(f"Error toggling SidePanelLeft: {e}")


    def _open_app_launcher_in_left_side_panel(self, monitor_id: int):
        # print(f"Open AppLauncher in SidePanelLeft requested for monitor: {monitor_id}")
        try:
            panel_window = app.get_window("ignis_SIDE_PANEL_LEFT")
            panel_window.props.monitor = monitor_id # Zawsze ustawiaj monitor
            app.open_window("ignis_SIDE_PANEL_LEFT")
            # Ustawienie aktywnego widoku na launcher
            app.run_python(
                "from modules.side_panel_left.state import active_view_in_left_panel; "
                "active_view_in_left_panel.value = 'app_launcher'"
            )
        except Exception as e:
            print(f"Error opening AppLauncher in SidePanelLeft: {e}")