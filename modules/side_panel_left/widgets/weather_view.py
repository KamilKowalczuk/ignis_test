# modules/side_panel_left/widgets/weather_view.py
import json
import asyncio
from gi.repository import GLib
from ignis.widgets import Widget
from ignis.utils import Utils
from user_options import user_options

# WEATHER_ICON_MAP (bez zmian, jak poprzednio)
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
            vertical=True, vexpand=True, hexpand=True, spacing=10,
            css_classes=["weather-view"]
            # Padding ustawiamy w CSS: .weather-view { padding: 0.75rem; }
        )
        print("WeatherView: __init__ called")
        
        self.city_label = Widget.Label(label="Ładowanie lokalizacji...", css_classes=["weather-city-label"], halign="center")
        self.weather_icon = Widget.Icon(pixel_size=96, css_classes=["weather-main-icon"], halign="center")
        self.temp_label = Widget.Label(label="--°", css_classes=["weather-temp-label"], halign="center") # Usunięto jednostkę, dodamy w _update_ui
        self.description_label = Widget.Label(label="Pobieranie opisu...", css_classes=["weather-description-label"], halign="center")
        self.details_grid = Widget.Grid(column_spacing=15, row_spacing=8, css_classes=["weather-details-grid"], halign="center")

        self.append(self.city_label)
        self.append(self.weather_icon)
        self.append(self.temp_label)
        self.append(self.description_label)
        self.append(Widget.Separator(margin_top=10, margin_bottom=10))
        self.append(self.details_grid)
        
        refresh_button = Widget.Button(
            label="Odśwież pogodę", # Zmieniono etykietę dla jasności
            on_click=self._on_refresh_click, # Użyjemy dedykowanej metody
            halign="center", margin_top=10, css_classes=["weather-refresh-button"]
        )
        self.append(refresh_button)

        self.refresh_poll = Utils.Poll(30 * 60 * 1000, self.fetch_weather_data) # 30 minut
        
        print("WeatherView: Scheduling initial fetch_weather_data via idle_add")
        GLib.idle_add(self._init_fetch_wrapper) # Opakowujemy wywołanie async

    def _init_fetch_wrapper(self):
        print("WeatherView: _init_fetch_wrapper called by idle_add")
        asyncio.ensure_future(self.fetch_weather_data())
        return False # Wykonaj idle_add tylko raz

    def _on_refresh_click(self, _widget):
        print("WeatherView: Refresh button clicked")
        self.description_label.label = "Odświeżanie..."
        self.weather_icon.image = "view-refresh-symbolic" # Ikona odświeżania
        asyncio.ensure_future(self.fetch_weather_data())


    def _build_details_grid(self, weather_data: dict):
        # ... (kod bez zmian, jak w poprzedniej odpowiedzi)
        children_to_remove = [child for child in self.details_grid.child]
        for child_widget in children_to_remove:
            self.details_grid.remove(child_widget)
        details = []
        if "main" in weather_data:
            if "feels_like" in weather_data["main"]: details.append(("Odczuwalna", f"{weather_data['main']['feels_like']:.0f}°C"))
            if "humidity" in weather_data["main"]: details.append(("Wilgotność", f"{weather_data['main']['humidity']}%"))
            if "pressure" in weather_data["main"]: details.append(("Ciśnienie", f"{weather_data['main']['pressure']} hPa"))
        if "wind" in weather_data and "speed" in weather_data["wind"]:
            wind_speed_kmh = weather_data['wind']['speed'] * 3.6
            details.append(("Wiatr", f"{wind_speed_kmh:.1f} km/h"))
        if "visibility" in weather_data:
            visibility_km = weather_data['visibility'] / 1000
            details.append(("Widoczność", f"{visibility_km:.1f} km"))
        row = 0
        for i, (label_text, value_text) in enumerate(details):
            label = Widget.Label(label=label_text + ":", halign="end", css_classes=["weather-detail-label"])
            value = Widget.Label(label=value_text, halign="start", css_classes=["weather-detail-value"])
            current_col = 0 if i < (len(details) + 1) // 2 else 1
            current_row_for_grid = row # Zmieniono nazwę zmiennej, aby uniknąć konfliktu z 'row' pętli
            self.details_grid.attach(label, 0 + current_col * 2, current_row_for_grid, 1, 1)
            self.details_grid.attach(value, 1 + current_col * 2, current_row_for_grid, 1, 1)
            if current_col == 1 or i == len(details) -1 : row += 1


    async def fetch_weather_data(self, poll_instance=None): # Akceptuje argument z Poll
        print("WeatherView: fetch_weather_data called")
        api_key = user_options.weather.api_key
        city = user_options.weather.city_name
        units = user_options.weather.units
        lang = user_options.weather.language
        print(f"WeatherView: Using API_KEY='{api_key[:5]}...' (first 5 chars), CITY='{city}', UNITS='{units}', LANG='{lang}'")


        if not api_key:
            print("WeatherView: API key is missing!")
            self.city_label.label = "Brak klucza API!"
            self.temp_label.label = "N/A"
            self.description_label.label = "Skonfiguruj klucz API w opcjach."
            self.weather_icon.image = WEATHER_ICON_MAP["default"]
            return

        if not city:
            print("WeatherView: City name is missing!")
            self.city_label.label = "Brak lokalizacji!"
            self.temp_label.label = "N/A"
            self.description_label.label = "Ustaw miasto w opcjach."
            self.weather_icon.image = WEATHER_ICON_MAP["default"]
            return

        # Ustawianie etykiet przed zapytaniem
        GLib.idle_add(self.city_label.set_property, "label", f"Pogoda dla: {city}")
        GLib.idle_add(self.description_label.set_property, "label", "Pobieranie danych...")
        GLib.idle_add(self.temp_label.set_property, "label", "--°")
        GLib.idle_add(self.weather_icon.set_property, "image", "dialog-information-symbolic")


        url = f"https://api.openweathermap.org/data/2.5/forecast?lat=51,2513&lon=22,5414&appid=463be7bb2d9ff2fe372b2bbe21abc3ee"
        print(f"WeatherView: Fetching from URL: {url}")

        try:
            response_bytes = await Utils.read_file_async(uri=url)
            
            if response_bytes:
                print(f"WeatherView: Received response_bytes, length: {len(response_bytes)}")
                response_str = response_bytes.decode('utf-8')
                # print(f"WeatherView: Decoded response_str (first 500 chars): {response_str[:500]}")
                weather_data = json.loads(response_str)
                print(f"WeatherView: Parsed weather_data (cod: {weather_data.get('cod')})")
                
                if weather_data.get("cod") == 200:
                    GLib.idle_add(self._update_ui, weather_data)
                else:
                    error_message = weather_data.get("message", "Nieznany błąd API OpenWeatherMap")
                    print(f"WeatherView: API Error from JSON ({weather_data.get('cod')}): {error_message}")
                    GLib.idle_add(self.description_label.set_property, "label", f"Błąd API: {error_message}")
                    GLib.idle_add(self.weather_icon.set_property, "image", WEATHER_ICON_MAP["default"])
            else:
                print("WeatherView: No response_bytes received from Utils.read_file_async.")
                GLib.idle_add(self.description_label.set_property, "label", "Błąd: Brak odpowiedzi z serwera.")
                GLib.idle_add(self.weather_icon.set_property, "image", WEATHER_ICON_MAP["default"])

        except json.JSONDecodeError as jde:
            print(f"WeatherView: JSONDecodeError: {jde}. Response was: {response_str[:500] if 'response_str' in locals() else 'N/A'}")
            GLib.idle_add(self.description_label.set_property, "label", "Błąd: Niepoprawny format danych od API.")
            GLib.idle_add(self.weather_icon.set_property, "image", WEATHER_ICON_MAP["default"])
        except UnicodeDecodeError as ude:
            print(f"WeatherView: UnicodeDecodeError: {ude}. Response might not be UTF-8.")
            GLib.idle_add(self.description_label.set_property, "label", "Błąd: Problem z kodowaniem odpowiedzi API.")
            GLib.idle_add(self.weather_icon.set_property, "image", WEATHER_ICON_MAP["default"])
        except Exception as e:
            print(f"WeatherView: General Exception in fetch_weather_data: {type(e).__name__} - {e}")
            GLib.idle_add(self.description_label.set_property, "label", f"Błąd pobierania: {type(e).__name__}")
            GLib.idle_add(self.weather_icon.set_property, "image", WEATHER_ICON_MAP["default"])


    def _update_ui(self, data: dict, user_data=None): # Dodano user_data dla GLib.idle_add
        print("WeatherView: _update_ui called with data")
        try:
            if "name" in data:
                self.city_label.label = data["name"]
            
            if "weather" in data and len(data["weather"]) > 0:
                main_weather = data["weather"][0]
                self.description_label.label = main_weather.get("description", "Brak opisu").capitalize()
                icon_code = main_weather.get("icon", "default")
                self.weather_icon.image = WEATHER_ICON_MAP.get(icon_code, WEATHER_ICON_MAP["default"])
            else:
                self.description_label.label = "Brak danych o pogodzie"
                self.weather_icon.image = WEATHER_ICON_MAP["default"]

            if "main" in data and "temp" in data["main"]:
                temp_unit = "°C" if user_options.weather.units == "metric" else ("°F" if user_options.weather.units == "imperial" else " K") # Spacja przed K
                self.temp_label.label = f"{data['main']['temp']:.0f}{temp_unit}"
            else:
                self.temp_label.label = "--°" # Domyślna wartość, jeśli brak danych
            
            self._build_details_grid(data)
            print("WeatherView: UI updated successfully.")
        except Exception as e:
            print(f"WeatherView: Error updating weather UI: {e}")
            self.description_label.label = "Błąd wewnętrzny aktualizacji UI."
        return False # Dla GLib.idle_add