# modules/bar/widgets/running_apps_bar.py
from gi.repository import GObject, GLib # Dodajemy GLib dla timeout_add jeśli będzie potrzebny
from ignis.widgets import Widget
from ignis.services.hyprland import HyprlandService, HyprlandWindow
from ignis.services.applications import ApplicationsService
from ignis.utils import Utils
# from ignis.app import IgnisApp # Już niepotrzebne

hyprland = HyprlandService.get_default()
applications_service = ApplicationsService.get_default()

class RunningAppButton(Widget.Button):
    def __init__(self, window_data: HyprlandWindow):
        self.window_data = window_data
        self.icon_widget = Widget.Icon(pixel_size=14)
        super().__init__(
            child=self.icon_widget,
            on_click=self._on_click,
            css_classes=["running-app-button", "unset"]
        )
        self._update_icon()
        self._update_active_state() # ODTERAZ ODKOMENTOWANE

        # Połącz z sygnałem zmiany aktywnego okna Hyprland, aby aktualizować styl WSZYSTKICH przycisków
        # To połączenie będzie w RunningAppsBar, aby nie tworzyć wielu listenerów dla tego samego globalnego sygnału
        # self.hyprland_active_window_conn = hyprland.connect("notify::active_window", self._update_active_state)
        
        # Połącz z sygnałem zamknięcia TEGO konkretnego okna
        self.window_closed_conn_id = self.window_data.connect("closed", self._on_window_closed) # ODTERAZ ODKOMENTOWANE


    def _update_icon(self):
        icon_name = "application-x-executable-symbolic"
        try:
            app_candidates = applications_service.search(applications_service.apps, self.window_data.initial_class)
            if not app_candidates:
                app_candidates = applications_service.search(applications_service.apps, self.window_data.class_name)

            if app_candidates and app_candidates[0].icon:
                icon_name = app_candidates[0].icon
            else:
                util_icon = Utils.get_app_icon_name(self.window_data.initial_class.lower().replace(" ", "-"))
                if not util_icon:
                    util_icon = Utils.get_app_icon_name(self.window_data.class_name.lower().replace(" ", "-"))
                if util_icon:
                    icon_name = util_icon
        except Exception as e:
            # print(f"Error getting icon for {self.window_data.title} (in _update_icon): {e}")
            pass # Zmniejszamy ilość logów, gdy działa
        self.icon_widget.image = icon_name

    def _on_click(self, _):
        # print(f"Attempting to switch to window: {self.window_data.title}, address: {self.window_data.address}, workspace: {self.window_data.workspace_id}")
        try:
            current_active_workspace_id = hyprland.active_workspace.id
            # print(f"Current active workspace ID: {current_active_workspace_id}")

            if self.window_data.workspace_id != current_active_workspace_id:
                # print(f"Switching to workspace {self.window_data.workspace_id}")
                hyprland.switch_to_workspace(self.window_data.workspace_id)
                # Dajemy Hyprlandowi chwilę na przetworzenie zmiany pulpitu przed próbą focusu
                GLib.timeout_add(50, self._focus_window_command)
            else:
                self._focus_window_command()
        except Exception as e:
            print(f"Could not switch to window {self.window_data.title}: {e}")

    def _focus_window_command(self):
        try:
            command = f"dispatch focuswindow address:{self.window_data.address}"
            # print(f"Executing Hyprland command: {command}")
            hyprland.send_command(command)
            return False # Ważne dla GLib.timeout_add - wykonaj tylko raz
        except Exception as e:
            print(f"Error focusing window {self.window_data.title} with command: {e}")
            return False # Ważne dla GLib.timeout_add

    def _update_active_state(self, *args):
        """Aktualizuje styl przycisku w zależności od tego, czy okno jest aktywne."""
        if hyprland.active_window and hyprland.active_window.address == self.window_data.address:
            if not self.has_css_class("active"):
                self.add_css_class("active")
        else:
            if self.has_css_class("active"):
                self.remove_css_class("active")
    
    def _on_window_closed(self, *args):
        # print(f"Window {self.window_data.title} (addr: {self.window_data.address}) closed signal received.")
        # Poproś rodzica (RunningAppsBar) o usunięcie tego przycisku
        parent_bar = self.get_parent()
        if isinstance(parent_bar, RunningAppsBar): # Sprawdzenie typu dla bezpieczeństwa
             parent_bar.remove_app_button_by_address(self.window_data.address)
        
        # Rozłącz wszystkie sygnały tego obiektu, aby uniknąć wycieków pamięci
        # if hasattr(self, 'hyprland_active_window_conn'): # Jeśli byłoby indywidualne połączenie
        #    hyprland.disconnect(self.hyprland_active_window_conn)
        if hasattr(self, 'window_closed_conn_id') and self.window_closed_conn_id > 0:
            try:
                self.window_data.disconnect(self.window_closed_conn_id)
            except TypeError: # Czasem GLib może mieć problem, jeśli obiekt już nie istnieje
                pass
        # print(f"Button for {self.window_data.title} should be removed now.")

    def get_window_address(self) -> str:
        return self.window_data.address


