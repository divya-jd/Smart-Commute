"""
🚗 SmartCommute — Dynamic Commute Analyzer
=============================================
Interactive Streamlit dashboard with REAL-TIME weather forecasts
and route-based travel time predictions.

APIs used (free, no keys):
  - OSRM for real driving distance & time
  - Open-Meteo for live weather forecasts

Run: streamlit run app.py
"""

import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import joblib
from datetime import datetime, timedelta, date

# ── Add project root to path ─────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from optimizer.departure_optimizer import load_models, find_optimal_departure, predict_travel_time
from services.live_data import get_driving_info, get_weather_forecast, get_tomorrow_forecast, search_addresses

# ── Constants ─────────────────────────────────────────────────
BASELINE_DISTANCE_MI = 54   # OSRM-verified ATL→GNV
BASELINE_DURATION_MIN = 64  # OSRM-verified ATL→GNV base

# ══════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="🚗 SmartCommute",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    }

    /* Card-style metric containers */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 16px 20px;
        backdrop-filter: blur(10px);
    }
    div[data-testid="stMetric"] label {
        color: #a3a8b8 !important;
        font-weight: 500;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-weight: 700;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        border-right: 1px solid rgba(255,255,255,0.05);
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(255,255,255,0.05);
        border-radius: 8px 8px 0 0;
        color: #a3a8b8;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .stTabs [aria-selected="true"] {
        background: rgba(99, 102, 241, 0.3) !important;
        color: #ffffff !important;
        border-color: #6366f1 !important;
    }

    /* Headers */
    h1 {
        background: linear-gradient(90deg, #6366f1, #a855f7, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
    }
    h2, h3 {
        color: #e0e0e0 !important;
    }

    /* Dividers */
    hr {
        border-color: rgba(255,255,255,0.1) !important;
    }

    /* Info / success boxes */
    .stAlert {
        border-radius: 10px;
    }

    /* Selectbox, sliders */
    .stSelectbox label, .stSlider label, .stRadio label {
        color: #c4c4cc !important;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Tomorrow's commute special card */
    .tomorrow-card {
        background: linear-gradient(135deg, rgba(99,102,241,0.15), rgba(168,85,247,0.15));
        border: 1px solid rgba(99,102,241,0.3);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════
@st.cache_data
def load_data():
    path = os.path.join(os.path.dirname(__file__), "data", "commute_data.csv")
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_resource
def get_models():
    return load_models()


@st.cache_data(ttl=3600)
def cached_driving_info(origin, dest):
    return get_driving_info(origin, dest)


@st.cache_data(ttl=1800)
def cached_weather_forecast(lat, lon, days=3):
    return get_weather_forecast(lat, lon, days)


@st.cache_data(ttl=600)
def cached_address_search(query):
    return search_addresses(query, limit=5)


df = load_data()
models, le_weather, feature_cols = get_models()

# ══════════════════════════════════════════════════════════════
# SIDEBAR — Route Setup
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🚗 SmartCommute")
    st.markdown("*Real-Time Commute Intelligence*")
    st.divider()

    st.markdown("### 📍 Your Route")

    # ── Origin ──
    origin_input = st.text_input(
        "From",
        value="Atlanta, GA",
        placeholder="e.g. 2450 Peachtree Rd NW, Atlanta, GA",
        help="Enter a street address, city, or landmark. Use full addresses for best results (Nominatim doesn't index business names — use the street address instead).",
    )
    origin_matches = cached_address_search(origin_input)
    if len(origin_matches) > 1:
        origin_input = st.selectbox(
            "Did you mean?", origin_matches, index=0,
            key="origin_pick", label_visibility="visible"
        )
    elif len(origin_matches) == 1:
        st.caption(f"📍 {origin_matches[0][:80]}…" if len(origin_matches[0]) > 80 else f"📍 {origin_matches[0]}")

    # ── Destination ──
    dest_input = st.text_input(
        "To",
        value="Gainesville, GA",
        placeholder="e.g. 1112 Airport Pkwy, Gainesville, GA",
        help="Enter a street address, city, or landmark. Use full addresses for best results.",
    )
    dest_matches = cached_address_search(dest_input)
    if len(dest_matches) > 1:
        dest_input = st.selectbox(
            "Did you mean?", dest_matches, index=0,
            key="dest_pick", label_visibility="visible"
        )
    elif len(dest_matches) == 1:
        st.caption(f"📍 {dest_matches[0][:80]}…" if len(dest_matches[0]) > 80 else f"📍 {dest_matches[0]}")

    # ── OSRM real driving info ──
    route_info = cached_driving_info(origin_input, dest_input)

    if route_info["success"]:
        route_distance = route_info["distance_mi"]
        route_base_min = route_info["duration_min"]
        dist_scale = route_distance / BASELINE_DISTANCE_MI
        dest_coords = route_info["dest_coords"]

        st.success(f"📏 **{route_distance} mi** · Base: **{route_base_min:.0f} min** (no traffic)")
    else:
        route_distance = BASELINE_DISTANCE_MI
        route_base_min = BASELINE_DURATION_MIN
        dist_scale = 1.0
        dest_coords = (34.2979, -83.8241)  # Gainesville default
        st.warning(route_info.get("error", "Route lookup failed"))
        st.info("Using default: Atlanta → Gainesville (54 mi)")

    # ── Live weather ──
    st.divider()
    st.markdown("### 🌦️ Live Forecast")
    forecasts = cached_weather_forecast(dest_coords[0], dest_coords[1], days=3)

    if forecasts:
        for fc in forecasts:
            emoji_map = {"Clear": "☀️", "Rain": "🌧️", "Heavy Rain": "⛈️", "Fog": "🌫️"}
            wx_emoji = emoji_map.get(fc["weather_category"], "🌤️")
            is_today = fc["date"] == date.today().isoformat()
            label = "**Today**" if is_today else fc["day_name"]
            st.markdown(
                f"{wx_emoji} {label}: {fc['weather_desc']} "
                f"({fc['precip_probability']}% precip) "
                f"· {fc['temp_min_f']:.0f}–{fc['temp_max_f']:.0f}°F"
            )
    else:
        st.info("Weather unavailable")

    st.divider()
    st.markdown("### 📊 Model Info")
    st.metric("Training Records", f"{len(df):,}")
    st.metric("Baseline Route", f"{BASELINE_DISTANCE_MI} mi (ATL→GNV)")
    st.metric("Distance Scale", f"{dist_scale:.2f}x")

# ── Build display labels ──────────────────────────────────────
origin_short = origin_input.split(",")[0].strip() if origin_input else "Origin"
dest_short = dest_input.split(",")[0].strip() if dest_input else "Destination"
route_label = f"{origin_short} → {dest_short}"

# ══════════════════════════════════════════════════════════════
# MAIN CONTENT
# ══════════════════════════════════════════════════════════════
st.title(f"🚗 {route_label} Commute Analyzer")
st.markdown(
    f"*Real-time predictions powered by live weather & routing — "
    f"**{route_distance} mi**, base drive **{route_base_min:.0f} min***"
)

tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Overview",
    "📊 EDA Explorer",
    "🎯 Departure Advisor",
    "🔥 Risk Analysis"
])

# ──────────────────────────────────────────────────────────────
# TAB 1: OVERVIEW
# ──────────────────────────────────────────────────────────────
with tab1:
    st.header("Route Overview")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🕐 Avg Travel Time", f"{df['travel_time_min'].mean() * dist_scale:.0f} min")
    col2.metric("📈 Worst Case", f"{df['travel_time_min'].max() * dist_scale:.0f} min")
    col3.metric("🌧️ Rainy Days", f"{(df.groupby('date')['weather'].first().isin(['Rain','Heavy Rain'])).mean():.0%}")
    col4.metric("💥 Crash Rate", f"{df['crash_on_route'].mean():.1%}")

    st.divider()

    # Overall distribution
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Travel Time Distribution")
        fig = px.histogram(
            df, x="travel_time_min", nbins=80,
            color_discrete_sequence=["#6366f1"],
            labels={"travel_time_min": "Travel Time (min)"},
        )
        fig.add_vline(x=df["travel_time_min"].median(), line_dash="dash",
                       line_color="yellow",
                       annotation_text=f"Median: {df['travel_time_min'].median():.0f} min")
        fig.add_vline(x=df["travel_time_min"].quantile(0.95), line_dash="dot",
                       line_color="red",
                       annotation_text=f"95th: {df['travel_time_min'].quantile(0.95):.0f} min")
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Weather Breakdown")
        weather_counts = df.groupby("date")["weather"].first().value_counts()
        fig = px.pie(
            values=weather_counts.values,
            names=weather_counts.index,
            color_discrete_sequence=px.colors.qualitative.Pastel,
            hole=0.4,
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Monthly trend
    st.subheader("Monthly Travel Time Trend")
    monthly = df.groupby(df["date"].dt.to_period("M"))["travel_time_min"].agg(
        ["mean", "median"]
    ).reset_index()
    monthly["date"] = monthly["date"].dt.to_timestamp()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly["date"], y=monthly["mean"],
                              mode="lines+markers", name="Mean",
                              line=dict(color="#a855f7", width=3)))
    fig.add_trace(go.Scatter(x=monthly["date"], y=monthly["median"],
                              mode="lines+markers", name="Median",
                              line=dict(color="#6366f1", width=3)))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=350,
        yaxis_title="Travel Time (min)",
    )
    st.plotly_chart(fig, use_container_width=True)


