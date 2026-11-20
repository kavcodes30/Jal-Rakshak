
from pathlib import Path

import pandas as pd
import plotly.express as px  # pyright: ignore[reportMissingImports]
import streamlit as st


RISK_COLORS = {
    "Low": "#2EAD69",
    "Moderate": "#E6A23C",
    "High": "#D94B4B"
}


@st.cache_data
def load_analytics_data(csv_path):

    df = pd.read_csv(csv_path)

    required = {"station", "t", "state", "target_risk"}
    missing = required.difference(df.columns)

    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(sorted(missing))
        )

    df["t"] = pd.to_datetime(df["t"], errors="coerce")
    df["target_risk"] = (
        df["target_risk"].astype(str).str.title()
    )

    df = df.dropna(
        subset=["station", "t", "state", "target_risk"]
    )

    df = df[
        df["target_risk"].isin(RISK_COLORS)
    ].copy()

    df["Month"] = df["t"].dt.to_period("M").dt.to_timestamp()

    return df


def render_analytics_page(
    csv_path="data/model_ready_dataset.csv"
):

    st.title("Historical Analytics & Risk Trends")

    st.caption(
        "Analysis of all available dated water-quality "
        "observations and their dataset risk labels."
    )

    csv_path = Path(csv_path)

    if not csv_path.exists():
        st.error(f"Dataset not found: {csv_path}")
        return

    try:
        df = load_analytics_data(str(csv_path))

    except Exception as exc:
        st.error(f"Could not load analytics data: {exc}")
        return

    if df.empty:
        st.warning("No valid historical observations found.")
        return

    # ---------------- FILTERS ----------------

    st.subheader("Analytics Filters")

    col1, col2 = st.columns(2)

    min_date = df["t"].min().date()
    max_date = df["t"].max().date()

    with col1:
        selected_dates = st.date_input(
            "Select date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="analytics_dates"
        )

    states = sorted(df["state"].unique().tolist())

    with col2:
        selected_states = st.multiselect(
            "Select states",
            options=states,
            default=states,
            key="analytics_states"
        )

    selected_risks = st.multiselect(
        "Select risk categories",
        options=["Low", "Moderate", "High"],
        default=["Low", "Moderate", "High"],
        key="analytics_risks"
    )

    if not isinstance(selected_dates, (tuple, list)) or len(selected_dates) != 2:
        st.warning("Please select a start date and end date.")
        return

    start_date, end_date = selected_dates

    if start_date > end_date:
        st.warning("Start date cannot be after end date.")
        return

    filtered = df[
        (df["t"].dt.date >= start_date)
        & (df["t"].dt.date <= end_date)
        & (df["state"].isin(selected_states))
        & (df["target_risk"].isin(selected_risks))
    ].copy()

    if filtered.empty:
        st.warning("No observations match the selected filters.")
        return

    # ---------------- SUMMARY METRICS ----------------

    high_count = int(
        (filtered["target_risk"] == "High").sum()
    )

    moderate_count = int(
        (filtered["target_risk"] == "Moderate").sum()
    )

    low_count = int(
        (filtered["target_risk"] == "Low").sum()
    )

    total = len(filtered)

    st.subheader("Historical Summary")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Observations", f"{total:,}")
    c2.metric("High Risk", f"{high_count:,}")
    c3.metric("Moderate Risk", f"{moderate_count:,}")
    c4.metric("Low Risk", f"{low_count:,}")

    # ---------------- RISK DISTRIBUTION ----------------

    st.divider()
    st.subheader("1. Overall Risk Distribution")

    distribution = (
        filtered["target_risk"]
        .value_counts()
        .reindex(["Low", "Moderate", "High"], fill_value=0)
        .reset_index()
    )

    distribution.columns = ["Risk Category", "Observations"]

    fig1 = px.pie(
        distribution,
        names="Risk Category",
        values="Observations",
        color="Risk Category",
        color_discrete_map=RISK_COLORS,
        hole=0.48
    )

    fig1.update_layout(
        height=400,
        legend_title_text="Risk Category"
    )

    st.plotly_chart(fig1, use_container_width=True)

    # ---------------- MONTHLY TREND ----------------

    st.divider()
    st.subheader("2. Monthly Risk Trends")

    monthly = (
        filtered.groupby(["Month", "target_risk"])
        .size()
        .reset_index(name="Observations")
    )

    fig2 = px.line(
        monthly,
        x="Month",
        y="Observations",
        color="target_risk",
        markers=True,
        color_discrete_map=RISK_COLORS,
        category_orders={
            "target_risk": ["Low", "Moderate", "High"]
        },
        labels={
            "Month": "Observation Month",
            "Observations": "Number of Records",
            "target_risk": "Risk Category"
        }
    )

    fig2.update_layout(height=450)

    st.plotly_chart(fig2, use_container_width=True)

    # ---------------- STATE COMPARISON ----------------

    st.divider()
    st.subheader("3. State-wise Risk Comparison")

    state_summary = (
        filtered.groupby(["state", "target_risk"])
        .size()
        .reset_index(name="Observations")
    )

    fig3 = px.bar(
        state_summary,
        x="state",
        y="Observations",
        color="target_risk",
        barmode="stack",
        color_discrete_map=RISK_COLORS,
        category_orders={
            "target_risk": ["Low", "Moderate", "High"]
        },
        labels={
            "state": "State",
            "Observations": "Number of Records",
            "target_risk": "Risk Category"
        }
    )

    fig3.update_layout(
        height=500,
        xaxis_tickangle=-35
    )

    st.plotly_chart(fig3, use_container_width=True)

    # ---------------- RISK TABLE ----------------

    st.divider()
    st.subheader("4. State-wise Risk Summary")

    pivot = pd.crosstab(
        filtered["state"],
        filtered["target_risk"]
    )

    pivot = pivot.reindex(
        columns=["Low", "Moderate", "High"],
        fill_value=0
    )

    pivot["Total"] = pivot.sum(axis=1)

    st.dataframe(
        pivot,
        use_container_width=True
    )

    # ---------------- DOWNLOAD ----------------

    st.divider()
    st.subheader("Export Historical Analysis")

    export = filtered[
        ["station", "state", "t", "target_risk"]
    ].copy()

    export = export.rename(
        columns={
            "station": "Station",
            "state": "State",
            "t": "Observation Date",
            "target_risk": "Risk Category"
        }
    )

    st.download_button(
        "Download Historical Data (CSV)",
        data=export.to_csv(index=False).encode("utf-8"),
        file_name="jal_rakshak_historical_analytics.csv",
        mime="text/csv",
        use_container_width=True
    )

    st.caption(
        "Each record represents a dated dataset observation, "
        "not a confirmed disease case or outbreak. Counts are "
        "observation counts, not counts of unique stations."
    )