class RunningAppsBar(Widget.Box):
    __gtype_name__ = "RunningAppsBar"

    def __init__(self):
        super().__init__(
            css_classes=["running-apps-bar"],
            spacing=3
        )
        self._app_buttons: dict[str, RunningAppButton] = {}
        print("--- RunningAppsBar Initialized (Step 3 - Dynamic Updates & Active State) ---")

        # Połączenie z globalnymi sygnałami Hyprland
        hyprland.connect("window_added", self._on_window_added_or_changed)
        # Nie ma bezpośredniego "window_removed", polegamy na sygnale "closed" z HyprlandWindow
        # oraz na Poll jako fallback
        hyprland.connect("notify::active_window", self._on_active_window_changed)

        self._rebuild_bar_initial() # Zmieniona nazwa dla jasności

        # Utils.Poll do okresowego sprawdzania, czy stan się zgadza (fallback)
        self.poll_task = Utils.Poll(timeout=2000, callback=self._rebuild_bar_if_changed) #

    def _get_filtered_windows(self) -> list[HyprlandWindow]:
        ignored_classes = ["ignis", "eww"] 
        return [
            win for win in hyprland.windows
            if win.pid != -1 and win.mapped and win.title != "" and
               (win.class_name.lower() not in ignored_classes if win.class_name else True)
        ]

    def _on_window_added_or_changed(self, service, window_data: HyprlandWindow):
        """Obsługuje dodanie nowego okna lub zmianę (choć głównie dodanie)."""
        # print(f"Signal window_added: {window_data.title} (Addr: {window_data.address})")
        if window_data.address not in self._app_buttons and \
           window_data.pid != -1 and window_data.mapped and window_data.title != "":
            # print(f"Adding new button for {window_data.title}")
            self._add_app_button(window_data)
        # Aktualizuj stan aktywny dla wszystkich, bo fokus mógł się zmienić
        self._on_active_window_changed()


    def _on_active_window_changed(self, *args):
        """Aktualizuje stan aktywności dla wszystkich przycisków."""
        # print(f"Active window changed: {hyprland.active_window.title if hyprland.active_window else 'None'}")
        for button in self._app_buttons.values():
            button._update_active_state()

    def _add_app_button(self, window_data: HyprlandWindow):
        if window_data.address in self._app_buttons:
            # print(f"Button for {window_data.title} already exists.")
            return
        # print(f"Creating and adding button for: {window_data.title}")
        button = RunningAppButton(window_data)
        self._app_buttons[window_data.address] = button
        self.append(button)
        button._update_active_state() # Upewnij się, że stan jest poprawny od razu

    def remove_app_button_by_address(self, address: str):
        """Usuwa przycisk aplikacji z paska i ze słownika na podstawie adresu."""
        if address in self._app_buttons:
            button_to_remove = self._app_buttons.pop(address) # Usuń ze słownika i pobierz
            self.remove(button_to_remove) # Usuń z UI
            # print(f"Removed button for address {address}")
        # else:
            # print(f"Attempted to remove button for address {address}, but not found.")


    def _rebuild_bar_initial(self):
        """Początkowe zbudowanie paska na podstawie aktualnej listy okien."""
        # print("--- RunningAppsBar: Initial Rebuild ---")
        # Czyszczenie jest ważne przy inicjalizacji, jeśli coś zostało z poprzedniej sesji debugowania
        current_children = list(self.child) 
        for child_widget in current_children:
            self.remove(child_widget)
        self._app_buttons.clear()

        active_windows_data = self._get_filtered_windows()
        # print(f"Initial rebuild: Found {len(active_windows_data)} windows.")
        for window_data in active_windows_data:
            self._add_app_button(window_data)
        self._on_active_window_changed() # Ustaw poprawny aktywny przycisk


    def _rebuild_bar_if_changed(self, *args):
        """Okresowo sprawdza i synchronizuje stan paska z rzeczywistymi oknami (fallback)."""
        # print("--- RunningAppsBar: Poll - Rebuilding if changed ---")
        current_window_addresses_on_bar = set(self._app_buttons.keys())
        actual_filtered_windows_addresses = {win.address for win in self._get_filtered_windows()}

        # Okna do dodania (są w systemie, nie ma ich na pasku)
        to_add = actual_filtered_windows_addresses - current_window_addresses_on_bar
        for addr in to_add:
            window_data = hyprland.get_window_by_address(addr) #
            if window_data: # Upewnij się, że okno nadal istnieje
                # print(f"Poll: Adding missing button for address {addr}")
                self._add_app_button(window_data)

        # Okna do usunięcia (są na pasku, nie ma ich już w systemie/filtrach)
        to_remove = current_window_addresses_on_bar - actual_filtered_windows_addresses
        for addr in to_remove:
            # print(f"Poll: Removing button for vanished window address {addr}")
            self.remove_app_button_by_address(addr)
        
        # Zawsze aktualizuj stan aktywny
        self._on_active_window_changed()
        return True # Dla Utils.Poll, aby kontynuował