# ──────────────────────────────────────────────────────────────
# TAB 2: EDA EXPLORER
# ──────────────────────────────────────────────────────────────
with tab2:
    st.header("EDA Explorer")

    # Filters
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        sel_weather = st.multiselect(
            "Weather", df["weather"].unique().tolist(),
            default=df["weather"].unique().tolist()
        )
    with fcol2:
        sel_days = st.multiselect(
            "Day of Week",
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        )
    with fcol3:
        hour_range = st.slider("Departure Hour Range", 5, 20, (5, 20))

    filtered = df[
        (df["weather"].isin(sel_weather)) &
        (df["day_of_week"].isin(sel_days)) &
        (df["departure_hour"] >= hour_range[0]) &
        (df["departure_hour"] <= hour_range[1])
    ]

    st.markdown(f"*Showing {len(filtered):,} of {len(df):,} records*")
    st.divider()

    # Chart 1: boxplot by hour
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Travel Time by Departure Hour")
        fig = px.box(
            filtered, x="departure_hour", y="travel_time_min",
            color="weather",
            color_discrete_map={
                "Clear": "#22c55e", "Rain": "#3b82f6",
                "Heavy Rain": "#ef4444", "Fog": "#f59e0b"
            },
            labels={"departure_hour": "Hour", "travel_time_min": "Travel Time (min)"},
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=450,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Weather Impact (Violin Plot)")
        fig = px.violin(
            filtered, x="weather", y="travel_time_min",
            color="weather",
            box=True, points=False,
            color_discrete_map={
                "Clear": "#22c55e", "Rain": "#3b82f6",
                "Heavy Rain": "#ef4444", "Fog": "#f59e0b"
            },
            category_orders={"weather": ["Clear", "Fog", "Rain", "Heavy Rain"]},
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=450,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Chart 2: Heat map
    st.subheader("Average Travel Time — Day × Hour Heatmap")
    pivot = filtered.pivot_table(
        values="travel_time_min", index="day_of_week",
        columns="departure_hour", aggfunc="mean"
    )
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    pivot = pivot.reindex([d for d in day_order if d in pivot.index])

    fig = px.imshow(
        pivot, color_continuous_scale="YlOrRd",
        labels={"x": "Departure Hour", "y": "Day", "color": "Avg Minutes"},
        aspect="auto",
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Chart 3: percentile ribbon
    st.subheader("Travel-Time Percentile Bands")
    pcts = filtered.groupby("departure_hour_frac")["travel_time_min"].quantile(
        [0.50, 0.75, 0.90, 0.95]
    ).unstack().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pcts["departure_hour_frac"], y=pcts[0.95],
        fill=None, mode="lines", line_color="rgba(239,68,68,0.3)", name="95th"
    ))
    fig.add_trace(go.Scatter(
        x=pcts["departure_hour_frac"], y=pcts[0.50],
        fill="tonexty", mode="lines", line_color="rgba(99,102,241,0.8)",
        fillcolor="rgba(239,68,68,0.15)", name="50th–95th band"
    ))
    fig.add_trace(go.Scatter(
        x=pcts["departure_hour_frac"], y=pcts[0.90],
        fill=None, mode="lines", line_color="rgba(249,115,22,0.5)", name="90th"
    ))
    fig.add_trace(go.Scatter(
        x=pcts["departure_hour_frac"], y=pcts[0.75],
        fill=None, mode="lines", line_color="rgba(234,179,8,0.5)", name="75th"
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Departure Time (hour)",
        yaxis_title="Travel Time (min)",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)


# ──────────────────────────────────────────────────────────────
# TAB 3: DEPARTURE ADVISOR (with Tomorrow's Commute)
# ──────────────────────────────────────────────────────────────
with tab3:
    st.header("🎯 Departure Advisor")

    # ┌──────────────────────────────────────────────────────────┐
    # │  TOMORROW'S COMMUTE — Live Forecast + Auto Recommendation│
    # └──────────────────────────────────────────────────────────┘
    tomorrow_fc = None
    if forecasts and len(forecasts) >= 2:
        tomorrow_fc = forecasts[1]  # index 0=today, 1=tomorrow

    if tomorrow_fc and tomorrow_fc["day_of_week_num"] < 5:  # weekday
        st.markdown("### 🗓️ Tomorrow's Commute — Live Prediction")

        emoji_map = {"Clear": "☀️", "Rain": "🌧️", "Heavy Rain": "⛈️", "Fog": "🌫️"}
        wx_emoji = emoji_map.get(tomorrow_fc["weather_category"], "🌤️")
        wx_cat = tomorrow_fc["weather_category"]
        dow_num = tomorrow_fc["day_of_week_num"]
        day_name = tomorrow_fc["day_name"]

        # Auto-compute recommendations for 8:00 AM and 9:00 AM arrivals
        rec_8 = find_optimal_departure(
            models, le_weather, "08:00", dow_num, wx_cat, 0.95,
            distance_scale=dist_scale
        )
        rec_9 = find_optimal_departure(
            models, le_weather, "09:00", dow_num, wx_cat, 0.95,
            distance_scale=dist_scale
        )

        # Risk context
        crash_rate_rush = df[
            (df["departure_hour_frac"].between(7.0, 8.5)) &
            (df["weather"] == wx_cat)
        ]["crash_on_route"].mean()

        st.markdown(f"""
<div class="tomorrow-card">
<h3 style="margin-top:0; color: #a855f7 !important;">{wx_emoji} {day_name}, {tomorrow_fc["date"]} — {tomorrow_fc["weather_desc"]}</h3>
<p style="color: #c4c4cc; font-size: 0.95em;">
    Precipitation: <strong>{tomorrow_fc["precip_probability"]}%</strong> · 
    Temperature: <strong>{tomorrow_fc["temp_min_f"]:.0f}–{tomorrow_fc["temp_max_f"]:.0f}°F</strong> ·
    Route: <strong>{route_label}</strong> ({route_distance} mi) ·
    Rush-hour crash rate ({wx_cat}): <strong>{crash_rate_rush:.1%}</strong>
</p>
</div>
""", unsafe_allow_html=True)

        tcol1, tcol2 = st.columns(2)
        with tcol1:
            if rec_8["recommended_departure"]:
                st.metric(
                    "🏢 Arrive by 8:00 AM (95% confidence)",
                    f"Leave at {rec_8['recommended_departure']}",
                    f"~{rec_8['predicted_travel_min']:.0f} min travel, {rec_8['buffer_minutes']:.0f} min buffer"
                )
            else:
                st.warning("⚠️ 8:00 AM arrival may not be feasible with 95% confidence")

        with tcol2:
            if rec_9["recommended_departure"]:
                st.metric(
                    "🏢 Arrive by 9:00 AM (95% confidence)",
                    f"Leave at {rec_9['recommended_departure']}",
                    f"~{rec_9['predicted_travel_min']:.0f} min travel, {rec_9['buffer_minutes']:.0f} min buffer"
                )
            else:
                st.warning("⚠️ 9:00 AM arrival may not be feasible with 95% confidence")

        # Insight
        if wx_cat in ("Rain", "Heavy Rain"):
            clear_rec = find_optimal_departure(
                models, le_weather, "08:00", dow_num, "Clear", 0.95,
                distance_scale=dist_scale
            )
            if clear_rec["recommended_departure"] and rec_8["recommended_departure"]:
                clear_dep_dt = datetime.strptime(clear_rec["recommended_departure"], "%H:%M")
                rain_dep_dt = datetime.strptime(rec_8["recommended_departure"], "%H:%M")
                delta = (clear_dep_dt - rain_dep_dt).total_seconds() / 60
                if delta > 0:
                    st.info(
                        f"🌧️ **Weather impact**: {wx_cat} conditions mean leaving "
                        f"**{delta:.0f} minutes earlier** than a clear day to arrive by 8:00 AM."
                    )

        st.divider()

    # ┌──────────────────────────────────────────────────────────┐
    # │            CUSTOM DEPARTURE QUERY                        │
    # └──────────────────────────────────────────────────────────┘
    st.markdown(
        "### 🔧 Custom Query\n"
        "Pick any target arrival, weather, and day to get a personalized recommendation."
    )

    acol1, acol2, acol3, acol4 = st.columns(4)

    with acol1:
        target_hour = st.selectbox("Target Arrival Hour", list(range(6, 22)), index=2)
    with acol2:
        target_min = st.selectbox("Target Arrival Minute", [0, 15, 30, 45], index=0)
    with acol3:
        adv_weather = st.selectbox(
            "Expected Weather",
            ["Clear", "Rain", "Heavy Rain", "Fog"],
            index=0
        )
    with acol4:
        adv_dow = st.selectbox(
            "Day of Week",
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            index=2
        )

    confidence = st.slider(
        "Confidence Level",
        min_value=0.50, max_value=0.95, value=0.95, step=0.05,
        help="Higher = more conservative. 95% means you'll be on time 95% of the time."
    )

    target_str = f"{target_hour:02d}:{target_min:02d}"
    dow_num = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"].index(adv_dow)

    if st.button("🔍 Find Optimal Departure", type="primary", use_container_width=True):
        result = find_optimal_departure(
            models, le_weather, target_str, dow_num, adv_weather, confidence,
            distance_scale=dist_scale
        )

        if result["recommended_departure"]:
            st.divider()

            rcol1, rcol2, rcol3, rcol4 = st.columns(4)
            rcol1.metric("🚗 Depart At", result["recommended_departure"])
            rcol2.metric("⏱️ Est. Travel", f"{result['predicted_travel_min']:.0f} min")
            rcol3.metric("🏁 Est. Arrival", result["predicted_arrival"])
            rcol4.metric("⏳ Buffer", f"{result['buffer_minutes']:.0f} min")

            st.success(
                f"**Leave at {result['recommended_departure']}** to arrive by "
                f"**{target_str}** with **{confidence:.0%} confidence** "
                f"on a **{adv_dow}** with **{adv_weather}** weather. "
                f"Route: **{route_label}** ({route_distance} mi)"
            )

            # Visualization: all candidates
            st.subheader("All Departure Options")
            cand_df = pd.DataFrame(result["all_candidates"])

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=cand_df["departure"],
                y=cand_df["predicted_travel"],
                marker_color=[
                    "#22c55e" if ot else "#ef4444" for ot in cand_df["on_time"]
                ],
                text=cand_df["predicted_arrival"],
                textposition="outside",
                hovertemplate="Depart: %{x}<br>Travel: %{y:.0f} min<br>Arrive: %{text}<extra></extra>",
            ))

            # Target line
            fig.add_hline(
                y=(datetime.strptime(target_str, "%H:%M") -
                   datetime.strptime("05:00", "%H:%M")).total_seconds() / 60,
                line_dash="dash", line_color="yellow",
                annotation_text=f"Target: {target_str}",
                annotation_position="top left",
            )

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis_title="Departure Time",
                yaxis_title=f"Predicted Travel Time ({confidence:.0%} quantile, min)",
                height=450,
                xaxis=dict(dtick=6),  # show every 6th label (~30 min)
            )
            st.plotly_chart(fig, use_container_width=True)

            st.caption("🟢 Green = on time | 🔴 Red = late at this confidence level")
        else:
            st.error("⚠️ No departure time in the 5:00–10:00 window can guarantee arrival on time at this confidence level.")


