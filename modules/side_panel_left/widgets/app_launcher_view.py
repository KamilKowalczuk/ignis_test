# modules/side_panel_left/widgets/app_launcher_view.py
import asyncio
from ignis.widgets import Widget
from ignis.app import IgnisApp
from ignis.services.applications import ApplicationsService, Application, ApplicationAction
from ignis.utils import Utils # Jeśli SearchWebButton będzie używany
# from ignis.menu_model import IgnisMenuModel, IgnisMenuItem, IgnisMenuSeparator # Jeśli menu kontekstowe będzie potrzebne

app = IgnisApp.get_default()
applications = ApplicationsService.get_default()
TERMINAL_FORMAT = "kitty %command%" # Można to przenieść do konfiguracji globalnej

class AppLauncherViewItem(Widget.Button): # Zamiast LauncherAppItem
    def __init__(self, application: Application):
        self._application = application
        # Usunięto menu kontekstowe dla uproszczenia, można dodać później
        super().__init__(
            on_click=self._launch_app,
            css_classes=["app-launcher-view-item", "unset"], # Nowe klasy CSS
            child=Widget.Box(
                spacing=10,
                child=[
                    Widget.Icon(image=application.icon, pixel_size=36), # Dostosuj rozmiar ikony
                    Widget.Label(
                        label=application.name,
                        ellipsize="end",
                        max_width_chars=25, # Dostosuj szerokość
                        css_classes=["app-launcher-view-item-label"],
                        halign="start",
                        hexpand=True,
                    ),
                ]
            )
        )

    def _launch_app(self, _widget):
        self._application.launch(terminal_format=TERMINAL_FORMAT)
        # Po uruchomieniu aplikacji, zamknij panel boczny
        if app.get_window("ignis_SIDE_PANEL_LEFT").visible: # Sprawdź, czy okno istnieje i jest widoczne
            app.close_window("ignis_SIDE_PANEL_LEFT") #

class AppLauncherView(Widget.Box):
    __gtype_name__ = "AppLauncherView"

    def __init__(self):
        self._app_list_container = Widget.Box( # Kontener na listę aplikacji
            vertical=True,
            spacing=5,
            # css_classes=["app-launcher-view-list-container"]
        )
        
        self.search_entry = Widget.Entry(
            hexpand=True,
            placeholder_text="Szukaj aplikacji...",
            css_classes=["app-launcher-view-search-entry"],
            on_change=self._on_search_changed,
            # on_accept=self._on_search_accept, # Można dodać, aby uruchomić pierwszy wynik
            margin_bottom=10, # Odstęp pod polem wyszukiwania
        )

        # Dodajemy Widget.Scroll, aby lista była przewijalna
        app_scroll_window = Widget.Scroll(
            vexpand=True,
            hexpand=True,
            css_classes=["app-launcher-view-scroll"],
            child=self._app_list_container
        )

        super().__init__( # TUTAJ jest wywołanie konstruktora Widget.Box
            vertical=True,
            vexpand=True,
            hexpand=True,
            css_classes=["app-launcher-view"],
            child=[
                Widget.Box( # Kontener dla pola wyszukiwania z ikoną
                    spacing=8,
                    css_classes=["app-launcher-view-search-box"],
                    child=[
                        Widget.Icon(image="system-search-symbolic", pixel_size=20),
                        self.search_entry
                    ]
                ),
                app_scroll_window,
            ]
        )
        self._load_all_apps() # Załaduj wszystkie aplikacje na starcie

    def _load_all_apps(self):
        self._update_app_list(applications.apps)

    def _on_search_changed(self, entry: Widget.Entry):
        query = entry.text.strip()
        if query:
            results = applications.search(applications.apps, query) #
            self._update_app_list(results)
        else:
            self._load_all_apps() # Pokaż wszystkie, jeśli wyszukiwanie puste

    # def _on_search_accept(self, entry: Widget.Entry):
    #     # Uruchom pierwszy element z listy, jeśli istnieje
    #     if self._app_list_container.child:
    #         first_item = self._app_list_container.child[0]
    #         if isinstance(first_item, AppLauncherViewItem):
    #             first_item._launch_app(None)


    def _update_app_list(self, apps_to_display: list[Application]):
        # Czyszczenie poprzednich wyników
        children_to_remove = [child for child in self._app_list_container.child]
        for child_widget in children_to_remove:
            self._app_list_container.remove(child_widget)
            # Można też dodać child_widget.destroy() dla pewności, jeśli nie są od razu usuwane
        
        # Dodawanie nowych wyników
        if apps_to_display:
            for app_data in apps_to_display:
                item_widget = AppLauncherViewItem(app_data)
                self._app_list_container.append(item_widget)
        else:
            self._app_list_container.append(
                Widget.Label(label="Nie znaleziono aplikacji.", halign="center", css_classes=["app-launcher-view-no-results"])
            )