# modules/bar/widgets/weather_bar_widget.py
import asyncio
from gi.repository import GLib, Gtk
from ignis.widgets import Widget
from ignis.app import IgnisApp
from ignis.utils import Utils
from modules.side_panel_left.api import weather_api # Używamy naszego API
from modules.side_panel_left.widgets.weather_view import WEATHER_ICON_MAP # Współdzielimy mapę ikon
from modules.side_panel_left.state import active_view_in_left_panel # Do ustawiania widoku
from user_options import user_options

app = IgnisApp.get_default()

class WeatherBarWidget(Widget.Button): # Robimy go klikalnym Widget.Button
    __gtype_name__ = "WeatherBarWidget"

    def __init__(self, monitor_id: int):
        super().__init__(
            on_click=self._on_click,
            css_classes=["weather-bar-widget", "bar-button", "unset"] # Dodajemy style
        )
        self.monitor_id = monitor_id # Monitor, na którym ma się otwierać panel boczny
        self._is_fetching = False
        
        # Wewnętrzny Box na ikonę i temperaturę
        self.content_box = Widget.Box(spacing=0, halign="center", valign="center")
        self.icon_widget = Widget.Icon(pixel_size=20) # Mniejsza ikona na pasek
        self.temp_label = Widget.Label(label="--°")

        self.content_box.append(self.icon_widget)
        self.content_box.append(self.temp_label)
        self.child = self.content_box # Ustawiamy content_box jako dziecko przycisku

        # Inicjalizacja danych (lat/lon) - podobnie jak w WeatherView
        self._lat = user_options.weather.latitude
        self._lon = user_options.weather.longitude
        self._city_for_coords = user_options.weather.city_name if self._lat and self._lon else None

        # Pierwsze pobranie i cykliczne odświeżanie
        GLib.idle_add(self._request_weather_update, True) # True dla initial_call
        # Odświeżanie co 30 minut (tak jak WeatherView, lub częściej, jeśli chcesz)
        self.refresh_poll = Utils.Poll(30 * 60 * 1000, self._request_weather_update)
        # print(f"WeatherBarWidget for monitor {monitor_id} initialized.")

    def _on_click(self, _widget):
        # print(f"WeatherBarWidget clicked on monitor {self.monitor_id}")
        try:
            panel_window = app.get_window("ignis_SIDE_PANEL_LEFT")
            
            # Zawsze ustawiamy widok na pogodę
            active_view_in_left_panel.value = "weather_view"
            
            panel_window.props.monitor = self.monitor_id
            app.open_window("ignis_SIDE_PANEL_LEFT") # Zawsze otwieramy/pokazujemy
            
        except Exception as e:
            print(f"Error in WeatherBarWidget _on_click: {e}")

    def _request_weather_update(self, initial_call_or_poll_instance=None):
        is_initial = (initial_call_or_poll_instance is True)
        if self._is_fetching and not is_initial: # Pozwól na initial_call nawet jeśli trwa inne pobieranie
            return False if is_initial else True

        self._is_fetching = True
        asyncio.ensure_future(self._fetch_and_update_ui())
        return False if is_initial else True

    async def _fetch_and_update_ui(self):
        # print(f"WeatherBarWidget: Fetching weather for monitor {self.monitor_id}")
        current_weather_data = None
        error_to_show = None
        
        try:
            api_key = weather_api.get_api_key()
            if not api_key:
                raise Exception("Brak klucza API")

            # Użyj zapisanych lub pobierz nowe koordynaty
            lat_to_use = self._lat
            lon_to_use = self._lon
            city_to_use = self._city_for_coords or user_options.weather.city_name

            if not lat_to_use or not lon_to_use or \
               (city_to_use and city_to_use != self._city_for_coords): # Jeśli miasto się zmieniło lub brak koordynatów
                
                city_to_geocode = city_to_use
                if not city_to_geocode: # Jeśli nie ma miasta ani w cache ani w opcjach
                    city_to_geocode = "Lublin" # Fallback, jeśli wszystko inne zawiedzie

                # print(f"WeatherBarWidget: Geocoding for {city_to_geocode}")
                lat_to_use, lon_to_use = await weather_api.get_coordinates_async(city_to_geocode)
                if lat_to_use and lon_to_use:
                    self._lat = lat_to_use
                    self._lon = lon_to_use
                    self._city_for_coords = city_to_geocode
                else:
                    raise Exception(f"Nie można znaleźć współrzędnych dla {city_to_geocode}")
            
            if not lat_to_use or not lon_to_use:
                 raise Exception("Brak współrzędnych")

            # Pobierz tylko aktualną pogodę z One Call API
            # Możemy dodać do weather_api.py nową funkcję lub zmodyfikować istniejącą,
            # aby pobierała tylko sekcję "current"
            # Na razie użyjemy istniejącej i weźmiemy tylko 'current'
            one_call_data = await weather_api.fetch_onecall_api_data(lat_to_use, lon_to_use)

            if one_call_data and "current" in one_call_data:
                current_weather_data = weather_api.get_current_weather(one_call_data)
            else:
                msg = one_call_data.get("message") if isinstance(one_call_data, dict) else "Błąd pobierania"
                raise Exception(msg)

        except Exception as e:
            # print(f"WeatherBarWidget: Error fetching weather: {e}")
            error_to_show = str(e)
        finally:
            self._is_fetching = False
            GLib.idle_add(self._update_display_values, current_weather_data, error_to_show)
    
    def _update_display_values(self, current_data, error=None):
        if error or not current_data:
            # print(f"WeatherBarWidget: Error updating display - {error}")
            self.icon_widget.image = WEATHER_ICON_MAP["default"]
            self.temp_label.label = "N/A"
            self.set_tooltip_text(f"Błąd pogody: {error or 'Nieznany'}")
            return False

        try:
            temp = current_data.get("temp")
            icon_code = current_data.get("weather", [{}])[0].get("icon", "default")
            description = current_data.get("weather", [{}])[0].get("description", "").capitalize()
            city_name = self._city_for_coords or user_options.weather.city_name

            self.icon_widget.image = WEATHER_ICON_MAP.get(icon_code, WEATHER_ICON_MAP["default"])
            self.temp_label.label = f"{float(temp):.0f}°" if temp is not None else "--°"
            self.set_tooltip_text(f"{city_name}: {description}, {float(temp):.0f}°C")
        except Exception as e:
            # print(f"WeatherBarWidget: Error processing weather data for UI: {e}")
            self.icon_widget.image = WEATHER_ICON_MAP["default"]
            self.temp_label.label = "Err"
            self.set_tooltip_text("Błąd przetwarzania danych")
        return False