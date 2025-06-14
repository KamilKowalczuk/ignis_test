# modules/side_panel_left/side_panel_left.py
from gi.repository import GLib, Gtk 
from ignis.widgets import Widget
from ignis.app import IgnisApp
from ignis.variable import Variable
from .state import active_view_in_left_panel
from .widgets.app_launcher_view import AppLauncherView
from .widgets.weather_view import WeatherView
from .widgets.system_info_view import SystemInfoView 

app = IgnisApp.get_default()

class SidePanelLeft(Widget.RevealerWindow):
    __gtype_name__ = "SidePanelLeft"
    
    def __init__(self):
        # ... (cała logika tworzenia navigation_column, content_stack, panel_content_box, revealer, overlay_background_button, overlay_container - BEZ ZMIAN) ...
        # --- Lewa kolumna nawigacyjna (bez zmian) ---
        self.nav_system_info_button = Widget.Button( # NOWY PRZYCISK
            child=Widget.Icon(image="preferences-system-details-symbolic", pixel_size=28), # Ikona informacji o systemie
            on_click=lambda x: setattr(active_view_in_left_panel, 'value', "system_info"),
            tooltip_text="Informacje o systemie",
            css_classes=["side-panel-nav-button", "unset"]
        )
        self.nav_app_launcher_button = Widget.Button(
            child=Widget.Icon(image="view-app-grid-symbolic", pixel_size=28),
            on_click=lambda x: setattr(active_view_in_left_panel, 'value', "app_launcher"),
            tooltip_text="Aplikacje",
            css_classes=["side-panel-nav-button", "unset"]
        )
        self.nav_weather_button = Widget.Button( 
            child=Widget.Icon(image="weather-clear-symbolic", pixel_size=28),
            on_click=lambda x: setattr(active_view_in_left_panel, 'value', "weather_view"),
            tooltip_text="Pogoda",
            css_classes=["side-panel-nav-button", "unset"]
        )
        self.nav_gemini_button = Widget.Button( 
            child=Widget.Icon(image="chat-bubbles-symbolic", pixel_size=28),
            on_click=lambda x: setattr(active_view_in_left_panel, 'value', "gemini_chat"),
            tooltip_text="Czat Gemini",
            css_classes=["side-panel-nav-button", "unset"]
        )
        navigation_column = Widget.Box(
            vertical=True, valign="start", halign="center",
            css_classes=["side-panel-left-navigation-column"],
            spacing=8, margin_top=10, margin_bottom=10, margin_start=5, margin_end=5,
            child=[
                self.nav_system_info_button,
                self.nav_app_launcher_button,
                self.nav_weather_button,
                self.nav_gemini_button,
            ]
        )

        self.system_info_view = SystemInfoView()
        self.app_launcher_view = AppLauncherView()
        self.weather_view = WeatherView()
        self.gemini_chat_placeholder = Widget.Box(child=[Widget.Label(label="Widok Czatu Gemini (TODO)")], vexpand=True, hexpand=True, halign="center", valign="center")

        self.content_stack = Widget.Stack(
            transition_type="slide_left_right", vexpand=True, hexpand=True,
            css_classes=["side-panel-left-content-stack"]
        )
        self.content_stack.add_named(self.system_info_view, "system_info") # Dodajemy nowy widok
        self.content_stack.add_named(self.app_launcher_view, "app_launcher")
        self.content_stack.add_named(self.weather_view, "weather_view")
        self.content_stack.add_named(self.gemini_chat_placeholder, "gemini_chat")
        
        active_view_in_left_panel.connect("notify::value", self._on_active_view_changed)

        panel_content_box = Widget.Box(
            css_classes=["side-panel-left-main-box"],
            child=[
                navigation_column,
                Widget.Separator(vertical=True, css_classes=["side-panel-separator"]), 
                self.content_stack,
            ]
        )
        # Ustawiamy żądaną szerokość na właściwej zawartości panelu
        panel_content_box.props.width_request = 620 # Szerokość widocznej części panelu


        revealer = Widget.Revealer(
            transition_type="slide_right", 
            child=panel_content_box,
            transition_duration=250,
            hexpand=False, 
            vexpand=True,  
            halign="start", # Używamy stringów
            valign="fill"   # Używamy stringów
        )

        overlay_background_button = Widget.Button(
            vexpand=True, 
            hexpand=True, 
            css_classes=["unset", "side-panel-left-overlay-background"],
            on_click=lambda x: app.close_window("ignis_SIDE_PANEL_LEFT"),
            can_focus=False
        )
        
        overlay_container = Widget.Overlay( 
            child=overlay_background_button,
            overlays=[revealer] 
        )
        
        super().__init__(
            namespace="ignis_SIDE_PANEL_LEFT",
            anchor=["left", "top", "bottom"], 
            layer="overlay", 
            exclusivity="ignore", 
            kb_mode="on_demand", 
            popup=True, 
            visible=False,
            child=overlay_container,
            revealer=revealer, 
            # margin_top=50,    # Odstęp w pikselach od góry ekranu
            # margin_bottom=14, # Odstęp od dołu
            # margin_left=10,   # Odstęp od lewej
            default_width=620, # <<<--- PRZYWRACAMY default_width na oknie
            css_classes=["side-panel-left-window", "unset"],
            setup=self._initial_view_setup 
        )
        # panel_content_box.props.width_request = 370 # Możemy to zostawić lub zakomentować, jeśli default_width okna wystarczy

    # ... (reszta metod bez zmian) ...
    def _on_active_view_changed(self, variable: Variable, pspec):
        if variable.value and self.content_stack.get_child_by_name(variable.value):
            self.content_stack.visible_child_name = variable.value
            self._update_nav_buttons_active_state(variable.value)
        elif not variable.value and self.content_stack.get_children():
            pass 

    def _update_nav_buttons_active_state(self, active_view_name: str | None):
        buttons_map = {
            "system_info": self.nav_system_info_button,
            "app_launcher": self.nav_app_launcher_button,
            "weather_view": self.nav_weather_button,
            "gemini_chat": self.nav_gemini_button,
        }
        for name, button in buttons_map.items():
            if name == active_view_name:
                button.add_css_class("active")
            else:
                button.remove_css_class("active")
                
    def _initial_view_setup(self, _widget):
        # print(f"SidePanelLeft: Initial view setup. Current active_view: {active_view_in_left_panel.value}")
        if active_view_in_left_panel.value and self.content_stack.get_child_by_name(active_view_in_left_panel.value):
            GLib.idle_add(self._set_initial_stack_view, active_view_in_left_panel.value)
        else:
            # Ustaw domyślny widok na "system_info"
            active_view_in_left_panel.value = "system_info" 
            GLib.idle_add(self._set_initial_stack_view, "system_info")

    # _on_active_view_changed i _set_initial_stack_view pozostają takie same
    def _on_active_view_changed(self, variable: Variable, pspec):
        # print(f"SidePanelLeft: Active view changed to: {variable.value}")
        if variable.value and self.content_stack.get_child_by_name(variable.value):
            self.content_stack.visible_child_name = variable.value
            self._update_nav_buttons_active_state(variable.value)
        # Jeśli variable.value jest None, a chcemy domyślny, to _initial_view_setup to obsłuży przy pierwszym otwarciu
        # lub możemy dodać tu fallback, jeśli panel jest już otwarty, a wartość staje się None.
        elif not variable.value and self.content_stack.get_child_by_name("system_info"): 
             # print("SidePanelLeft: active_view is None, defaulting to system_info")
             self.content_stack.visible_child_name = "system_info"
             self._update_nav_buttons_active_state("system_info")


    def _set_initial_stack_view(self, view_name: str):
        if self.content_stack.get_child_by_name(view_name):
            self.content_stack.visible_child_name = view_name
            self._update_nav_buttons_active_state(view_name)
        return False