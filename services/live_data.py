"""
Live Data Services — Real-Time Weather & Routing
==================================================
Free APIs, no keys required:
  - OSRM (Open Source Routing Machine) for driving distance & time
  - Open-Meteo for weather forecasts
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta


# ══════════════════════════════════════════════════════════════
# GEOCODING (Nominatim — free, no key)
# ══════════════════════════════════════════════════════════════

def geocode(address):
    """
    Geocode an address to (lat, lon) using OpenStreetMap Nominatim.
    Returns (lat, lon, display_name) or None.
    """
    try:
        encoded = urllib.parse.quote(address)
        url = (
            f"https://nominatim.openstreetmap.org/search"
            f"?q={encoded}&format=json&limit=1"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "SmartCommute/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data:
                return (
                    float(data[0]["lat"]),
                    float(data[0]["lon"]),
                    data[0].get("display_name", address),
                )
    except Exception as e:
        print(f"Geocoding error for '{address}': {e}")
    return None


def search_addresses(query, limit=5):
    """
    Search for address suggestions matching a partial query.
    Returns list of display_name strings (up to `limit`).
    """
    if not query or len(query.strip()) < 3:
        return []
    try:
        encoded = urllib.parse.quote(query)
        url = (
            f"https://nominatim.openstreetmap.org/search"
            f"?q={encoded}&format=json&limit={limit}&addressdetails=1"
            f"&countrycodes=us"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "SmartCommute/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            return [item.get("display_name", "") for item in data if item.get("display_name")]
    except Exception as e:
        print(f"Address search error for '{query}': {e}")
    return []


# ══════════════════════════════════════════════════════════════
# ROUTING (OSRM — free, no key)
# ══════════════════════════════════════════════════════════════

def get_driving_info(origin_address, dest_address):
    """
    Get real driving distance and base travel time between two addresses.

    Returns dict:
        distance_mi    : float  (miles)
        duration_min   : float  (minutes, no traffic)
        origin_coords  : (lat, lon)
        dest_coords    : (lat, lon)
        origin_name    : str
        dest_name      : str
        success        : bool
    """
    origin = geocode(origin_address)
    dest = geocode(dest_address)

    if not origin or not dest:
        return {
            "success": False,
            "error": f"Could not geocode: {origin_address if not origin else dest_address}",
        }

    # OSRM uses lon,lat format
    url = (
        f"https://router.project-osrm.org/route/v1/driving/"
        f"{origin[1]},{origin[0]};{dest[1]},{dest[0]}"
        f"?overview=false"
    )

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SmartCommute/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        if data.get("code") == "Ok" and data.get("routes"):
            route = data["routes"][0]
            distance_m = route["distance"]      # meters
            duration_s = route["duration"]       # seconds

            return {
                "success": True,
                "distance_mi": round(distance_m / 1609.344, 1),
                "duration_min": round(duration_s / 60, 1),
                "origin_coords": (origin[0], origin[1]),
                "dest_coords": (dest[0], dest[1]),
                "origin_name": origin[2],
                "dest_name": dest[2],
            }
    except Exception as e:
        print(f"OSRM routing error: {e}")

    return {"success": False, "error": "Routing failed"}


# ══════════════════════════════════════════════════════════════
# WEATHER FORECAST (Open-Meteo — free, no key)
# ══════════════════════════════════════════════════════════════

# WMO Weather Code mapping
WMO_TO_CATEGORY = {
    0:  "Clear",       # Clear sky
    1:  "Clear",       # Mainly clear
    2:  "Clear",       # Partly cloudy
    3:  "Clear",       # Overcast
    45: "Fog",         # Fog
    48: "Fog",         # Depositing rime fog
    51: "Rain",        # Light drizzle
    53: "Rain",        # Moderate drizzle
    55: "Rain",        # Dense drizzle
    56: "Rain",        # Light freezing drizzle
    57: "Rain",        # Dense freezing drizzle
    61: "Rain",        # Slight rain
    63: "Rain",        # Moderate rain
    65: "Heavy Rain",  # Heavy rain
    66: "Rain",        # Light freezing rain
    67: "Heavy Rain",  # Heavy freezing rain
    71: "Clear",       # Slight snow fall (treated as clear for driving)
    73: "Rain",        # Moderate snow fall
    75: "Heavy Rain",  # Heavy snow fall
    77: "Fog",         # Snow grains
    80: "Rain",        # Slight rain showers
    81: "Rain",        # Moderate rain showers
    82: "Heavy Rain",  # Violent rain showers
    85: "Rain",        # Slight snow showers
    86: "Heavy Rain",  # Heavy snow showers
    95: "Heavy Rain",  # Thunderstorm
    96: "Heavy Rain",  # Thunderstorm with slight hail
    99: "Heavy Rain",  # Thunderstorm with heavy hail
}

WMO_DESCRIPTIONS = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    56: "Freezing drizzle (light)", 57: "Freezing drizzle (dense)",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Freezing rain (light)", 67: "Freezing rain (heavy)",
    71: "Light snowfall", 73: "Moderate snowfall", 75: "Heavy snowfall",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    95: "Thunderstorm", 96: "Thunderstorm + hail", 99: "Severe thunderstorm + hail",
}


def get_weather_forecast(lat, lon, days=3):
    """
    Get weather forecast for the next `days` days.

    Returns list of dicts:
        date               : str  (YYYY-MM-DD)
        day_name           : str  (e.g. "Friday")
        weather_code       : int  (WMO code)
        weather_desc       : str  (human readable)
        weather_category   : str  (Clear/Rain/Heavy Rain/Fog)
        precip_probability : int  (0–100%)
        temp_max_f         : float
        temp_min_f         : float
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=weather_code,precipitation_probability_max,"
        f"temperature_2m_max,temperature_2m_min"
        f"&temperature_unit=fahrenheit"
        f"&timezone=America/New_York"
        f"&forecast_days={days}"
    )

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SmartCommute/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        daily = data.get("daily", {})
        forecasts = []

        for i in range(len(daily.get("time", []))):
            date_str = daily["time"][i]
            wmo_code = daily["weather_code"][i]
            dt = datetime.strptime(date_str, "%Y-%m-%d")

            forecasts.append({
                "date": date_str,
                "day_name": dt.strftime("%A"),
                "day_of_week_num": dt.weekday(),  # 0=Mon, 6=Sun
                "weather_code": wmo_code,
                "weather_desc": WMO_DESCRIPTIONS.get(wmo_code, f"Code {wmo_code}"),
                "weather_category": WMO_TO_CATEGORY.get(wmo_code, "Clear"),
                "precip_probability": daily["precipitation_probability_max"][i],
                "temp_max_f": daily["temperature_2m_max"][i],
                "temp_min_f": daily["temperature_2m_min"][i],
            })

        return forecasts

    except Exception as e:
        print(f"Weather API error: {e}")
        return []


