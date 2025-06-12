# modules/control_center/control_center.py
from ignis.widgets import Widget
from ignis.app import IgnisApp
from ignis.variable import Variable

# --- ZMIANA: Importujemy każdy widget bezpośrednio z jego pliku ---
from .widgets.quick_settings.quick_settings import QuickSettings
from .widgets.brightness import Brightness
from .widgets.volume import VolumeSlider
from .widgets.user import User
from .widgets.media import Media
from .widgets.notification_center import NotificationCenter
from .widgets.calendar_view import CalendarView
from .widgets.todo_view import TodoView
# -----------------------------------------------------------------

from .menu import opened_menu
from .state import active_view

app = IgnisApp.get_default()


class ControlCenter(Widget.RevealerWindow):
    def __init__(self):
        self.content_stack = Widget.Stack(
            transition_type="slide_up_down",
            vexpand=True,
        )

        notification_view = NotificationCenter()
        self.content_stack.add_named(notification_view, "notifications")

        calendar_view = CalendarView()
        self.content_stack.add_named(calendar_view, "calendar")

        todo_view = TodoView()
        self.content_stack.add_named(todo_view, "todo")
        
        self.nav_notifications_button = Widget.Button(
            icon_name="notifications-symbolic",
            on_click=lambda x: setattr(active_view, "value", "notifications"),
            hexpand=True,
            css_classes=["cc-nav-button", "unset"]
        )
        self.nav_calendar_button = Widget.Button(
            icon_name="x-office-calendar-symbolic",
            on_click=lambda x: setattr(active_view, "value", "calendar"),
            hexpand=True,
            css_classes=["cc-nav-button", "unset"]
        )
        self.nav_todo_button = Widget.Button(
            icon_name="format-justify-fill-symbolic",
            on_click=lambda x: setattr(active_view, "value", "todo"),
            hexpand=True,
            css_classes=["cc-nav-button", "unset"]
        )
        
        bottom_navigation = Widget.Box(
            css_classes=["cc-nav-bar"],
            homogeneous=True,
            child=[
                self.nav_notifications_button,
                self.nav_calendar_button,
                self.nav_todo_button,
            ]
        )
        
        active_view.connect("notify::value", self._on_view_change)

        bottom_panel_wrapper = Widget.Box(
            vertical=True,
            css_classes=["notification-center"],
            vexpand=True,
            child=[
                self.content_stack,
                bottom_navigation,
            ]
        )

        main_content_box = Widget.Box(
            vertical=True,
            css_classes=["control-center"],
            spacing=16,
            child=[
                Widget.Box(
                    vertical=True,
                    css_classes=["control-center-widget"],
                    child=[
                        QuickSettings(),
                        VolumeSlider("speaker"),
                        VolumeSlider("microphone"),
                        Brightness(),
                        User(),
                        Media(),
                    ],
                ),
                bottom_panel_wrapper,
            ],
        )

        revealer = Widget.Revealer(
            transition_type="slide_left",
            child=main_content_box,
            transition_duration=300,
            reveal_child=True,
        )

        super().__init__(
            visible=False,
            popup=True,
            kb_mode="on_demand",
            layer="top",
            css_classes=["unset"],
            anchor=["top", "right", "bottom", "left"],
            namespace="ignis_CONTROL_CENTER",
            child=Widget.Box(
                child=[
                    Widget.Button(
                        vexpand=True,
                        hexpand=True,
                        css_classes=["unset"],
                        on_click=lambda x: app.close_window("ignis_CONTROL_CENTER"),
                    ),
                    revealer,
                ],
            ),
            setup=self._initial_setup,
            revealer=revealer,
        )

    def _initial_setup(self, *args):
        self._on_view_change(active_view, None)
        self.connect("notify::visible", lambda x, y: opened_menu.set_value(""))

    def _on_view_change(self, variable: Variable, pspec):
        view_name = variable.value
        self.content_stack.set_visible_child_name(view_name)
        
        buttons = {
            "notifications": self.nav_notifications_button,
            "calendar": self.nav_calendar_button,
            "todo": self.nav_todo_button,
        }
        
        for name, button in buttons.items():
            if name == view_name:
                button.add_css_class("active")
            else:
                button.remove_css_class("active")