"""
Peer Comparison Dashboard - Indian IT Sector (Prototype)

Run with:
    pip install streamlit pandas plotly
    streamlit run dashboard.py

IMPORTANT: The numbers in SAMPLE_DATA are rough, illustrative figures only.
Replace them with real data (screener.in, annual reports) before drawing
any conclusions.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------
# 1. DATA  (edit these numbers with real figures from screener.in)
# ---------------------------------------------------------------------
SAMPLE_DATA = [
    {"Company": "TCS", "Revenue CAGR 3Y (%)": 11, "Profit CAGR 3Y (%)": 9,
     "Operating Margin (%)": 26, "ROE (%)": 50, "ROCE (%)": 64,
     "Debt/Equity": 0.05, "Interest Coverage (x)": 90,
     "Cash Conversion (OCF/PAT)": 1.05, "P/E (x)": 30, "EV/EBITDA (x)": 21},
    {"Company": "Infosys", "Revenue CAGR 3Y (%)": 14, "Profit CAGR 3Y (%)": 10,
     "Operating Margin (%)": 21, "ROE (%)": 31, "ROCE (%)": 40,
     "Debt/Equity": 0.08, "Interest Coverage (x)": 60,
     "Cash Conversion (OCF/PAT)": 1.00, "P/E (x)": 24, "EV/EBITDA (x)": 16},
    {"Company": "Wipro", "Revenue CAGR 3Y (%)": 10, "Profit CAGR 3Y (%)": 3,
     "Operating Margin (%)": 17, "ROE (%)": 16, "ROCE (%)": 19,
     "Debt/Equity": 0.20, "Interest Coverage (x)": 20,
     "Cash Conversion (OCF/PAT)": 1.30, "P/E (x)": 20, "EV/EBITDA (x)": 12},
    {"Company": "HCL Tech", "Revenue CAGR 3Y (%)": 12, "Profit CAGR 3Y (%)": 8,
     "Operating Margin (%)": 22, "ROE (%)": 23, "ROCE (%)": 29,
     "Debt/Equity": 0.08, "Interest Coverage (x)": 40,
     "Cash Conversion (OCF/PAT)": 1.10, "P/E (x)": 23, "EV/EBITDA (x)": 14},
    {"Company": "Tech Mahindra", "Revenue CAGR 3Y (%)": 9, "Profit CAGR 3Y (%)": -2,
     "Operating Margin (%)": 11, "ROE (%)": 11, "ROCE (%)": 14,
     "Debt/Equity": 0.07, "Interest Coverage (x)": 15,
     "Cash Conversion (OCF/PAT)": 1.40, "P/E (x)": 35, "EV/EBITDA (x)": 17},
]

# Metric name -> True if higher is better, False if lower is better
QUALITY_METRICS = {
    "Revenue CAGR 3Y (%)": True,
    "Profit CAGR 3Y (%)": True,
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
    "Growth": ["Revenue CAGR 3Y (%)", "Profit CAGR 3Y (%)"],
    "Profitability": ["Operating Margin (%)", "ROE (%)", "ROCE (%)"],
    "Financial Health": ["Debt/Equity", "Interest Coverage (x)",
                         "Cash Conversion (OCF/PAT)"],
    "Valuation": ["P/E (x)", "EV/EBITDA (x)"],
}

# ---------------------------------------------------------------------
# 2. HELPER FUNCTIONS
# ---------------------------------------------------------------------
def percentile_scores(df: pd.DataFrame, metrics: dict) -> pd.DataFrame:
    """Score each company 0-100 on each metric relative to the selected peers.
    Best company gets 100, worst gets the lowest. Direction-aware."""
    scores = pd.DataFrame(index=df.index)
    for col, higher_is_better in metrics.items():
        scores[col] = df[col].rank(pct=True, ascending=higher_is_better) * 100
    return scores


# ---------------------------------------------------------------------
# 3. PAGE SETUP
# ---------------------------------------------------------------------
st.set_page_config(page_title="Peer Comparison Dashboard", layout="wide")
st.title("Peer Comparison Dashboard: Indian IT Sector")
st.warning(
    "Prototype using rough, illustrative sample data. "
    "Replace with real figures before drawing conclusions."
)

df_all = pd.DataFrame(SAMPLE_DATA).set_index("Company")

# ---------------------------------------------------------------------
# 4. SIDEBAR
# ---------------------------------------------------------------------
st.sidebar.header("Controls")
selected = st.sidebar.multiselect(
    "Companies to compare", list(df_all.index), default=list(df_all.index)
)
if len(selected) < 2:
    st.info("Select at least two companies to compare.")
    st.stop()

df = df_all.loc[selected]

# ---------------------------------------------------------------------
# 5. TABS
# ---------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["Comparison table", "Metric charts", "Quality vs valuation", "Notes"]
)

# --- Tab 1: table + best in each metric --------------------------------
with tab1:
    st.subheader("All 10 factors side by side")
    st.dataframe(df, use_container_width=True)

    st.subheader("Best company on each factor")
    rows = []
    for col, higher_is_better in ALL_METRICS.items():
        best = df[col].idxmax() if higher_is_better else df[col].idxmin()
        rows.append({
            "Factor": col,
            "Best": best,
            "Value": df.loc[best, col],
            "Better when": "Higher" if higher_is_better else "Lower",
        })
    st.dataframe(pd.DataFrame(rows).set_index("Factor"),
                 use_container_width=True)

# --- Tab 2: one bar chart per metric group -----------------------------
with tab2:
    group = st.selectbox("Category", list(GROUPS.keys()))
    cols = st.columns(len(GROUPS[group]))
    for c, metric in zip(cols, GROUPS[group]):
        fig = px.bar(df.reset_index(), x="Company", y=metric,
                     color="Company", title=metric, text_auto=".2f")
        fig.update_layout(showlegend=False)
        c.plotly_chart(fig, use_container_width=True)

# --- Tab 3: quality score vs valuation ---------------------------------
with tab3:
    st.subheader("Is the price justified by the quality?")
    quality_scores = percentile_scores(df, QUALITY_METRICS)
    df_plot = pd.DataFrame({
        "Quality score (0-100)": quality_scores.mean(axis=1),
        "EV/EBITDA (x)": df["EV/EBITDA (x)"],
        "P/E (x)": df["P/E (x)"],
    }).reset_index()

    fig = px.scatter(df_plot, x="Quality score (0-100)", y="EV/EBITDA (x)",
                     text="Company", size="P/E (x)", color="Company")
    fig.update_traces(textposition="top center")
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Top-left = expensive for its quality. Bottom-right = high quality at a "
        "lower price (potentially attractive). Bubble size = P/E. "
        "Quality score is the average peer-relative rank across the 8 "
        "growth, profitability and health factors."
    )

    st.subheader("Quality profile (radar)")
    company = st.selectbox("Company", list(df.index))
    fig2 = go.Figure(go.Scatterpolar(
        r=quality_scores.loc[company].tolist(),
        theta=list(QUALITY_METRICS.keys()),
        fill="toself", name=company,
    ))
    fig2.update_layout(polar=dict(radialaxis=dict(range=[0, 100])),
                       showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

# --- Tab 4: notes ------------------------------------------------------
with tab4:
    st.markdown(
        """
**How scoring works:** each company is ranked against the others you selected
on every factor (direction-aware: lower debt scores better, higher ROE scores
better). Scores are relative to the chosen peers, so they change when you add
or remove companies.

**Limitations of this prototype**
- Data is illustrative, not real.
- Valuation is kept separate from quality because a low multiple is not
  automatically "good"; it may reflect weaker fundamentals.
- Interest coverage is less meaningful for near debt-free companies.

**Next steps:** replace sample data with real figures, add a source/date
column, add 5-year trend charts, then try another sector.
        """
    )
