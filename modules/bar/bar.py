# modules/bar/bar.py
from ignis.widgets import Widget
from ignis.app import IgnisApp
from ignis.services.hyprland import HyprlandService 
from ignis.services.applications import ApplicationsService
from .widgets import StatusPill, Tray, KeyboardLayout, Battery, Workspaces, RunningAppsBar

# >>> NOWY IMPORT <<<
from modules.side_panel_left.state import active_view_in_left_panel # Importujemy zmienną stanu

app = IgnisApp.get_default()
hyprland = HyprlandService.get_default()
applications_service = ApplicationsService.get_default()

class Bar(Widget.Window):
    __gtype_name__ = "Bar"

    def __init__(self, monitor: int):
        self.monitor_id = monitor

        side_panel_left_toggle_button = Widget.Button(
            child=Widget.Icon(image="menu-symbolic", pixel_size=20),
            on_click=lambda _, m=self.monitor_id: self._handle_side_panel_action(m, "system_info", toggle=True),
            css_classes=["bar-button", "unset"]
        )

        app_list_left_toggle_button = Widget.Button(
            child=Widget.Icon(image="apps-symbolic", pixel_size=20),
            on_click=lambda _, m=self.monitor_id: self._handle_side_panel_action(m, "app_launcher", toggle=False),
            css_classes=["bar-button", "unset"]
        )
        
        running_apps_bar = RunningAppsBar()

        super().__init__(
            anchor=["left", "top", "right"], exclusivity="exclusive", monitor=self.monitor_id,
            namespace=f"ignis_BAR_{self.monitor_id}", layer="top", kb_mode="none",
            child=Widget.CenterBox(
                css_classes=["bar-widget"],
                start_widget=Widget.Box(
                    child=[side_panel_left_toggle_button, app_list_left_toggle_button, running_apps_bar],
                    spacing=5
                ),
                center_widget=Widget.Box(child=[Workspaces()]),
                end_widget=Widget.Box(
                    child=[Tray(), KeyboardLayout(), Battery(), StatusPill(self.monitor_id)],
                    spacing=5
                ),
            ),
            css_classes=["unset"],
        )

    def _handle_side_panel_action(self, monitor_id: int, view_name: str, toggle: bool):
        print(f"--- _handle_side_panel_action called ---")
        print(f"  Monitor ID: {monitor_id}, View Name: '{view_name}', Toggle: {toggle}")

        target_window_name = "ignis_SIDE_PANEL_LEFT"

        try:
            panel_window = app.get_window(target_window_name)
            print(f"  Panel window '{target_window_name}' found.")

            # >>> ZMIANA SPOSOBU USTAWIANIA WIDOKU <<<
            print(f"  Setting active_view_in_left_panel.value to '{view_name}'")
            active_view_in_left_panel.value = view_name # Bezpośrednie ustawienie wartości Variable
            print(f"  active_view_in_left_panel.value is now '{active_view_in_left_panel.value}'")


            is_currently_visible = panel_window.props.visible
            is_on_correct_monitor = panel_window.props.monitor == monitor_id
            current_panel_view = None
            if hasattr(panel_window, 'content_stack') and panel_window.content_stack is not None and hasattr(panel_window.content_stack, 'props'):
                 current_panel_view = panel_window.content_stack.props.visible_child_name

            print(f"  Panel state: visible={is_currently_visible}, on_correct_monitor={is_on_correct_monitor}, current_view='{current_panel_view}'")

            if toggle: 
                if is_currently_visible and is_on_correct_monitor and current_panel_view == view_name:
                    print(f"  Toggle: Closing panel.")
                    app.close_window(target_window_name)
                else:
                    print(f"  Toggle: Opening/Moving panel to monitor {monitor_id}.")
                    panel_window.props.monitor = monitor_id
                    app.open_window(target_window_name) 
            else: 
                print(f"  Non-toggle: Opening/Moving panel to monitor {monitor_id}.")
                panel_window.props.monitor = monitor_id
                app.open_window(target_window_name)

        except Exception as e:
            print(f"  ERROR in _handle_side_panel_action: {e}")
            import traceback
            traceback.print_exc()