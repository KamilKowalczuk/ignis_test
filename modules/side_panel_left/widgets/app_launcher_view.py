import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, GLib, Gdk
from collections import defaultdict
import subprocess
import os
import re

from ignis.app import IgnisApp
from ignis.services.applications import Application, ApplicationsService

app = IgnisApp.get_default()
applications = ApplicationsService.get_default()

# --- Klasy AppGridItem i AllAppsGrid (bez zmian) ---
class AppGridItem(Gtk.Box):
    def __init__(self, application: Application, **kwargs):
        super().__init__(**kwargs, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_css_classes(["app-grid-item"])
        self.set_valign(Gtk.Align.START)
        self._application = application
        icon = Gtk.Image(icon_name=application.icon, icon_size=Gtk.IconSize.LARGE, pixel_size=48)
        label = Gtk.Label(label=application.name, ellipsize="end", justify="center", wrap=True, wrap_mode="char", width_chars=12)
        self.append(icon)
        self.append(label)
        click_gesture = Gtk.GestureClick.new()
        click_gesture.connect("released", self._on_click)
        self.add_controller(click_gesture)
    def _on_click(self, gesture, n_press, x, y):
        if self._application:
            self._application.launch()
            app.get_window("ignis_SIDE_PANEL_LEFT").set_visible(False)
    def matches_query(self, query: str) -> bool:
        if not query: return True
        app_obj = self._application
        keywords = app_obj.keywords or []
        return query in app_obj.name.lower() or (app_obj.description and query in app_obj.description.lower()) or any(query in kw.lower() for kw in keywords)

class AllAppsGrid(Gtk.ScrolledWindow):
    def __init__(self, search_entry: Gtk.SearchEntry, **kwargs):
        super().__init__(**kwargs, hexpand=True, vexpand=True)
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._search_entry = search_entry
        self._search_timeout_id = None
        self.flowbox = Gtk.FlowBox(valign=Gtk.Align.START, max_children_per_line=5, min_children_per_line=3, selection_mode=Gtk.SelectionMode.SINGLE)
        self.flowbox.set_css_classes(["app-grid"])
        self.set_child(self.flowbox)
        for app_obj in sorted(applications.apps, key=lambda app: app.name.lower()):
            item = AppGridItem(application=app_obj)
            self.flowbox.append(item)
        self._search_entry.connect("search-changed", self._on_search_changed)
        self.flowbox.connect("child-activated", self._on_child_activated)
    def _on_child_activated(self, flowbox, child_wrapper):
        item = child_wrapper.get_child()
        if isinstance(item, AppGridItem): item._on_click(None, None, None, None)
    def _on_search_changed(self, entry):
        if self._search_timeout_id: GLib.source_remove(self._search_timeout_id)
        self._search_timeout_id = GLib.timeout_add(150, self._perform_filter, entry)
    def _perform_filter(self, entry):
        query = entry.get_text().strip().lower()
        first_visible_child = None
        for child_wrapper in self.flowbox:
            actual_item = child_wrapper.get_child()
            if isinstance(actual_item, AppGridItem):
                is_visible = actual_item.matches_query(query)
                child_wrapper.set_visible(is_visible)
                if is_visible and not first_visible_child: first_visible_child = child_wrapper
        if first_visible_child: self.flowbox.select_child(first_visible_child)
        self._search_timeout_id = None
        return GLib.SOURCE_REMOVE

# --- NOWA, DOPRACOWANA WERSJA WIDOKU KATEGORII ---
class CategoriesView(Gtk.ScrolledWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.set_css_classes(["categories-view"])
        
        self.expanders = []
        
        # Słownik do tłumaczenia kategorii
        self.translation_map = {
            "AudioVideo": "Dźwięk i wideo", "Audio": "Dźwięk", "Video": "Wideo",
            "Development": "Programowanie", "Education": "Edukacja", "Game": "Gry",
            "Graphics": "Grafika", "Network": "Internet", "Office": "Biurowe",
            "Settings": "Ustawienia", "System": "Systemowe", "Utility": "Narzędzia",
            "Other": "Inne"
        }

        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_child(container)

        # Pasek z przyciskami do rozwijania/zwijania
        action_bar = Gtk.Box(halign="end", spacing=6)
        action_bar.set_css_classes(["categories-action-bar"])
        
        expand_button = Gtk.Button(icon_name="view-more-symbolic", tooltip_text="Rozwiń wszystko")
        expand_button.connect("clicked", self._on_toggle_all, True)
        
        collapse_button = Gtk.Button(icon_name="view-less-symbolic", tooltip_text="Zwiń wszystko")
        collapse_button.connect("clicked", self._on_toggle_all, False)
        
        action_bar.append(expand_button)
        action_bar.append(collapse_button)
        container.append(action_bar)

        # Logika grupowania i tworzenia expanderów
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        container.append(main_box)

        categorized_apps = defaultdict(list)
        for app in applications.apps:
            app_info = Gio.DesktopAppInfo.new(app.id)
            if not app_info: continue
            app_categories = app_info.get_categories() or ""
            category_en = app_categories.split(';')[0] if app_categories else "Other"
            if not category_en: category_en = "Other"
            
            # Tłumaczenie i grupowanie
            category_pl = self.translation_map.get(category_en, category_en)
            categorized_apps[category_pl].append(app)

        sorted_categories = sorted(categorized_apps.keys(), key=lambda k: (k == "Inne", k.lower()))

        for category in sorted_categories:
            apps_in_category = categorized_apps[category]
            expander = Gtk.Expander(label=f"{category} ({len(apps_in_category)})")
            expander.set_css_classes(["category-expander"])
            self.expanders.append(expander) # Dodanie do listy do zarządzania
            
            flowbox = Gtk.FlowBox(valign=Gtk.Align.START, max_children_per_line=5, min_children_per_line=3, selection_mode=Gtk.SelectionMode.NONE)
            flowbox.set_css_classes(["app-grid", "category-app-grid"])
            for app_item in sorted(apps_in_category, key=lambda a: a.name.lower()):
                item = AppGridItem(application=app_item)
                flowbox.append(item)
            expander.set_child(flowbox)
            main_box.append(expander)

    def _on_toggle_all(self, button, expand: bool):
        for expander in self.expanders:
            expander.set_expanded(expand)

# --- Główna klasa launchera ---
class AppLauncherView(Gtk.Box):
    __gtype_name__ = "AppLauncherView"

    def __init__(self, **kwargs):
        super().__init__(**kwargs, orientation=Gtk.Orientation.VERTICAL, spacing=10, vexpand=True, hexpand=True)
        self.set_css_classes(["app-launcher-view"])
        search_entry = Gtk.SearchEntry(placeholder_text="Szukaj aplikacji...", hexpand=True)
        self.connect("map", lambda *_: search_entry.grab_focus())
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        search_entry.add_controller(key_controller)
        
        stack_switcher = Gtk.StackSwitcher()
        stack = Gtk.Stack()
        stack_switcher.set_stack(stack)
        
        self.all_apps_grid = AllAppsGrid(search_entry)
        stack.add_titled(self.all_apps_grid, "all-apps", "Wszystkie")
        
        categories_view = CategoriesView()
        stack.add_titled(categories_view, "categories", "Kategorie")
        
        # USUNIĘCIE FILARU 3: Koniec z Centrum Zarządzania
        
        self.append(search_entry)
        self.append(stack_switcher)
        self.append(stack)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Down:
            self.all_apps_grid.flowbox.grab_focus()
            return True
        if keyval == Gdk.KEY_Escape:
            try:
                window = app.get_window("ignis_SIDE_PANEL_LEFT")
                window.set_visible(False)
            except Exception: pass
            return True
        return False