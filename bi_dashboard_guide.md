# 📊 SmartCommute — BI Dashboard Build Guide

> **Dataset file:** `smartcommute_bi_data.csv` (94,482 rows × 39 columns)
>
> Import this single CSV — all columns are pre-computed for drag-and-drop.

---

## Option A: Tableau Public (Free, works on Mac)

### Setup
1. Download **Tableau Public** from [public.tableau.com](https://public.tableau.com) (free, Mac-compatible)
2. Open Tableau Public → **Connect → Text file** → select `smartcommute_bi_data.csv`
3. In the Data Source tab, verify these data types:
   - `date` → Date
   - `travel_time_min`, `departure_hour_frac`, `congestion_pct` → Number (decimal)
   - `crash_on_route`, `on_time_8h`, `on_time_9h` → Number (whole)
   - Everything else → String (keep defaults)

---

### Page 1: Route Overview

**KPI Bar (top row — use a horizontal container with 4 sheets):**

| KPI | Calculation | Format |
|---|---|---|
| Avg Travel Time | `AVG([travel_time_min])` | `#0 "min"` |
| 95th Percentile | `PERCENTILE([travel_time_min], 0.95)` | `#0 "min"` |
| Crash Rate | `SUM([crash_on_route]) / COUNT([crash_on_route])` | `0.0%` |
| Rainy Day % | `COUNTD(IF [weather]="Rain" OR [weather]="Heavy Rain" THEN [date] END) / COUNTD([date])` | `0.0%` |

**Chart 1 — Travel Time Distribution (Histogram):**
- Drag `travel_time_min` to Columns → right-click → **Dimension** → **Create Bins** (bin size = 2)
- Drag the bin to Columns, `CNT(travel_time_min)` to Rows
- Color: gradient blue
- Add reference lines: Median (dashed blue), 95th percentile (dashed red)

**Chart 2 — Weather Breakdown (Pie/Donut):**
- Drag `weather` to Color, `CNT(date)` to Angle
- Sort by `weather_severity`
- Colors: Clear=#22c55e, Rain=#3b82f6, Heavy Rain=#ef4444, Fog=#a78bfa

**Chart 3 — Monthly Trend (Line):**
- `year_month` on Columns, `AVG(travel_time_min)` on Rows
- Add `PERCENTILE(travel_time_min, 0.95)` as second axis
- Dual axis, synchronized

---

### Page 2: Time Analysis

**Chart 1 — Heatmap: Day of Week × Departure Hour:**
- Rows: `day_of_week` (sort Mon→Fri)
- Columns: `departure_hour_bucket`
- Color: `AVG(travel_time_min)` → Red-Green diverging (reversed)
- Label: `AVG(travel_time_min)` formatted as `#0`

**Chart 2 — Dual Rush Hour Profile (Area Chart):**
- Columns: `departure_hour_frac` (continuous)
- Rows: `AVG(travel_time_min)`
- Color mark: create calculated field:
  ```
  IF [departure_hour_frac] >= 7 AND [departure_hour_frac] <= 9 THEN "AM Rush"
  ELSEIF [departure_hour_frac] >= 16.5 AND [departure_hour_frac] <= 18.5 THEN "PM Rush"
  ELSE "Off-Peak"
  END
  ```
- Colors: AM Rush=#ef4444, PM Rush=#f97316, Off-Peak=#6366f1

**Chart 3 — Congestion by Time Period (Bar):**
- Rows: `time_period` (sorted by `time_period_sort`)
- Columns: `AVG(congestion_pct)`
- Color: `AVG(congestion_pct)` → Orange-Red sequential
- Label: show values

---

### Page 3: Weather & Risk Impact

**Chart 1 — Travel Time by Weather (Box Plot):**
- Columns: `weather` (sorted by `weather_severity`)
- Use the built-in box plot: Analytics pane → drag **Box Plot** onto the view
- Reference: `travel_time_min`

**Chart 2 — Crash Impact (Grouped Bar):**
- Columns: `crash_label`
- Rows: `AVG(travel_time_min)`
- Color: `crash_label`
- Add: `weather` as a column detail for side-by-side comparison

**Chart 3 — Risk Heatmap: Weather × Time Period:**
- Rows: `weather` (sorted by `weather_severity`)
- Columns: `time_period` (sorted by `time_period_sort`)
- Color: `AVG(travel_time_min)` → Red-Yellow-Green diverging (reversed)
- Label: `AVG(travel_time_min)` formatted `#0`

---

### Page 4: Departure Advisor

**Chart 1 — On-Time Probability by Departure Hour:**
- Create calculated field `On-Time Rate (8 AM)`: `AVG([on_time_8h])`
- Columns: `departure_hour_frac` (continuous, filter 5–10)
- Rows: `On-Time Rate (8 AM)`
- Mark type: Area, with line
- Add reference line at 95% (dashed green)
- Color: gradient green

**Chart 2 — On-Time by Weather × Departure Time (Scatter):**
- Columns: `departure_hour_frac`
- Rows: `AVG(on_time_8h)`
- Color: `weather`
- Mark type: Line
- Filter: departure_hour_frac 5–10

**Chart 3 — PM On-Time (6 PM Target):**
- Same as Chart 1 but use `on_time_18h`
- Filter: departure_hour_frac 14–20

**Filters (add to all pages as global filters):**
- `weather` → dropdown
- `day_of_week` → checkboxes
- `season` → dropdown
- `year` → single select

---

### Publishing
1. **File → Save to Tableau Public** (requires free account)
2. Your dashboard will be hosted at `public.tableau.com/app/profile/YOUR_NAME`
3. Share the link on LinkedIn!

---

## Option B: Power BI (Free Web Version)

### Setup
1. Go to [app.powerbi.com](https://app.powerbi.com) → sign in with Microsoft account
2. **Get Data → Text/CSV** → upload `smartcommute_bi_data.csv`
3. In Power Query Editor, verify column types (should auto-detect)

### DAX Measures to Create

Click **New Measure** in the modeling tab for each:

```
Avg Travel Time = AVERAGE('smartcommute_bi_data'[travel_time_min])

95th Percentile = PERCENTILE.INC('smartcommute_bi_data'[travel_time_min], 0.95)

Crash Rate = DIVIDE(SUM('smartcommute_bi_data'[crash_on_route]), COUNT('smartcommute_bi_data'[crash_on_route]))

On-Time Rate 8AM = AVERAGE('smartcommute_bi_data'[on_time_8h])

On-Time Rate 6PM = AVERAGE('smartcommute_bi_data'[on_time_18h])

Rainy Day Pct = 
DIVIDE(
    CALCULATE(DISTINCTCOUNT('smartcommute_bi_data'[date]),
              'smartcommute_bi_data'[weather] IN {"Rain", "Heavy Rain"}),
    DISTINCTCOUNT('smartcommute_bi_data'[date])
)

Total Records = COUNTROWS('smartcommute_bi_data')
```

### Page Layout

**Use the same 4-page structure as Tableau above.** The column names are identical — just drag the same fields and use the DAX measures for KPI cards.

**Power BI-specific tips:**
- Use **Card** visuals for KPIs
- Use **Matrix** visual for heatmaps (Rows: day_of_week, Columns: departure_hour_bucket, Values: Avg Travel Time, with conditional formatting → color scale)
- Use **Line chart** for time series
- Use **Stacked bar** for weather breakdowns
- Add **Slicers** for: weather, day_of_week, season, year
- Theme: use Dark theme → Format → Theme → select "Storm"

---

## 🎨 Recommended Color Palette (Both Tools)

| Element | Hex Color |
|---|---|
| Primary (brand) | `#6366F1` (indigo) |
| AM Rush | `#EF4444` (red) |
| PM Rush | `#F97316` (orange) |
| Off-Peak | `#22C55E` (green) |
| Clear weather | `#22C55E` |
| Rain | `#3B82F6` (blue) |
| Heavy Rain | `#EF4444` (red) |
| Fog | `#A78BFA` (purple) |
| Background | `#0F172A` (dark slate) |
| Card background | `#1E293B` |

---

## 📁 Column Reference (All 39 Columns)

| Column | Type | Description |
|---|---|---|
| `date` | Date | Commute date |
| `day_of_week` | String | Monday–Friday |
| `day_of_week_num` | Int | 0=Mon, 4=Fri |
| `season` | String | winter/spring/summer/fall |
| `departure_time` | String | HH:MM format |
| `departure_hour` | Int | Hour (5–20) |
| `departure_minute` | Int | Minute (0–55) |
| `departure_hour_frac` | Float | Continuous hour (e.g., 7.5) |
| `weather` | String | Clear/Rain/Heavy Rain/Fog |
| `crash_on_route` | Int | 0 or 1 |
| `rush_hour_multiplier` | Float | Congestion multiplier |
| `base_travel_min` | Float | Base drive time |
| `weather_penalty_min` | Float | Weather-added minutes |
| `crash_delay_min` | Float | Crash-added minutes |
| `travel_time_min` | Float | **Total travel time** |
| `arrival_time` | String | HH:MM arrival |
| `distance_miles` | Float | Route distance |
| `time_period` | String | Human-readable time bucket |
| `time_period_sort` | Int | Sort order (1–9) |
| `departure_time_label` | String | Formatted HH:MM |
| `departure_hour_bucket` | String | Rounded hour (e.g., "07:00") |
| `travel_time_category` | String | Fast/Normal/Slow/Very Slow/Extreme |
| `on_time_8h` | Int | Would arrive by 8:00 AM? (0/1) |
| `on_time_9h` | Int | Would arrive by 9:00 AM? (0/1) |
| `on_time_17h` | Int | Would arrive by 5:00 PM? (0/1) |
| `on_time_18h` | Int | Would arrive by 6:00 PM? (0/1) |
| `month` / `month_name` | Int/String | Month number and name |
| `year` / `year_month` | Int/String | Year and YYYY-MM |
| `week_number` | Int | ISO week number |
| `is_am_rush` / `is_pm_rush` | Int | Rush hour flags (0/1) |
| `is_rush_hour` | Int | Any rush hour (0/1) |
| `congestion_pct` | Float | Congestion as % above baseline |
| `total_delay_min` | Float | Weather + crash delay combined |
| `weather_severity` | Int | Severity order (1–4) |
| `day_type` | String | Mon/Fri (Lighter) or Tue-Thu (Heavier) |
| `crash_label` | String | "No Crash" or "Crash on Route" |
