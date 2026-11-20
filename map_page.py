
from pathlib import Path
from importlib import import_module

import pandas as pd
import streamlit as st

from reports_store import get_submitted_reports

try:
    px = import_module("plotly.express")
except ModuleNotFoundError:
    px = None


RISK_COLORS = {
    "Low": "#2EAD69",
    "Moderate": "#E6A23C",
    "High": "#D94B4B",
}


@st.cache_data
def load_station_data(csv_path: str) -> pd.DataFrame:
    """Load historical observations and retain the latest record per station."""
    df = pd.read_csv(csv_path)

    required = {"station", "t", "lat", "lon", "state", "target_risk"}
    missing = required.difference(df.columns)

    if missing:
        raise ValueError(
            "The model-ready CSV is missing required columns: "
            + ", ".join(sorted(missing))
        )

    df["t"] = pd.to_datetime(df["t"], errors="coerce")
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    df = df.dropna(
        subset=["station", "t", "lat", "lon", "state", "target_risk"]
    )

    df = df[
        df["lat"].between(-90, 90)
        & df["lon"].between(-180, 180)
    ]

    df = (
        df.sort_values("t")
        .drop_duplicates(subset=["station"], keep="last")
        .copy()
    )

    df["target_risk"] = df["target_risk"].astype(str).str.title()
    df = df[df["target_risk"].isin(RISK_COLORS)]

    df["record_date"] = df["t"].dt.strftime("%d %b %Y")
    df["source"] = "Historical dataset"
    df["report_id"] = None

    return df


