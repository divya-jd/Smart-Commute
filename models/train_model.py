"""
Probabilistic Travel-Time Model
================================
Trains Gradient Boosting Quantile Regressors for the 50th, 75th, 90th, and
95th percentiles of travel time, given departure features + conditions.

Run: python3 models/train_model.py
"""

import os
import sys
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import LabelEncoder
import joblib

# ── Paths ─────────────────────────────────────────────────────
MODEL_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(MODEL_DIR, "..", "data", "commute_data.csv")

# ── Load & prep ───────────────────────────────────────────────
print("📂  Loading data...")
df = pd.read_csv(DATA_PATH)

# Encode weather
le_weather = LabelEncoder()
df["weather_enc"] = le_weather.fit_transform(df["weather"])

# Features for the model
FEATURE_COLS = [
    "departure_hour_frac",
    "day_of_week_num",
    "weather_enc",
]

TARGET = "travel_time_min"

X = df[FEATURE_COLS].values
y = df[TARGET].values

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"   Train: {len(X_train):,}  |  Test: {len(X_test):,}\n")

# ── Train quantile regressors ────────────────────────────────
QUANTILES = [0.50, 0.75, 0.90, 0.95]
models = {}

for q in QUANTILES:
    print(f"🔧  Training quantile={q:.2f} ...")
    model = GradientBoostingRegressor(
        loss="quantile",
        alpha=q,
        n_estimators=300,
        max_depth=5,
        learning_rate=0.1,
        min_samples_leaf=20,
        random_state=42,
    )
    model.fit(X_train, y_train)
    models[q] = model

    # Evaluate
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    coverage = np.mean(y_test <= y_pred)  # should be ~q for quantile q
    print(f"   MAE={mae:.2f} min  |  Coverage={coverage:.2%} (target: {q:.0%})\n")

# ── Save models + artifacts ──────────────────────────────────
print("💾  Saving models...")
for q, model in models.items():
    fname = f"quantile_{int(q*100):02d}_model.joblib"
    joblib.dump(model, os.path.join(MODEL_DIR, fname))
    print(f"   ✓  {fname}")

# Save encoder
joblib.dump(le_weather, os.path.join(MODEL_DIR, "weather_encoder.joblib"))
print("   ✓  weather_encoder.joblib")

# Save feature names
joblib.dump(FEATURE_COLS, os.path.join(MODEL_DIR, "feature_cols.joblib"))
print("   ✓  feature_cols.joblib")

# ── Feature importance (95th quantile model) ──────────────────
print("\n📊  Feature Importance (95th percentile model):")
imp = models[0.95].feature_importances_
for name, score in sorted(zip(FEATURE_COLS, imp), key=lambda x: -x[1]):
    print(f"   {name:25s}  {score:.4f}")

print("\n✅  Model training complete!")
