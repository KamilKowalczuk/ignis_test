# modules/side_panel_left/widgets/weather_view.py
import asyncio
import datetime
from gi.repository import GLib, Gtk
from ignis.widgets import Widget
from ignis.app import IgnisApp
from modules.side_panel_left.api import weather_api # Zakładam, że ten plik jest poprawny
from user_options import user_options
from ignis.utils import Utils

app = IgnisApp.get_default()

WEATHER_ICON_MAP = {
    "01d": "weather-clear-symbolic", "01n": "weather-clear-night-symbolic",
    "02d": "weather-few-clouds-symbolic", "02n": "weather-few-clouds-night-symbolic",
    "03d": "weather-clouds-symbolic", "03n": "weather-clouds-night-symbolic",
    "04d": "weather-overcast-symbolic", "04n": "weather-overcast-symbolic",
    "09d": "weather-showers-scattered-symbolic", "09n": "weather-showers-scattered-night-symbolic",
    "10d": "weather-showers-symbolic", "10n": "weather-showers-night-symbolic",
    "11d": "weather-storm-symbolic", "11n": "weather-storm-night-symbolic",
    "13d": "weather-snow-symbolic", "13n": "weather-snow-night-symbolic",
    "50d": "weather-fog-symbolic", "50n": "weather-fog-symbolic",
    "default": "weather-severe-alert-symbolic"
}