def load_submitted_reports() -> pd.DataFrame:
    """Load newly submitted reports from the local SQLite database."""
    reports = pd.DataFrame(get_submitted_reports())

    if reports.empty:
        return pd.DataFrame(
            columns=[
                "station", "state", "lat", "lon",
                "target_risk", "record_date",
                "source", "report_id"
            ]
        )

    reports["latitude"] = pd.to_numeric(
        reports["latitude"], errors="coerce"
    )
    reports["longitude"] = pd.to_numeric(
        reports["longitude"], errors="coerce"
    )

    reports["risk_level"] = reports["risk_level"].astype(str).str.title()

    reports = reports.dropna(
        subset=["latitude", "longitude", "state", "risk_level"]
    )

    reports = reports[
        reports["latitude"].between(-90, 90)
        & reports["longitude"].between(-180, 180)
        & reports["risk_level"].isin(RISK_COLORS)
    ].copy()

    reports["reading_date"] = pd.to_datetime(
        reports["reading_date"], errors="coerce"
    )

    reports["submitted_at"] = pd.to_datetime(
        reports["submitted_at"], errors="coerce", utc=True
    )

    reports["record_date"] = (
        reports["reading_date"]
        .dt.strftime("%d %b %Y")
        .fillna(reports["submitted_at"].dt.strftime("%d %b %Y"))
    )

    reports["station"] = (
        reports["station_name"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    reports.loc[
        reports["station"] == "", "station"
    ] = "Submitted report"

    reports["station"] = (
        reports["station"]
        + " (Report #"
        + reports["id"].astype(str)
        + ")"
    )

    reports["source"] = "Submitted report"
    reports["report_id"] = reports["id"]

    reports = reports.rename(
        columns={
            "latitude": "lat",
            "longitude": "lon",
            "risk_level": "target_risk",
        }
    )

    return reports[
        [
            "station",
            "state",
            "lat",
            "lon",
            "target_risk",
            "record_date",
            "source",
            "report_id",
        ]
    ]


def render_map_page(csv_path: str | Path = "data/model_ready_dataset.csv"):
    st.title("Geographic Monitoring Map")

    if px is None:
        st.error("Plotly is unavailable. Install the plotly package to view the map.")
        return

    st.caption(
        "Explore historical monitoring stations and newly submitted "
        "model-generated risk assessments. These are decision-support "
        "estimates, not confirmed contamination events."
    )

    csv_path = str(csv_path)

    if not Path(csv_path).exists():
        st.error(f"Dataset not found: {csv_path}")
        return

    try:
        historical = load_station_data(csv_path)
        submitted = load_submitted_reports()

    except Exception as exc:
        st.error(f"Could not load map data: {exc}")
        return

    historical_count = len(historical)
    submitted_count = len(submitted)

    # Combine both sources without changing the historical CSV.
    locations = pd.concat(
        [historical, submitted],
        ignore_index=True
    )

    if locations.empty:
        st.warning("No valid monitoring locations were found.")
        return

    states = sorted(
        locations["state"].dropna().unique().tolist()
    )

    selected_states = st.multiselect(
        "Filter by state",
        options=states,
        default=states,
        key="monitor_map_states",
    )

    selected_risks = st.multiselect(
        "Filter by risk category",
        options=["Low", "Moderate", "High"],
        default=["Low", "Moderate", "High"],
        key="monitor_map_risks",
    )

    selected_sources = st.multiselect(
        "Filter by data source",
        options=["Historical dataset", "Submitted report"],
        default=["Historical dataset", "Submitted report"],
        key="monitor_map_sources",
    )

    filtered = locations[
        locations["state"].isin(selected_states)
        & locations["target_risk"].isin(selected_risks)
        & locations["source"].isin(selected_sources)
    ].copy()

    low_count = int((filtered["target_risk"] == "Low").sum())
    moderate_count = int((filtered["target_risk"] == "Moderate").sum())
    high_count = int((filtered["target_risk"] == "High").sum())

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Locations shown", f"{len(filtered):,}")
    c2.metric("Low", f"{low_count:,}")
    c3.metric("Moderate", f"{moderate_count:,}")
    c4.metric("High", f"{high_count:,}")

    st.caption(
        f"Historical locations: {historical_count:,} | "
        f"Submitted reports: {submitted_count:,}"
    )

    if filtered.empty:
        st.warning("No locations match the selected filters.")
        return

    hover_fields = {
        "state": True,
        "record_date": True,
        "target_risk": True,
        "source": True,
        "report_id": True,
        "lat": False,
        "lon": False,
    }

    if "district" in filtered.columns:
        hover_fields["district"] = True

    fig = px.scatter_geo(
        filtered,
        lat="lat",
        lon="lon",
        color="target_risk",
        symbol="source",
        symbol_map={
            "Historical dataset": "circle",
            "Submitted report": "diamond",
        },
        color_discrete_map=RISK_COLORS,
        hover_name="station",
        hover_data=hover_fields,
        scope="asia",
        projection="natural earth",
        height=620,
        category_orders={
            "target_risk": ["Low", "Moderate", "High"],
            "source": ["Historical dataset", "Submitted report"],
        },
    )

    fig.update_geos(
        showcountries=True,
        showcoastlines=True,
        showland=True,
        landcolor="#EAF0F2",
        countrycolor="#AAB7BC",
        coastlinecolor="#87979D",
        lataxis_range=[5, 38],
        lonaxis_range=[65, 100],
        showocean=True,
        oceancolor="#F5FAFC",
        bgcolor="rgba(0,0,0,0)",
    )

    fig.update_traces(
        marker={"size": 10, "opacity": 0.85}
    )

    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 10, "b": 0},
        legend_title_text="Risk / data source",
        geo={"bgcolor": "rgba(0,0,0,0)"},
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Location details")

    display_columns = [
        col
        for col in [
            "station",
            "state",
            "district",
            "record_date",
            "target_risk",
            "source",
            "report_id",
            "lat",
            "lon",
        ]
        if col in filtered.columns
    ]

    table = filtered[display_columns].sort_values(
        ["target_risk", "source", "state", "station"]
    )

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "Historical markers represent the latest dated dataset record "
        "for each station. Diamond markers represent individual submitted "
        "reports and their model-generated predictions. Multiple reports "
        "from the same area may appear separately."
    )
