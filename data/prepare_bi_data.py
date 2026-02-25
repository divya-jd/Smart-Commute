"""
Prepare BI-Optimized Dataset
==============================
Creates an enriched CSV with pre-computed columns for easy
drag-and-drop dashboard building in Tableau / Power BI.
"""

import pandas as pd
import numpy as np
import os

# Load the raw data
data_dir = os.path.dirname(__file__)
df = pd.read_csv(os.path.join(data_dir, "commute_data.csv"))
df["date"] = pd.to_datetime(df["date"])

# ── Enrich with BI-friendly columns ──

# Time period buckets
def time_period(hour_frac):
    if hour_frac < 6:
        return "Early Morning (5-6 AM)"
    elif hour_frac < 7:
        return "Pre-Rush (6-7 AM)"
    elif hour_frac < 9:
        return "AM Rush Hour (7-9 AM)"
    elif hour_frac < 11:
        return "Late Morning (9-11 AM)"
    elif hour_frac < 13:
        return "Midday (11 AM-1 PM)"
    elif hour_frac < 15:
        return "Early Afternoon (1-3 PM)"
    elif hour_frac < 16.5:
        return "Pre-PM Rush (3-4:30 PM)"
    elif hour_frac < 18.5:
        return "PM Rush Hour (4:30-6:30 PM)"
    else:
        return "Evening (6:30-8 PM)"

df["time_period"] = df["departure_hour_frac"].apply(time_period)

# Time period sort order
period_order = {
    "Early Morning (5-6 AM)": 1,
    "Pre-Rush (6-7 AM)": 2,
    "AM Rush Hour (7-9 AM)": 3,
    "Late Morning (9-11 AM)": 4,
    "Midday (11 AM-1 PM)": 5,
    "Early Afternoon (1-3 PM)": 6,
    "Pre-PM Rush (3-4:30 PM)": 7,
    "PM Rush Hour (4:30-6:30 PM)": 8,
    "Evening (6:30-8 PM)": 9,
}
df["time_period_sort"] = df["time_period"].map(period_order)

# Departure time as formatted string (for labels)
df["departure_time_label"] = df["departure_hour_frac"].apply(
    lambda h: f"{int(h):02d}:{int((h % 1) * 60):02d}"
)

# Hour bucket (rounded)
df["departure_hour_bucket"] = df["departure_hour"].astype(str).str.zfill(2) + ":00"

# Travel time bins
def travel_bin(t):
    if t < 55:
        return "Fast (< 55 min)"
    elif t < 65:
        return "Normal (55-65 min)"
    elif t < 80:
        return "Slow (65-80 min)"
    elif t < 100:
        return "Very Slow (80-100 min)"
    else:
        return "Extreme (100+ min)"

df["travel_time_category"] = df["travel_time_min"].apply(travel_bin)

# On-time flags (for different target arrivals)
for target_h in [8, 9, 17, 18]:
    target_label = f"{target_h:02d}:00"
    # arrival_time is a string like "07:45"
    df[f"on_time_{target_h}h"] = df["arrival_time"].apply(
        lambda a: 1 if a <= target_label else 0
    )

# Month and year
df["month"] = df["date"].dt.month
df["month_name"] = df["date"].dt.strftime("%B")
df["year"] = df["date"].dt.year
df["year_month"] = df["date"].dt.strftime("%Y-%m")
df["week_number"] = df["date"].dt.isocalendar().week.astype(int)

# Is rush hour (boolean for filtering)
df["is_am_rush"] = ((df["departure_hour_frac"] >= 7.0) & (df["departure_hour_frac"] <= 9.0)).astype(int)
df["is_pm_rush"] = ((df["departure_hour_frac"] >= 16.5) & (df["departure_hour_frac"] <= 18.5)).astype(int)
df["is_rush_hour"] = (df["is_am_rush"] | df["is_pm_rush"]).astype(int)

# Congestion level (rush_hour_multiplier as %)
df["congestion_pct"] = ((df["rush_hour_multiplier"] - 1) * 100).round(1)

# Total delay (weather + crash)
df["total_delay_min"] = (df["weather_penalty_min"] + df["crash_delay_min"]).round(1)

# Weather severity order (for sorting in charts)
weather_order = {"Clear": 1, "Fog": 2, "Rain": 3, "Heavy Rain": 4}
df["weather_severity"] = df["weather"].map(weather_order)

# Day type
df["day_type"] = df["day_of_week"].apply(
    lambda d: "Mon/Fri (Lighter)" if d in ["Monday", "Friday"] else "Tue-Thu (Heavier)"
)

# Crash label
df["crash_label"] = df["crash_on_route"].map({0: "No Crash", 1: "Crash on Route"})

# ── Save ──
output_path = os.path.join(data_dir, "smartcommute_bi_data.csv")
df.to_csv(output_path, index=False)

print(f"✅  BI-optimized dataset saved to: {output_path}")
print(f"   Records: {len(df):,}")
print(f"   Columns: {len(df.columns)}")
print(f"\n📊  New columns added:")
new_cols = [
    "time_period", "time_period_sort", "departure_time_label",
    "departure_hour_bucket", "travel_time_category",
    "on_time_8h", "on_time_9h", "on_time_17h", "on_time_18h",
    "month", "month_name", "year", "year_month", "week_number",
    "is_am_rush", "is_pm_rush", "is_rush_hour",
    "congestion_pct", "total_delay_min", "weather_severity",
    "day_type", "crash_label"
]
for col in new_cols:
    print(f"   • {col}")
