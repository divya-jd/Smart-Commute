"""
Exploratory Data Analysis — Atlanta → Gainesville Commute
=========================================================
Generates publication-quality visualizations and saves them as PNGs.
Run: python3 notebooks/eda.py
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns

# ── Config ────────────────────────────────────────────────────
FIG_DIR = os.path.join(os.path.dirname(__file__), "figures")
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "commute_data.csv")
os.makedirs(FIG_DIR, exist_ok=True)

sns.set_theme(style="whitegrid", palette="muted", font_scale=1.1)
COLORS = sns.color_palette("husl", 8)

# ── Load ──────────────────────────────────────────────────────
print("📂  Loading data...")
df = pd.read_csv(DATA_PATH)
df["date"] = pd.to_datetime(df["date"])
print(f"   {len(df):,} records loaded.\n")


# ──────────────────────────────────────────────────────────────
# 1. Travel-time distribution by departure hour
# ──────────────────────────────────────────────────────────────
def plot_travel_time_by_hour():
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.boxplot(
        data=df, x="departure_hour", y="travel_time_min",
        palette="YlOrRd", fliersize=1, ax=ax
    )
    ax.set_title("Travel Time Distribution by Departure Hour", fontsize=16, weight="bold")
    ax.set_xlabel("Departure Hour (24h)", fontsize=13)
    ax.set_ylabel("Travel Time (minutes)", fontsize=13)
    ax.axhline(60, ls="--", color="green", alpha=0.6, label="60 min baseline")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "01_travel_time_by_hour.png"), dpi=150)
    plt.close(fig)
    print("  ✓  01_travel_time_by_hour.png")


# ──────────────────────────────────────────────────────────────
# 2. Weather impact on travel time
# ──────────────────────────────────────────────────────────────
def plot_weather_impact():
    order = ["Clear", "Fog", "Rain", "Heavy Rain"]
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.violinplot(
        data=df, x="weather", y="travel_time_min",
        order=order, palette="coolwarm", inner="quartile", ax=ax
    )
    ax.set_title("Weather Impact on Travel Time", fontsize=16, weight="bold")
    ax.set_xlabel("Weather Condition", fontsize=13)
    ax.set_ylabel("Travel Time (minutes)", fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "02_weather_impact.png"), dpi=150)
    plt.close(fig)
    print("  ✓  02_weather_impact.png")


# ──────────────────────────────────────────────────────────────
# 3. Crash frequency by hour and weather
# ──────────────────────────────────────────────────────────────
def plot_crash_frequency():
    crash_rate = (
        df.groupby(["departure_hour", "weather"])["crash_on_route"]
        .mean()
        .reset_index()
    )
    fig, ax = plt.subplots(figsize=(12, 6))
    for weather_type in ["Clear", "Rain", "Heavy Rain", "Fog"]:
        subset = crash_rate[crash_rate["weather"] == weather_type]
        ax.plot(subset["departure_hour"], subset["crash_on_route"] * 100,
                marker="o", label=weather_type, linewidth=2)
    ax.set_title("Crash Probability by Hour & Weather", fontsize=16, weight="bold")
    ax.set_xlabel("Departure Hour", fontsize=13)
    ax.set_ylabel("Crash Probability (%)", fontsize=13)
    ax.legend(title="Weather")
    ax.yaxis.set_major_formatter(ticker.PercentFormatter(decimals=0))
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "03_crash_frequency.png"), dpi=150)
    plt.close(fig)
    print("  ✓  03_crash_frequency.png")


# ──────────────────────────────────────────────────────────────
# 4. Day-of-week heatmap
# ──────────────────────────────────────────────────────────────
def plot_dow_heatmap():
    pivot = df.pivot_table(
        values="travel_time_min",
        index="day_of_week",
        columns="departure_hour",
        aggfunc="mean"
    )
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    pivot = pivot.reindex(day_order)

    fig, ax = plt.subplots(figsize=(14, 5))
    sns.heatmap(pivot, cmap="YlOrRd", annot=True, fmt=".0f", linewidths=0.5, ax=ax)
    ax.set_title("Avg Travel Time (min) — Day of Week × Departure Hour",
                 fontsize=15, weight="bold")
    ax.set_xlabel("Departure Hour", fontsize=13)
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "04_dow_heatmap.png"), dpi=150)
    plt.close(fig)
    print("  ✓  04_dow_heatmap.png")


# ──────────────────────────────────────────────────────────────
# 5. Correlation matrix
# ──────────────────────────────────────────────────────────────
def plot_correlation_matrix():
    numeric_cols = [
        "departure_hour_frac", "day_of_week_num", "crash_on_route",
        "rush_hour_multiplier", "base_travel_min", "weather_penalty_min",
        "crash_delay_min", "travel_time_min"
    ]
    corr = df[numeric_cols].corr()
    fig, ax = plt.subplots(figsize=(10, 8))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r",
                center=0, linewidths=0.5, ax=ax)
    ax.set_title("Feature Correlation Matrix", fontsize=16, weight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "05_correlation_matrix.png"), dpi=150)
    plt.close(fig)
    print("  ✓  05_correlation_matrix.png")


# ──────────────────────────────────────────────────────────────
# 6. Percentile ribbons by departure time
# ──────────────────────────────────────────────────────────────
def plot_percentile_ribbon():
    pcts = df.groupby("departure_hour_frac")["travel_time_min"].quantile(
        [0.50, 0.75, 0.90, 0.95]
    ).unstack()

    fig, ax = plt.subplots(figsize=(14, 7))

    ax.fill_between(pcts.index, pcts[0.50], pcts[0.95],
                     alpha=0.15, color="red", label="50th–95th pctl")
    ax.fill_between(pcts.index, pcts[0.50], pcts[0.90],
                     alpha=0.2, color="orange", label="50th–90th pctl")
    ax.fill_between(pcts.index, pcts[0.50], pcts[0.75],
                     alpha=0.3, color="gold", label="50th–75th pctl")
    ax.plot(pcts.index, pcts[0.50], color="darkblue", linewidth=2.5, label="Median (50th)")
    ax.plot(pcts.index, pcts[0.95], color="red", linewidth=1.5, linestyle="--", label="95th percentile")

    ax.set_title("Travel-Time Percentile Bands by Departure Time",
                 fontsize=16, weight="bold")
    ax.set_xlabel("Departure Time (hour, fractional)", fontsize=13)
    ax.set_ylabel("Travel Time (minutes)", fontsize=13)
    ax.legend(loc="upper left")

    hours = range(5, 11)
    ax.set_xticks(hours)
    ax.set_xticklabels([f"{h}:00" for h in hours])

    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "06_percentile_ribbon.png"), dpi=150)
    plt.close(fig)
    print("  ✓  06_percentile_ribbon.png")


# ──────────────────────────────────────────────────────────────
# 7. Travel time distribution (overall)
# ──────────────────────────────────────────────────────────────
def plot_overall_distribution():
    fig, ax = plt.subplots(figsize=(12, 5))
    sns.histplot(df["travel_time_min"], bins=80, kde=True, color="steelblue", ax=ax)
    ax.axvline(df["travel_time_min"].median(), color="red", ls="--", label=f"Median: {df['travel_time_min'].median():.0f} min")
    ax.axvline(df["travel_time_min"].quantile(0.95), color="darkred", ls=":",
               label=f"95th pctl: {df['travel_time_min'].quantile(0.95):.0f} min")
    ax.set_title("Overall Travel Time Distribution", fontsize=16, weight="bold")
    ax.set_xlabel("Travel Time (minutes)", fontsize=13)
    ax.set_ylabel("Count", fontsize=13)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "07_overall_distribution.png"), dpi=150)
    plt.close(fig)
    print("  ✓  07_overall_distribution.png")


# ──────────────────────────────────────────────────────────────
# 8. Monthly trend
# ──────────────────────────────────────────────────────────────
def plot_monthly_trend():
    monthly = df.groupby(df["date"].dt.to_period("M"))["travel_time_min"].agg(
        ["mean", "median", lambda x: x.quantile(0.95)]
    )
    monthly.columns = ["Mean", "Median", "95th Percentile"]
    monthly.index = monthly.index.to_timestamp()

    fig, ax = plt.subplots(figsize=(14, 5))
    for col, style in zip(monthly.columns, ["-", "--", ":"]):
        ax.plot(monthly.index, monthly[col], linestyle=style, marker="o",
                markersize=4, linewidth=2, label=col)
    ax.set_title("Monthly Travel Time Trend", fontsize=16, weight="bold")
    ax.set_xlabel("Month", fontsize=13)
    ax.set_ylabel("Travel Time (minutes)", fontsize=13)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "08_monthly_trend.png"), dpi=150)
    plt.close(fig)
    print("  ✓  08_monthly_trend.png")


# ──────────────────────────────────────────────────────────────
# Run all
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🎨  Generating EDA visualizations...\n")
    plot_travel_time_by_hour()
    plot_weather_impact()
    plot_crash_frequency()
    plot_dow_heatmap()
    plot_correlation_matrix()
    plot_percentile_ribbon()
    plot_overall_distribution()
    plot_monthly_trend()
    print(f"\n✅  All figures saved to {FIG_DIR}/")
