"""
Departure Time Optimizer
=========================
Given a target arrival time and desired confidence level, determines the
optimal (latest) departure time that ensures on-time arrival.

Can be used as a module or run standalone for quick checks.
"""

import os
import sys
import numpy as np
import joblib
from datetime import datetime, timedelta


# ── Load model artifacts ──────────────────────────────────────
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")


def load_models():
    """Load all quantile models, encoder, and feature list."""
    quantiles = [0.50, 0.75, 0.90, 0.95]
    models = {}
    for q in quantiles:
        fname = f"quantile_{int(q*100):02d}_model.joblib"
        path = os.path.join(MODEL_DIR, fname)
        models[q] = joblib.load(path)

    le_weather = joblib.load(os.path.join(MODEL_DIR, "weather_encoder.joblib"))
    feature_cols = joblib.load(os.path.join(MODEL_DIR, "feature_cols.joblib"))

    return models, le_weather, feature_cols


def predict_travel_time(models, le_weather, departure_hour_frac,
                        day_of_week_num, weather, quantile=0.95):
    """
    Predict travel time at the given quantile.

    Parameters
    ----------
    departure_hour_frac : float   – e.g. 7.5 for 7:30 AM
    day_of_week_num     : int     – 0=Mon, 4=Fri
    weather             : str     – "Clear", "Rain", "Heavy Rain", "Fog"
    quantile            : float   – 0.50, 0.75, 0.90, or 0.95

    Returns
    -------
    float : predicted travel time in minutes
    """
    weather_enc = le_weather.transform([weather])[0]
    X = np.array([[departure_hour_frac, day_of_week_num, weather_enc]])
    return models[quantile].predict(X)[0]


def find_optimal_departure(models, le_weather, target_arrival_time,
                           day_of_week_num, weather, confidence=0.95,
                           search_start="05:00", search_end="20:00",
                           step_minutes=5, distance_scale=1.0):
    """
    Find the LATEST departure time such that:
        departure + predicted_travel_time(q=confidence) * distance_scale <= target_arrival

    Parameters
    ----------
    target_arrival_time : str   – "HH:MM" format, e.g. "08:30"
    day_of_week_num     : int   – 0=Mon, 4=Fri
    weather             : str   – weather condition
    confidence          : float – quantile confidence level (0.50–0.95)
    distance_scale      : float – multiplier relative to baseline 55-mi route (default 1.0)

    Returns
    -------
    dict with keys:
        - recommended_departure : str  ("HH:MM")
        - predicted_travel_min  : float
        - predicted_arrival     : str  ("HH:MM")
        - buffer_minutes        : float (minutes of slack)
        - all_candidates        : list of dicts (for visualization)
    """
    target = datetime.strptime(target_arrival_time, "%H:%M")

    start = datetime.strptime(search_start, "%H:%M")
    end   = datetime.strptime(search_end, "%H:%M")

    candidates = []
    best = None

    current = start
    while current <= end:
        dep_hour_frac = current.hour + current.minute / 60.0
        predicted_min = predict_travel_time(
            models, le_weather, dep_hour_frac, day_of_week_num,
            weather, quantile=confidence
        ) * distance_scale
        predicted_arrival = current + timedelta(minutes=float(predicted_min))

        on_time = predicted_arrival <= target
        buffer = (target - predicted_arrival).total_seconds() / 60.0

        candidate = {
            "departure":         current.strftime("%H:%M"),
            "departure_frac":    dep_hour_frac,
            "predicted_travel":  round(predicted_min, 1),
            "predicted_arrival": predicted_arrival.strftime("%H:%M"),
            "on_time":           on_time,
            "buffer_min":        round(buffer, 1),
        }
        candidates.append(candidate)

        if on_time:
            best = candidate  # keep updating — we want the LATEST on-time slot

        current += timedelta(minutes=step_minutes)

    result = {
        "recommended_departure": best["departure"] if best else None,
        "predicted_travel_min":  best["predicted_travel"] if best else None,
        "predicted_arrival":     best["predicted_arrival"] if best else None,
        "buffer_minutes":        best["buffer_min"] if best else None,
        "confidence_level":      confidence,
        "target_arrival":        target_arrival_time,
        "weather":               weather,
        "all_candidates":        candidates,
    }
    return result


# ── CLI ───────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🧭  Departure Time Optimizer")
    print("=" * 50)

    models, le_weather, feature_cols = load_models()

    # Example: arrive by 8:30 AM on a Wednesday, rainy day
    scenarios = [
        ("08:30", 2, "Clear",      0.95),
        ("08:30", 2, "Rain",       0.95),
        ("08:30", 2, "Heavy Rain", 0.95),
        ("09:00", 0, "Clear",      0.90),
        ("08:00", 4, "Fog",        0.95),
    ]

    for target, dow, weather, conf in scenarios:
        days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        result = find_optimal_departure(
            models, le_weather, target, dow, weather, conf
        )
        rec = result["recommended_departure"]
        travel = result["predicted_travel_min"]
        buf = result["buffer_minutes"]

        print(f"\n🎯  Arrive by {target} | {days[dow]} | {weather} | {conf:.0%} confidence")
        if rec:
            print(f"   ✅  Depart at {rec}  (travel ≈{travel:.0f} min, buffer ≈{buf:.0f} min)")
        else:
            print(f"   ⚠️  No feasible departure found in 5:00–10:00 window!")
