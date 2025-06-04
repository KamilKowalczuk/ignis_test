# modules/side_panel_left/api/weather_api.py
import json
import os
import time
import asyncio # Potrzebne dla async/await
from user_options import user_options # Importujemy opcje użytkownika
from ignis.utils import Utils # Dla asynchronicznych zapytań sieciowych

# Lokalizacja cache (bez zmian)
CACHE_PATH = os.path.expanduser("~/.cache/ignis_weather.json")
CACHE_TTL = 1800  # 30 minut

# Domyślne współrzędne - Lublin (bez zmian)
DEFAULT_LAT = 51.2465
DEFAULT_LON = 22.5684

def get_api_key():
    """Pobiera klucz API z user_options."""
    key = user_options.weather.api_key
    if not key or key == "APIKEY": # Sprawdź, czy nie jest to placeholder
        print("[weather_api] KLUCZ API NIE JEST USTAWIONY W user_options.py!")
        return None
    return key

def get_cached_weather():
    # ... (logika bez zmian) ...
    if not os.path.exists(CACHE_PATH):
        return None
    try:
        with open(CACHE_PATH, "r") as f:
            data = json.load(f)
            if time.time() - data.get("timestamp", 0) < CACHE_TTL:
                # print("[weather_api] Zwracam dane z cache")
                return data["weather"]
    except Exception as e:
        print(f"[weather_api] Błąd odczytu cache: {e}")
        return None
    # print("[weather_api] Cache nieaktualny lub brak")
    return None

def save_cache(weather_data):
    # ... (logika bez zmian) ...
    try:
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True) # Upewnij się, że katalog cache istnieje
        with open(CACHE_PATH, "w") as f:
            json.dump({
                "timestamp": time.time(),
                "weather": weather_data
            }, f)
        # print("[weather_api] Zapisano dane do cache")
    except Exception as e:
        print(f"[weather_api] Błąd zapisu do cache: {e}")
        pass

async def fetch_onecall_api_data(lat, lon):
    """Asynchronicznie pobiera dane z One Call API 3.0."""
    API_KEY = get_api_key()
    if not API_KEY:
        return None

    url = "https://api.openweathermap.org/data/3.0/onecall"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY,
        "units": user_options.weather.units,
        "lang": user_options.weather.language,
        "exclude": "minutely,alerts" # Pobieramy current, hourly, daily
    }
    # Budowanie URL z parametrami
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    full_url = f"{url}?{query_string}"
    
    # print(f"[weather_api] Fetching OneCall data from: {full_url}")
    try:
        response_data = await Utils.read_file_async(uri=full_url)
        if response_data:
            response_str = response_data.decode('utf-8') if isinstance(response_data, bytes) else response_data
            data = json.loads(response_str)
            # OneCall API nie zawsze zwraca 'cod' na głównym poziomie dla sukcesu.
            # Sprawdzamy obecność kluczowych pól.
            if "current" in data and "daily" in data:
                save_cache(data)
                return data
            else:
                print(f"[weather_api] Błąd w odpowiedzi OneCallAPI: {data.get('message', 'Niekompletne dane')}")
                return None
        else:
            print("[weather_api] Brak odpowiedzi z OneCallAPI")
            return None
    except Exception as e:
        print(f"[weather_api] Błąd pobierania danych z OneCallAPI: {e}")
        return None

async def get_coordinates_async(city_name: str):
    """Asynchronicznie pobiera współrzędne dla miasta."""
    API_KEY = get_api_key()
    if not API_KEY:
        return None, None
        
    url = "http://api.openweathermap.org/geo/1.0/direct"
    params = {
        "q": city_name,
        "limit": 1,
        "appid": API_KEY
    }
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    full_url = f"{url}?{query_string}"

    # print(f"[weather_api] Fetching coordinates for '{city_name}' from: {full_url}")
    try:
        response_data = await Utils.read_file_async(uri=full_url)
        if response_data:
            response_str = response_data.decode('utf-8') if isinstance(response_data, bytes) else response_data
            data = json.loads(response_str)
            if data and isinstance(data, list) and len(data) > 0:
                # print(f"[weather_api] Coordinates found: {data[0]['lat']}, {data[0]['lon']}")
                return data[0].get("lat"), data[0].get("lon")
            else:
                print(f"[weather_api] Nie znaleziono współrzędnych dla: {city_name}. Odpowiedź: {data}")
    except Exception as e:
        print(f"[weather_api] Błąd pobierania współrzędnych dla '{city_name}': {e}")
    return None, None

# --- Funkcje pomocnicze do ekstrakcji danych (mogą pozostać takie same) ---
def get_daily_forecast(data, days=7):
    if not data or "daily" not in data:
        return []
    return data["daily"][:days]

def get_current_weather(data):
    if not data or "current" not in data:
        return {} # Zwróć pusty dict, jeśli brak danych 'current'
    return data["current"]

def get_hourly_forecast(data, hours=12): # Dodatkowa funkcja, jeśli chcemy prognozę godzinową
    if not data or "hourly" not in data:
        return []
    return data["hourly"][:hours]

# get_icon_url nie będzie już potrzebne, jeśli użyjemy mapowania na ikony systemowe/symboliczne
# def get_icon_url(icon_code):
# return f"https://openweathermap.org/img/wn/{icon_code}@2x.png"