class WeatherView(Widget.Box):
    __gtype_name__ = "WeatherView"

    def __init__(self):
        super().__init__(
            vertical=True, vexpand=True, hexpand=True, spacing=15,
            css_classes=["weather-view", "page-content"]
        )
        # ... (inicjalizacja _is_fetching, _current_api_data, _lat, _lon, _city_for_coords) ...
        self._is_fetching = False
        self._current_api_data = None
        self._lat = user_options.weather.latitude
        self._lon = user_options.weather.longitude
        self._city_for_coords = user_options.weather.city_name if self._lat and self._lon else None

        # --- Sekcja wprowadzania miasta ---
        self.city_entry = Widget.Entry( # Tworzymy Entry BEZ on_activate
            placeholder_text="Wpisz miasto lub zostaw puste...",
            hexpand=True,
            css_classes=["weather-city-entry"]
        )
        self.city_entry.connect("activate", self._on_city_entry_activate) # <<<--- PODŁĄCZAMY SYGNAŁ TUTAJ
        
        current_city_from_opts = user_options.weather.city_name
        if current_city_from_opts:
            self.city_entry.text = current_city_from_opts
            
        self.refresh_button = Widget.Button(
            child=Widget.Icon(image="view-refresh-symbolic"),
            tooltip_text="Odśwież dane pogodowe",
            on_click=self._on_refresh_click, # on_click dla Button jest OK jako argument konstruktora
            css_classes=["flat", "circular", "weather-refresh-btn"]
        )
        
        input_box = Widget.Box(spacing=10, css_classes=["weather-input-box"], child=[
            self.city_entry, self.refresh_button
        ])
        self.append(input_box)
        
        # ... (reszta kodu __init__ - definicje i dodawanie pozostałych widgetów UI) ...
        # Upewnij się, że reszta __init__ jest taka sama jak w Twojej działającej wersji
        # (poza tą poprawką dla city_entry)
        self.current_weather_display_box = Widget.Box(vertical=True, spacing=5, css_classes=["current-weather-section", "card"], visible=False)
        self.current_city_time_label = Widget.Label(label="Miasto, Czas", halign="start", css_classes=["weather-city-time"])
        current_main_info_box = Widget.Box(spacing=15, valign="center", halign="center")
        self.current_weather_icon = Widget.Icon(pixel_size=80, css_classes=["weather-current-icon"])
        self.current_temp_label = Widget.Label(label="--°", css_classes=["weather-current-temp"])
        current_main_info_box.append(self.current_weather_icon)
        current_main_info_box.append(self.current_temp_label)
        self.current_desc_label = Widget.Label(label="Pobieranie...", halign="center", css_classes=["weather-current-desc"])
        self.current_feels_like_label = Widget.Label(label="Odczuwalna: --°", halign="center", css_classes=["weather-sub-info"])
        self.current_weather_display_box.append(self.current_city_time_label)
        self.current_weather_display_box.append(current_main_info_box)
        self.current_weather_display_box.append(self.current_desc_label)
        self.current_weather_display_box.append(self.current_feels_like_label)
        self.append(self.current_weather_display_box)

        self.details_grid = Widget.Grid(column_spacing=20, row_spacing=8, css_classes=["weather-details-grid", "card"], visible=False, halign="center")
        self.append(self.details_grid)

        self.daily_forecast_title = Widget.Label(label="Prognoza na kolejne dni", css_classes=["h3", "forecast-title"], halign="center", margin_top=15, visible=False)
        self.daily_forecast_grid = Widget.Grid(
            column_spacing=10, row_spacing=10, css_classes=["daily-forecast-grid"],
            column_homogeneous=True, halign="center"
        )
        self.daily_forecast_scroll = Widget.Scroll(
            child=self.daily_forecast_grid, hscrollbar_policy="never", vscrollbar_policy="automatic",
            css_classes=["daily-forecast-scroll"], visible=False, vexpand=True
        )
        self.append(self.daily_forecast_title)
        self.append(self.daily_forecast_scroll)
        
        self.placeholder_label = Widget.Label(label="Wprowadź miasto lub kliknij odśwież.", vexpand=True, hexpand=True, halign="center", valign="center", css_classes=["placeholder-text"])
        self.append(self.placeholder_label)

        GLib.idle_add(self._request_weather_update, True)
        self.refresh_poll = Utils.Poll(30 * 60 * 1000, self._request_weather_update)

    # ... (reszta metod klasy WeatherView: _request_weather_update, _on_refresh_click, 
    #      _on_city_entry_activate, _fetch_and_populate_weather_data, itd. -
    #      powinny być takie same jak w Twojej ostatniej działającej wersji,
    #      poza ewentualnymi poprawkami, które już wprowadziliśmy) ...
    def _request_weather_update(self, initial_call_or_poll_instance=None):
        is_initial = (initial_call_or_poll_instance is True)
        if self._is_fetching:
            return False if is_initial else True
        self._is_fetching = True
        if is_initial or not self._current_api_data or (isinstance(initial_call_or_poll_instance, Widget.Button)):
            self.placeholder_label.label = f"Pobieranie danych dla: {self.city_entry.text.strip() or user_options.weather.city_name}..."
            self.placeholder_label.visible = True
            self.current_weather_display_box.visible = False
            self.details_grid.visible = False
            self.daily_forecast_title.visible = False
            self.daily_forecast_scroll.visible = False
        asyncio.ensure_future(self._fetch_and_populate_weather_data())
        return False if is_initial else True

    def _on_refresh_click(self, _widget):
        if self._is_fetching: return 
        self.placeholder_label.label = "Odświeżanie..."
        self.placeholder_label.visible = True
        self.current_weather_display_box.visible = False
        self.details_grid.visible = False
        self.daily_forecast_title.visible = False
        self.daily_forecast_scroll.visible = False
        self._clear_daily_forecast_ui()
        self._clear_details_grid()
        self._is_fetching = True
        asyncio.ensure_future(self._fetch_and_populate_weather_data())

    def _on_city_entry_activate(self, entry: Widget.Entry):
        city_name = entry.text.strip()
        if city_name and city_name != self._city_for_coords:
            self._lat = None 
            self._lon = None
            self._city_for_coords = city_name 
        elif not city_name:
            self._city_for_coords = user_options.weather.city_name
            self._lat = user_options.weather.latitude
            self._lon = user_options.weather.longitude
        self._on_refresh_click(None) # Wywołaj logikę odświeżania
    
    async def _fetch_and_populate_weather_data(self):
        new_api_data = None; error_to_show = None
        city_for_display = self.city_entry.text.strip() or user_options.weather.city_name or "Twoja lokalizacja"
        try:
            api_key = weather_api.get_api_key()
            if not api_key:
                error_to_show = "Brak klucza API."
                raise Exception(error_to_show)
            lat_to_use = self._lat; lon_to_use = self._lon
            city_from_options = user_options.weather.city_name
            current_input_city = self.city_entry.text.strip()
            if not lat_to_use or not lon_to_use or \
               (current_input_city and current_input_city != self._city_for_coords) or \
               (not current_input_city and self._city_for_coords != city_from_options):
                city_to_geocode = current_input_city or city_from_options
                if not city_to_geocode:
                    error_to_show = "Brak miasta do geolokalizacji."
                    raise Exception(error_to_show)
                lat_to_use, lon_to_use = await weather_api.get_coordinates_async(city_to_geocode)
                if lat_to_use and lon_to_use:
                    self._lat = lat_to_use; self._lon = lon_to_use; self._city_for_coords = city_to_geocode
                    city_for_display = city_to_geocode 
                else:
                    error_to_show = f"Nie można znaleźć współrzędnych dla: {city_to_geocode}"
                    raise Exception(error_to_show)
            if not lat_to_use or not lon_to_use:
                error_to_show = "Brak współrzędnych."
                raise Exception(error_to_show)
            
            new_api_data = await weather_api.fetch_onecall_api_data(lat_to_use, lon_to_use)

            if not new_api_data or ("current" not in new_api_data or "daily" not in new_api_data):
                msg = new_api_data.get("message") if isinstance(new_api_data, dict) else "Nie udało się pobrać pełnych danych."
                error_to_show = f"Błąd API: {msg}" if msg else "Niekompletne dane pogodowe."
                new_api_data = None
        except Exception as e:
            if not error_to_show: error_to_show = str(e) or type(e).__name__
        finally:
            self._is_fetching = False
            GLib.idle_add(self._update_ui_after_fetch, new_api_data, city_for_display, error_to_show)

    def _update_ui_after_fetch(self, api_data, city_name_used, error_message_from_fetch=None):
        if error_message_from_fetch or not api_data:
            self._show_error(error_message_from_fetch or "Nieznany błąd.")
            return False
        self.placeholder_label.visible = False
        self._current_api_data = api_data
        current_data = weather_api.get_current_weather(self._current_api_data)
        daily_forecast_list = weather_api.get_daily_forecast(self._current_api_data, days=7)
        if current_data:
            self.current_weather_display_box.visible = True
            self._update_current_weather_section(current_data, city_name_used)
            self.details_grid.visible = True
        else:
            self.current_weather_display_box.visible = False; self.details_grid.visible = False
        if daily_forecast_list:
            self.daily_forecast_title.visible = True
            self.daily_forecast_scroll.visible = True
            self._update_daily_forecast_section(daily_forecast_list)
        else:
            self.daily_forecast_title.visible = False
            self.daily_forecast_scroll.visible = False
        if not current_data and not daily_forecast_list: self._show_error("Brak danych pogodowych.")
        return False

    def _show_error(self, message: str):
        self.placeholder_label.label = message if message else "Wystąpił nieznany błąd."
        self.placeholder_label.visible = True
        self.current_weather_display_box.visible = False; self.details_grid.visible = False
        self.daily_forecast_title.visible = False; self.daily_forecast_scroll.visible = False
        self._clear_details_grid(); self._clear_daily_forecast_ui()
        return False

    def _update_current_weather_section(self, current_data: dict, city_name_for_display: str):
        current_dt = current_data.get("dt"); time_str = datetime.datetime.fromtimestamp(current_dt).strftime("%H:%M") if current_dt else datetime.datetime.now().strftime("%H:%M")
        self.current_city_time_label.label = f"{city_name_for_display}, {time_str}"
        if "weather" in current_data and current_data["weather"]:
            icon_code = current_data["weather"][0].get("icon"); self.current_weather_icon.image = WEATHER_ICON_MAP.get(icon_code, WEATHER_ICON_MAP["default"])
            self.current_desc_label.label = current_data["weather"][0].get("description", "").capitalize()
        temp = current_data.get("temp"); self.current_temp_label.label = f"{float(temp):.0f}°C" if temp is not None else "--°"
        feels_like = current_data.get("feels_like"); self.current_feels_like_label.label = f"Odczuwalna: {float(feels_like):.0f}°C" if feels_like is not None else "Odczuwalna: --°"
        self._build_details_grid(current_data)

    def _build_details_grid(self, current_data: dict):
        self._clear_details_grid()
        details = []
        if "humidity" in current_data: details.append(("Wilgotność", f"{current_data['humidity']}%"))
        if "pressure" in current_data: details.append(("Ciśnienie", f"{current_data['pressure']} hPa"))
        if "wind_speed" in current_data:
            wind_speed_kmh = current_data['wind_speed'] * 3.6; deg = current_data.get('wind_deg')
            wind_str = f"{wind_speed_kmh:.1f} km/h"; 
            if deg is not None: wind_str += f" ({self._deg_to_compass(deg)})"
            details.append(("Wiatr", wind_str))
        if "uvi" in current_data: details.append(("Indeks UV", f"{current_data['uvi']:.1f}"))
        if "sunrise" in current_data: details.append(("Wschód słońca", datetime.datetime.fromtimestamp(current_data['sunrise']).strftime("%H:%M")))
        if "sunset" in current_data: details.append(("Zachód słońca", datetime.datetime.fromtimestamp(current_data['sunset']).strftime("%H:%M")))
        row = 0
        for i, (label_text, value_text) in enumerate(details):
            label = Widget.Label(label=label_text, halign="end", css_classes=["weather-detail-label"])
            value = Widget.Label(label=value_text, halign="start", css_classes=["weather-detail-value"], selectable=True)
            self.details_grid.attach(label, 0, row, 1, 1); self.details_grid.attach(value, 1, row, 1, 1); row += 1
            
    def _deg_to_compass(self, degrees: int | float) -> str:
        val = int((float(degrees)/22.5)+.5); arr = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]; return arr[(val % 16)]

    def _update_daily_forecast_section(self, daily_data_list: list):
        self._clear_daily_forecast_ui()
        days_to_show = min(len(daily_data_list), 6)
        for i in range(days_to_show):
            day_data = daily_data_list[i]
            day_box = self._create_daily_forecast_item(day_data, i == 0)
            column = i % 2
            row = i // 2
            self.daily_forecast_grid.attach(day_box, column, row, 1, 1)

    def _create_daily_forecast_item(self, day_data: dict, is_today: bool) -> Widget.Box:
        timestamp = day_data.get("dt")
        if timestamp:
            date_obj = datetime.datetime.fromtimestamp(timestamp)
            if is_today: day_name_str = "Dziś"
            else: days_pl_short = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"]; day_name_str = days_pl_short[date_obj.weekday()]
        else: day_name_str = "Dzień"
        temp_data = day_data.get("temp", {}); min_temp = temp_data.get("min"); max_temp = temp_data.get("max")
        weather_info = day_data.get("weather", [{}])[0]; icon_code = weather_info.get("icon", "default")
        item_box = Widget.Box(vertical=True, spacing=4, css_classes=["daily-forecast-item"], valign="start")
        item_box.append(Widget.Label(label=day_name_str, css_classes=["forecast-day-name"], halign="center"))
        item_box.append(Widget.Icon(image=WEATHER_ICON_MAP.get(icon_code, WEATHER_ICON_MAP["default"]), pixel_size=40, halign="center", margin_top=4, margin_bottom=4))
        if min_temp is not None and max_temp is not None:
            item_box.append(Widget.Label(label=f"{float(max_temp):.0f}°/{float(min_temp):.0f}°", css_classes=["forecast-day-temp"], halign="center"))
        pop = day_data.get("pop", 0) 
        if pop > 0.05:
             pop_label = Widget.Label(label=f"{pop*100:.0f}%", css_classes=["forecast-pop"], halign="center")
             pop_label.set_tooltip_text(f"Szansa opadów: {pop*100:.0f}%")
             item_box.append(pop_label)
        return item_box

    def _clear_daily_forecast_ui(self):
        children = [child for child in self.daily_forecast_grid.child]
        for child in children:
            self.daily_forecast_grid.remove(child); child.destroy()

    def _clear_details_grid(self):
        children = [child for child in self.details_grid.child]
        for child in children:
            self.details_grid.remove(child)

    def _create_section_box(self, title: str) -> Widget.Box:
        title_label = Widget.Label(label=title, halign="start", css_classes=["h2", "section-title"])
        section_box = Widget.Box(vertical=True, spacing=5, css_classes=["info-section"])
        section_box.append(title_label)
        section_box.append(Widget.Separator(margin_top=3, margin_bottom=6))
        return section_box