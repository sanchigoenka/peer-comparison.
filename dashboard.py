"""
Peer Comparison Dashboard - Indian Listed Companies (v2)

Features
- 10 companies across IT and FMCG (compare within a sector)
- Up to 10 years of data per company (FY2017 - FY2026)
- Compare a single year OR the average over any range of years
- Trend chart over time for any metric

Data comes from data.csv (same folder). Fill it with real figures.
A "demo data" switch generates RANDOM numbers just to show the features.

Run locally:
    pip install streamlit pandas plotly numpy
    streamlit run dashboard.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------
# 1. CONFIG
# ---------------------------------------------------------------------
COMPANIES = {
    # IT
    "TCS": "IT", "Infosys": "IT", "Wipro": "IT", "HCL Tech": "IT",
    "Tech Mahindra": "IT",
    # FMCG
    "Hindustan Unilever": "FMCG", "ITC": "FMCG", "Nestle India": "FMCG",
    "Britannia": "FMCG", "Dabur": "FMCG",
}
YEARS = list(range(2017, 2027))  # FY2017 ... FY2026
DATA_SOURCE = "Screener.in (Consolidated financials)"
DATA_EXPORTED = "29-09-2026"

# Metric -> True if higher is better, False if lower is better
QUALITY_METRICS = {
    "Revenue Growth YoY (%)": True,
    "Profit Growth YoY (%)": True,
    "Operating Margin (%)": True,
    "ROE (%)": True,
    "ROCE (%)": True,
    "Debt/Equity": False,
    "Interest Coverage (x)": True,
    "Cash Conversion (OCF/PAT)": True,
}
VALUATION_METRICS = {"P/E (x)": False, "EV/EBITDA (x)": False}
ALL_METRICS = {**QUALITY_METRICS, **VALUATION_METRICS}

GROUPS = {
    "Growth": ["Revenue Growth YoY (%)", "Profit Growth YoY (%)"],
    "Profitability": ["Operating Margin (%)", "ROE (%)", "ROCE (%)"],
    "Financial Health": ["Debt/Equity", "Interest Coverage (x)",
                         "Cash Conversion (OCF/PAT)"],
    "Valuation": ["P/E (x)", "EV/EBITDA (x)"],
}


# ---------------------------------------------------------------------
# 2. DATA LOADING
# ---------------------------------------------------------------------
@st.cache_data
def load_csv() -> pd.DataFrame:
    path = Path(__file__).parent / "data.csv"
    if not path.exists():
        return pd.DataFrame(columns=["Company", "Sector", "Year", *ALL_METRICS])
    return pd.read_csv(path)


@st.cache_data
def make_demo() -> pd.DataFrame:
    """RANDOM numbers, only to demonstrate the dashboard. Not real."""
    rng = np.random.default_rng(42)
    base = {  # rough sector-level starting points, in ALL_METRICS order
        "IT":   [12, 10, 22, 25, 32, 0.08, 50, 1.05, 26, 17],
        "FMCG": [9, 9, 22, 35, 45, 0.10, 60, 1.00, 50, 32],
        "Auto": [10, 12, 12, 15, 18, 0.40, 12, 1.20, 22, 13],
    }
    rows = []
    for company, sector in COMPANIES.items():
        scale = rng.normal(1, 0.25, len(ALL_METRICS))
        for year in YEARS:
            noise = rng.normal(1, 0.15, len(ALL_METRICS))
            vals = np.abs(np.array(base[sector]) * scale * noise)
            rows.append({"Company": company, "Sector": sector, "Year": year,
                         **dict(zip(ALL_METRICS, vals))})
    return pd.DataFrame(rows)


def percentile_scores(df: pd.DataFrame, metrics: dict) -> pd.DataFrame:
    """0-100 score per metric relative to the selected peers (direction-aware)."""
    out = pd.DataFrame(index=df.index)
    for col, higher_is_better in metrics.items():
        out[col] = df[col].rank(pct=True, ascending=higher_is_better) * 100
    return out


# ---------------------------------------------------------------------
# 3. PAGE + SIDEBAR
# ---------------------------------------------------------------------
st.set_page_config(page_title="Peer Comparison Dashboard", layout="wide")
st.title("Peer Comparison Dashboard: Indian Listed Companies")
st.caption(f"Source: {DATA_SOURCE} · Data exported {DATA_EXPORTED} · "
          f"Figures in Rs crore unless stated as a ratio or multiple")

my_data = load_csv()
has_real = my_data[list(ALL_METRICS)].notna().any().any() if len(my_data) else False

st.sidebar.header("Controls")
source = st.sidebar.radio(
    "Data source",
    ["My data (data.csv)", "Demo data (random, not real)"],
    index=0 if has_real else 1,
)
if source.startswith("Demo"):
    data = make_demo()
    st.error("DEMO MODE: these numbers are randomly generated to show how the "
             "dashboard works. They are NOT real company data.")
else:
    data = my_data
    if not has_real:
        st.info("data.csv has no numbers yet. Fill it in (see the Notes tab), "
                "or switch to Demo data in the sidebar to explore the features.")
        st.stop()

# Sector + company selection
sector = st.sidebar.selectbox("Sector", sorted(set(COMPANIES.values())))
sector_companies = [c for c, s in COMPANIES.items() if s == sector]
selected = st.sidebar.multiselect("Companies", sector_companies,
                                  default=sector_companies)

# Period selection
mode = st.sidebar.radio("Compare by", ["Single year", "Average over years"])
if mode == "Single year":
    year = st.sidebar.select_slider("Year", options=YEARS, value=YEARS[-1],
                                    format_func=lambda y: f"FY{y}")
    y_start = y_end = year
    period_label = f"FY{year}"
else:
    y_start, y_end = st.sidebar.slider(
        "Year range (average)", YEARS[0], YEARS[-1],
        (YEARS[-3], YEARS[-1]), format="FY%d")
    n = y_end - y_start + 1
    period_label = f"Average FY{y_start}-FY{y_end} ({n} years)"

if len(selected) < 2:
    st.info("Select at least two companies in the sidebar.")
    st.stop()

# ---------------------------------------------------------------------
# 4. BUILD THE COMPARISON TABLE FOR THE CHOSEN PERIOD
# ---------------------------------------------------------------------
metric_cols = list(ALL_METRICS)
period = data[data["Company"].isin(selected)
              & data["Year"].between(y_start, y_end)]

df = period.groupby("Company")[metric_cols].mean()  # mean() skips blanks
years_with_data = (period.dropna(subset=metric_cols, how="all")
                   .groupby("Company")["Year"].nunique())
df = df.dropna(how="all")
if len(df) < 2:
    st.warning("Not enough data in this period for at least two companies.")
    st.stop()

st.subheader(f"{sector} Sector Peer Comparison — {period_label}")

# ---------------------------------------------------------------------
# 5. TABS
# ---------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Comparison table", "Metric charts", "Trend over time",
     "Quality vs valuation", "Notes"])

with tab1:
    show = df.round(2).copy()
    show["Years of data"] = years_with_data.reindex(show.index)
    fmt = {col: "{:.2f}" for col in metric_cols}
    st.dataframe(show.style.format(fmt, na_rep="—"), use_container_width=True)
    st.download_button("Download this table (CSV)",
                       show.to_csv().encode(), "comparison.csv", "text/csv")

    st.markdown("**Best company on each factor**")
    rows = []
    for col, hib in ALL_METRICS.items():
        if df[col].notna().any():
            best = df[col].idxmax() if hib else df[col].idxmin()
            rows.append({"Factor": col, "Best": best,
                         "Value": round(df.loc[best, col], 2),
                         "Better when": "Higher" if hib else "Lower"})
    best_df = pd.DataFrame(rows).set_index("Factor")
    st.dataframe(best_df.style.format({"Value": "{:.2f}"}),
                 use_container_width=True)

with tab2:
    group = st.selectbox("Category", list(GROUPS))
    cols = st.columns(len(GROUPS[group]))
    for c, metric in zip(cols, GROUPS[group]):
        fig = px.bar(df.reset_index(), x="Company", y=metric, color="Company",
                     title=metric, text_auto=".2f")
        fig.update_layout(showlegend=False)
        c.plotly_chart(fig, use_container_width=True)

with tab3:
    metric = st.selectbox("Metric", metric_cols)
    trend = data[data["Company"].isin(selected)]
    fig = px.line(trend, x="Year", y=metric, color="Company", markers=True)
    fig.update_xaxes(tickmode="array", tickvals=YEARS,
                     ticktext=[f"FY{y}" for y in YEARS])
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Shows all available years for the selected companies, "
               "regardless of the period chosen in the sidebar.")

with tab4:
    st.markdown("**Is the price justified by the quality?**")
    q = percentile_scores(df, QUALITY_METRICS)
    plot = pd.DataFrame({
        "Quality score (0-100)": q.mean(axis=1),
        "EV/EBITDA (x)": df["EV/EBITDA (x)"],
        "P/E (x)": df["P/E (x)"],
    }).dropna().reset_index()
    fig = px.scatter(plot, x="Quality score (0-100)", y="EV/EBITDA (x)",
                     text="Company", size="P/E (x)", color="Company")
    fig.update_traces(textposition="top center")
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Top-left = expensive for its quality. Bottom-right = high "
               "quality at a lower price. Bubble size = P/E.")

    st.markdown("**Quality profile (radar)**")
    company = st.selectbox("Company", list(df.index))
    fig2 = go.Figure(go.Scatterpolar(
        r=q.loc[company].fillna(0).tolist(),
        theta=list(QUALITY_METRICS), fill="toself"))
    fig2.update_layout(polar=dict(radialaxis=dict(range=[0, 100])),
                       showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

with tab5:
    st.markdown(
        f"""
**About this dashboard**
Compares Indian IT and FMCG companies on 10 financial factors covering
growth, profitability, financial health and valuation, across up to 10
years (FY2017-FY2026).

**Data source:** {DATA_SOURCE}, exported {DATA_EXPORTED}. Figures in Rs
crore unless the metric is already a ratio or multiple.

**How scoring works:** in the "Quality vs valuation" tab, each company is
ranked against the others you select (direction-aware — lower debt scores
better). Scores are relative to your chosen peers, so they shift when you
add or remove companies. Valuation is kept separate from the quality score
on purpose, since a cheap stock isn't automatically a good one.

**How averaging works:** the average is a simple mean of the yearly values
in your chosen range. Averaging YoY growth rates is a simplification; a
CAGR would be more precise for long periods.

**Limitations**
- Ratios such as margins and debt levels are not comparable across sectors
  (IT vs FMCG) — compare within a sector only. Banks need a different set
  of metrics entirely.
- Mergers or demergers (e.g. ITC's hotels demerger) can distort a
  company's year-on-year trend for the affected years.
- Data reflects each company's Consolidated financial statements at the
  time of export and may not include later restatements.
        """
    )
