"""
Atlanta → Gainesville (Boehringer Ingelheim) Commute Data Generator
===================================================================
Generates ~2 years of synthetic weekday commute records with realistic
traffic patterns, weather effects, and crash probabilities.

Route: Atlanta, GA → Gainesville, GA (~54 miles via I-85 N / I-985 N)
Baseline travel time: ~50–58 minutes (no traffic, clear weather)
OSRM-verified base: 53.5 mi / 63.7 min
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os

np.random.seed(42)

# ──────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────
START_DATE = datetime(2023, 1, 2)   # First Monday of 2023
END_DATE   = datetime(2024, 12, 31)
DEPARTURE_SLOTS = pd.date_range("05:00", "20:00", freq="5min").time  # 5 AM – 8 PM
BASE_DISTANCE_MI = 54

# Weather probabilities by season (winter has more rain/fog in North GA)
WEATHER_PROBS = {
    # season: {weather_type: probability}
    "winter":  {"Clear": 0.50, "Rain": 0.25, "Heavy Rain": 0.15, "Fog": 0.10},
    "spring":  {"Clear": 0.55, "Rain": 0.25, "Heavy Rain": 0.12, "Fog": 0.08},
    "summer":  {"Clear": 0.45, "Rain": 0.30, "Heavy Rain": 0.20, "Fog": 0.05},
    "fall":    {"Clear": 0.60, "Rain": 0.20, "Heavy Rain": 0.10, "Fog": 0.10},
}

# ──────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────────────────────

def get_season(month: int) -> str:
    if month in (12, 1, 2):
        return "winter"
    elif month in (3, 4, 5):
        return "spring"
    elif month in (6, 7, 8):
        return "summer"
    else:
        return "fall"


def rush_hour_multiplier(departure_hour_frac: float) -> float:
    """
    Returns a congestion multiplier based on departure time.
    Morning peak ~7:45 AM, Evening peak ~5:15 PM on I-85.
    """
    # ── Morning rush ──
    am_center = 7.75    # 7:45 AM
    am_width  = 0.6
    am_height = 0.40    # up to 40% longer

    am_secondary_center = 8.75  # late morning / school
    am_secondary_width  = 0.5
    am_secondary_height = 0.15

    morning = am_height * np.exp(-0.5 * ((departure_hour_frac - am_center) / am_width) ** 2)
    morning += am_secondary_height * np.exp(-0.5 * ((departure_hour_frac - am_secondary_center) / am_secondary_width) ** 2)

    # ── Evening rush ──
    pm_center = 17.25   # 5:15 PM
    pm_width  = 0.7
    pm_height = 0.35    # up to 35% longer

    pm_secondary_center = 16.25  # early leave wave ~4:15 PM
    pm_secondary_width  = 0.5
    pm_secondary_height = 0.12

    evening = pm_height * np.exp(-0.5 * ((departure_hour_frac - pm_center) / pm_width) ** 2)
    evening += pm_secondary_height * np.exp(-0.5 * ((departure_hour_frac - pm_secondary_center) / pm_secondary_width) ** 2)

    return 1.0 + morning + evening


def weather_penalty_minutes(weather: str) -> float:
    """Extra minutes added due to weather (mean of distribution)."""
    penalties = {
        "Clear":      0.0,
        "Rain":       6.0,
        "Heavy Rain": 14.0,
        "Fog":        4.0,
    }
    return penalties.get(weather, 0.0)


def crash_probability(weather: str, departure_hour_frac: float) -> float:
    """
    Probability of encountering a crash on the route.
    Higher during rush hours (AM and PM) and bad weather.
    """
    base_prob = 0.04  # 4% baseline

    # Morning rush-hour boost
    am_rush_boost = 0.08 * np.exp(-0.5 * ((departure_hour_frac - 7.75) / 0.7) ** 2)

    # Evening rush-hour boost
    pm_rush_boost = 0.06 * np.exp(-0.5 * ((departure_hour_frac - 17.25) / 0.7) ** 2)

    # Weather boost
    weather_boost = {"Clear": 0.0, "Rain": 0.04, "Heavy Rain": 0.10, "Fog": 0.06}

    return min(base_prob + am_rush_boost + pm_rush_boost + weather_boost.get(weather, 0.0), 0.35)


def crash_delay_minutes() -> float:
    """If a crash occurs, sample the delay from a log-normal distribution."""
    # Median ~12 min, can be much longer (right-skewed)
    return np.random.lognormal(mean=2.5, sigma=0.6)


def day_of_week_factor(dow: int) -> float:
    """
    Monday=0, Friday=4.
    Monday & Friday tend to be slightly lighter; Tue–Thu heavier.
    """
    factors = {0: 0.95, 1: 1.05, 2: 1.08, 3: 1.03, 4: 0.92}
    return factors.get(dow, 1.0)


# ──────────────────────────────────────────────────────────────
# MAIN GENERATOR
# ──────────────────────────────────────────────────────────────

def generate_commute_data() -> pd.DataFrame:
    records = []

    # Generate all weekdays in the date range
    all_dates = pd.bdate_range(START_DATE, END_DATE)  # business days only

    for date in all_dates:
        month = date.month
        season = get_season(month)
        dow = date.dayofweek  # Mon=0, Fri=4

        # Sample weather for the day (same weather all morning for simplicity)
        weather_types = list(WEATHER_PROBS[season].keys())
        weather_probs = list(WEATHER_PROBS[season].values())
        day_weather = np.random.choice(weather_types, p=weather_probs)

        for dep_time in DEPARTURE_SLOTS:
            dep_hour_frac = dep_time.hour + dep_time.minute / 60.0

            # --- Base travel time ---
            base_minutes = np.random.normal(loc=54, scale=3)  # ~50-58 min center (OSRM-calibrated)

            # --- Rush hour multiplier ---
            rush_mult = rush_hour_multiplier(dep_hour_frac)

            # --- Day-of-week factor ---
            dow_factor = day_of_week_factor(dow)

            # --- Weather penalty ---
            wx_penalty = weather_penalty_minutes(day_weather)
            wx_noise   = np.random.normal(0, wx_penalty * 0.3) if wx_penalty > 0 else 0

            # --- Crash ---
            crash_prob = crash_probability(day_weather, dep_hour_frac)
            had_crash  = np.random.random() < crash_prob
            crash_delay = crash_delay_minutes() if had_crash else 0.0

            # --- Compute actual travel time ---
            travel_time = (base_minutes * rush_mult * dow_factor
                           + wx_penalty + wx_noise + crash_delay)

            # Clip to realistic bounds
            travel_time = np.clip(travel_time, 40, 210)

            # --- Derived fields ---
            dep_datetime = datetime.combine(date.date(), dep_time)
            arr_datetime = dep_datetime + timedelta(minutes=float(travel_time))

            records.append({
                "date":              date.date(),
                "day_of_week":       date.day_name(),
                "day_of_week_num":   dow,
                "season":            season,
                "departure_time":    dep_time.strftime("%H:%M"),
                "departure_hour":    dep_time.hour,
                "departure_minute":  dep_time.minute,
                "departure_hour_frac": round(dep_hour_frac, 4),
                "weather":           day_weather,
                "crash_on_route":    int(had_crash),
                "rush_hour_multiplier": round(rush_mult, 4),
                "base_travel_min":   round(base_minutes, 2),
                "weather_penalty_min": round(wx_penalty + wx_noise, 2),
                "crash_delay_min":   round(crash_delay, 2),
                "travel_time_min":   round(travel_time, 2),
                "arrival_time":      arr_datetime.strftime("%H:%M"),
                "distance_miles":    BASE_DISTANCE_MI,
            })

    df = pd.DataFrame(records)
    return df


# ──────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚗  Generating commute data (Atlanta → Gainesville)...")
    df = generate_commute_data()

    output_path = os.path.join(os.path.dirname(__file__), "commute_data.csv")
    df.to_csv(output_path, index=False)

    print(f"✅  Saved {len(df):,} records to {output_path}")
    print(f"   Date range : {df['date'].min()} → {df['date'].max()}")
    print(f"   Columns    : {list(df.columns)}")
    print(f"\n📊  Quick stats on travel_time_min:")
    print(df["travel_time_min"].describe().to_string())