# ──────────────────────────────────────────────────────────────
# TAB 4: RISK ANALYSIS
# ──────────────────────────────────────────────────────────────
with tab4:
    st.header("🔥 Risk Analysis")
    st.markdown("Probability of being **late** for each departure slot, across conditions.")

    st.divider()

    rcol1, rcol2 = st.columns(2)
    with rcol1:
        risk_target_h = st.selectbox("Target Arrival Hour ", list(range(6, 22)), index=2, key="risk_h")
    with rcol2:
        risk_target_m = st.selectbox("Target Arrival Minute ", [0, 15, 30, 45], index=0, key="risk_m")

    risk_target = f"{risk_target_h:02d}:{risk_target_m:02d}"
    risk_target_dt = datetime.strptime(risk_target, "%H:%M")

    # Build risk matrix
    weather_types = ["Clear", "Fog", "Rain", "Heavy Rain"]
    dep_times = [f"{h:02d}:{m:02d}" for h in range(5, 21) for m in range(0, 60, 15)]

    risk_data = []
    for weather in weather_types:
        for dep_str in dep_times:
            dep_dt = datetime.strptime(dep_str, "%H:%M")
            dep_frac = dep_dt.hour + dep_dt.minute / 60.0

            # predict at 50th, 75th, 90th, 95th
            late_probs = {}
            for q in [0.50, 0.75, 0.90, 0.95]:
                pred = predict_travel_time(models, le_weather, dep_frac, 2, weather, q) * dist_scale
                arr = dep_dt + timedelta(minutes=float(pred))
                late_probs[q] = arr > risk_target_dt

            # Estimate P(late) — rough interpolation
            if not late_probs[0.50]:
                if not late_probs[0.75]:
                    if not late_probs[0.90]:
                        if not late_probs[0.95]:
                            p_late = 0.02
                        else:
                            p_late = 0.07
                    else:
                        p_late = 0.15
                else:
                    p_late = 0.35
            else:
                p_late = 0.70

            risk_data.append({
                "departure": dep_str,
                "weather": weather,
                "p_late": p_late,
            })

    risk_df = pd.DataFrame(risk_data)

    # Heatmap
    st.subheader(f"Late Probability Heatmap — Target: {risk_target}")

    risk_pivot = risk_df.pivot_table(
        values="p_late", index="weather", columns="departure"
    )
    risk_pivot = risk_pivot.reindex(weather_types)

    fig = px.imshow(
        risk_pivot,
        color_continuous_scale=["#22c55e", "#eab308", "#ef4444", "#7f1d1d"],
        labels={"x": "Departure Time", "y": "Weather", "color": "P(Late)"},
        aspect="auto",
        zmin=0, zmax=0.8,
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=350,
        xaxis=dict(dtick=2),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Risk by departure time (line chart)
    st.subheader("Late Probability by Departure Time")
    fig = go.Figure()
    color_map = {"Clear": "#22c55e", "Fog": "#f59e0b", "Rain": "#3b82f6", "Heavy Rain": "#ef4444"}
    for weather in weather_types:
        subset = risk_df[risk_df["weather"] == weather]
        fig.add_trace(go.Scatter(
            x=subset["departure"], y=subset["p_late"],
            mode="lines+markers", name=weather,
            line=dict(color=color_map[weather], width=3),
            marker=dict(size=5),
        ))
    fig.add_hline(y=0.05, line_dash="dot", line_color="white",
                   annotation_text="5% risk threshold")
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis_title="P(Late)",
        xaxis_title="Departure Time",
        height=400,
        xaxis=dict(dtick=4),
        yaxis=dict(tickformat=".0%"),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.info(
        "💡 **Interpretation**: The green zone means you're almost certainly on time. "
        "Red means you should leave earlier or expect to be late. "
        "Use the **Departure Advisor** tab to get a specific recommendation."
    )
