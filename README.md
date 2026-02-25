# 🚗 Atlanta → Gainesville Commute Analyzer

> **"Given weather, crashes, and day-of-week traffic patterns, what departure time ensures I arrive by my target time with ≥95% probability?"**

An end-to-end Data Analytics project born out of a real commute experience — interning at **Boehringer Ingelheim** (Gainesville, GA) while living in Atlanta. Rain delays, crashes on I-85, and unpredictable rush-hour congestion made every morning an adventure.

---

## 📁 Project Structure

```
traffic_analytics/
├── app.py                          # 🎯 Streamlit dashboard
├── requirements.txt                # Dependencies
├── data/
│   ├── generate_data.py            # Synthetic data generator
│   └── commute_data.csv            # Generated dataset (~32K records)
├── notebooks/
│   ├── eda.py                      # EDA visualization script
│   └── figures/                    # Generated EDA charts (8 PNGs)
├── models/
│   ├── train_model.py              # Quantile regression training
│   ├── quantile_*_model.joblib     # Trained model artifacts
│   ├── weather_encoder.joblib      # Label encoder
│   └── feature_cols.joblib         # Feature list
└── optimizer/
    └── departure_optimizer.py      # Departure time optimizer
```

## 🚀 Quick Start

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate data
python3 data/generate_data.py

# 4. Run EDA (generates charts in notebooks/figures/)
python3 notebooks/eda.py

# 5. Train models
python3 models/train_model.py

# 6. Launch dashboard
streamlit run app.py
```

## 📊 Methodology

### Data Generation
- **Route**: Atlanta, GA → Gainesville, GA (~55 mi via I-85 N / I-985 N)
- **Period**: 2 years of weekday commutes (2023–2024)
- **Features**: Departure time, day-of-week, weather (seasonal), crash occurrence
- **Realistic patterns**: Gaussian rush-hour peaks, log-normal crash delays, weather-dependent crash probabilities

### Modeling
- **Approach**: Gradient Boosting **Quantile Regression** (not just the mean!)
- **Quantiles**: 50th, 75th, 90th, 95th percentile of travel time
- **Why quantiles?** Because knowing the *average* commute is 75 minutes doesn't help you plan. You need to know the *worst-case* at your confidence level.

### Key Results
| Quantile | MAE | Coverage |
|---|---|---|
| 50th | 4.80 min | 50.4% |
| 75th | 5.73 min | 74.6% |
| 90th | 8.70 min | 89.0% |
| 95th | 12.57 min | 94.1% |

### Feature Importance (95th Percentile)
1. **Departure Time** — 57.3%
2. **Weather** — 33.9%
3. **Day of Week** — 8.7%

## 🎯 Sample Recommendations

| Scenario | Depart At | Travel Time |
|---|---|---|
| Wed, Clear, arrive by 8:30 (95%) | **6:55 AM** | ~94 min |
| Wed, Rain, arrive by 8:30 (95%) | **6:50 AM** | ~98 min |
| Wed, Heavy Rain, arrive by 8:30 (95%) | **6:40 AM** | ~107 min |
| Mon, Clear, arrive by 9:00 (90%) | **7:25 AM** | ~90 min |

## 🛠️ Tech Stack
- **Python** (pandas, NumPy, scikit-learn, scipy)
- **Visualization**: matplotlib, seaborn, Plotly
- **Dashboard**: Streamlit
- **ML**: Gradient Boosting Quantile Regression

---

*Built with ☕ and too many early mornings on I-85.*