def get_tomorrow_forecast(lat, lon):
    """Convenience: get just tomorrow's forecast."""
    forecasts = get_weather_forecast(lat, lon, days=2)
    if len(forecasts) >= 2:
        return forecasts[1]  # index 0 = today, 1 = tomorrow
    return None


# ══════════════════════════════════════════════════════════════
# CLI TEST
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("🚗  SmartCommute — Live Data Services Test")
    print("=" * 60)

    # Test routing
    print("\n📍 Routing: Atlanta, GA → Gainesville, GA")
    route = get_driving_info("Atlanta, GA", "Gainesville, GA")
    if route["success"]:
        print(f"   Distance : {route['distance_mi']} mi")
        print(f"   Base time: {route['duration_min']} min (no traffic)")
    else:
        print(f"   ❌ {route['error']}")

    # Test weather
    print("\n🌦️  Weather Forecast (Gainesville, GA):")
    forecasts = get_weather_forecast(34.2979, -83.8241, days=3)
    for f in forecasts:
        print(f"   {f['day_name']:10s} {f['date']}  "
              f"{f['weather_desc']:25s}  "
              f"Precip: {f['precip_probability']:3d}%  "
              f"→ Category: {f['weather_category']}")

    # Test different route
    print("\n📍 Routing: New York, NY → Boston, MA")
    route2 = get_driving_info("New York, NY", "Boston, MA")
    if route2["success"]:
        print(f"   Distance : {route2['distance_mi']} mi")
        print(f"   Base time: {route2['duration_min']} min (no traffic)")
