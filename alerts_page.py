
from pathlib import Path

import pandas as pd
import streamlit as st

from map_page import load_station_data
from reports_store import get_submitted_reports


RISK_PRIORITY = {
    "High": 0,
    "Moderate": 1,
    "Low": 2,
}


def recommended_action(level):
    if level == "High":
        return (
            "Priority review: arrange confirmatory laboratory "
            "testing and investigate possible contamination."
        )

    if level == "Moderate":
        return (
            "Increase monitoring frequency and review "
            "nearby contamination sources."
        )

    return (
        "Continue routine monitoring and retain "
        "the reading for trend analysis."
    )


def render_alerts_page(csv_path="data/model_ready_dataset.csv"):

    st.title("Risk Alerts & Early Warning")

    st.caption(
        "View historical monitoring-station risk labels and "
        "newly submitted model-generated risk assessments."
    )

    # =====================================================
    # SECTION 1: HISTORICAL DATASET ALERTS
    # =====================================================

    st.header("Historical Monitoring Alerts")

    csv_path = Path(csv_path)

    if csv_path.exists():

        try:
            stations = load_station_data(str(csv_path))

        except Exception as exc:
            stations = pd.DataFrame()
            st.error(f"Could not load historical dataset: {exc}")

        if not stations.empty:

            alerts = stations.copy()

            alerts["Priority"] = alerts["target_risk"].map(
                RISK_PRIORITY
            )

            alerts["Recommended Action"] = (
                alerts["target_risk"].apply(recommended_action)
            )

            alerts = alerts.sort_values(
                by=["Priority", "t"],
                ascending=[True, False],
            )

            st.subheader("Filter Historical Alerts")

            col1, col2 = st.columns(2)

            states = sorted(
                alerts["state"].dropna().unique().tolist()
            )

            with col1:
                selected_states = st.multiselect(
                    "Select State",
                    states,
                    default=states,
                    key="alert_states",
                )

            with col2:
                selected_risks = st.multiselect(
                    "Select Risk Category",
                    ["High", "Moderate", "Low"],
                    default=["High", "Moderate"],
                    key="alert_risks",
                )

            filtered = alerts[
                alerts["state"].isin(selected_states)
                & alerts["target_risk"].isin(selected_risks)
            ].copy()

            high_count = int(
                (filtered["target_risk"] == "High").sum()
            )
            moderate_count = int(
                (filtered["target_risk"] == "Moderate").sum()
            )
            low_count = int(
                (filtered["target_risk"] == "Low").sum()
            )

            st.subheader("Historical Alert Summary")

            c1, c2, c3, c4 = st.columns(4)

            c1.metric("Stations Shown", len(filtered))
            c2.metric("High Risk", high_count)
            c3.metric("Moderate Risk", moderate_count)
            c4.metric("Low Risk", low_count)

            if high_count > 0:
                st.error(
                    f"{high_count} high-risk historical station(s) "
                    "require priority review."
                )

            if moderate_count > 0:
                st.warning(
                    f"{moderate_count} moderate-risk historical "
                    "station(s) should receive increased monitoring."
                )

            if filtered.empty:
                st.info("No historical stations match the selected filters.")

            else:
                st.subheader("Historical Station Alert Register")

                display_columns = [
                    col
                    for col in [
                        "station",
                        "state",
                        "district",
                        "record_date",
                        "target_risk",
                        "Recommended Action",
                    ]
                    if col in filtered.columns
                ]

                display = filtered[display_columns].rename(
                    columns={
                        "station": "Station",
                        "state": "State",
                        "district": "District",
                        "record_date": "Observation Date",
                        "target_risk": "Risk Category",
                    }
                )

                st.dataframe(
                    display,
                    use_container_width=True,
                    hide_index=True,
                )

                export_columns = [
                    col
                    for col in [
                        "station",
                        "state",
                        "district",
                        "record_date",
                        "target_risk",
                        "lat",
                        "lon",
                        "Recommended Action",
                    ]
                    if col in filtered.columns
                ]

                historical_report = filtered[
                    export_columns
                ].rename(
                    columns={
                        "record_date": "observation_date",
                        "target_risk": "risk_category",
                    }
                )

                st.download_button(
                    "Download Historical Alerts (CSV)",
                    data=historical_report.to_csv(
                        index=False
                    ).encode("utf-8"),
                    file_name="jal_rakshak_historical_alerts.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

        else:
            st.info("No valid historical station records were found.")

    else:
        st.warning(f"Historical dataset not found: {csv_path}")

    # =====================================================
    # SECTION 2: NEWLY SUBMITTED REPORT ALERTS
    # =====================================================

    st.divider()

    st.header("Newly Submitted Report Alerts")

    st.caption(
        "These alerts are generated from reports submitted through "
        "the Risk Prediction page and stored in the local database."
    )

    try:
        reports = pd.DataFrame(get_submitted_reports())

    except Exception as exc:
        st.error(f"Could not load submitted reports: {exc}")
        return

    if reports.empty:
        st.info(
            "No reports have been submitted yet. "
            "Submit a report from the Risk Prediction page "
            "to see its alert here."
        )
        return

    # Convert database fields into display-friendly values.
    reports["risk_level"] = (
        reports["risk_level"].astype(str).str.title()
    )

    reports["high_risk_alert"] = (
        pd.to_numeric(
            reports["high_risk_alert"], errors="coerce"
        )
        .fillna(0)
        .astype(bool)
    )

    reports["submitted_at"] = pd.to_datetime(
        reports["submitted_at"],
        errors="coerce",
        utc=True,
    )

    reports["Priority"] = reports["risk_level"].map(
        RISK_PRIORITY
    )

    reports["Model Alert"] = reports[
        "high_risk_alert"
    ].map({
        True: "Raised",
        False: "Not raised",
    })

    reports["Requires Review"] = (
        (reports["risk_level"] == "High")
        | reports["high_risk_alert"]
    )

    reports["Recommended Action"] = (
        reports["risk_level"].apply(recommended_action)
    )

    reports.loc[
        reports["high_risk_alert"]
        & (reports["risk_level"] != "High"),
        "Recommended Action",
    ] = (
        "Model high-risk alert threshold raised despite a "
        "different predicted class. Prioritize confirmatory "
        "laboratory testing."
    )

    reports = reports.sort_values(
        by=["Priority", "submitted_at"],
        ascending=[True, False],
        na_position="last",
    )

    # Filters for newly submitted reports.
    st.subheader("Filter Submitted Reports")

    f1, f2 = st.columns(2)

    report_states = sorted(
        reports["state"].dropna().unique().tolist()
    )

    with f1:
        selected_report_states = st.multiselect(
            "Select Report State",
            report_states,
            default=report_states,
            key="submitted_alert_states",
        )

    with f2:
        selected_report_risks = st.multiselect(
            "Select Predicted Risk",
            ["High", "Moderate", "Low"],
            default=["High", "Moderate", "Low"],
            key="submitted_alert_risks",
        )

    submitted_filtered = reports[
        reports["state"].isin(selected_report_states)
        & reports["risk_level"].isin(selected_report_risks)
    ].copy()

    # Submitted-report metrics.
    submitted_high = int(
        (submitted_filtered["risk_level"] == "High").sum()
    )

    submitted_moderate = int(
        (submitted_filtered["risk_level"] == "Moderate").sum()
    )

    submitted_low = int(
        (submitted_filtered["risk_level"] == "Low").sum()
    )

    review_count = int(
        submitted_filtered["Requires Review"].sum()
    )

    st.subheader("Submitted Report Summary")

    a, b, c, d = st.columns(4)

    a.metric("Reports Shown", len(submitted_filtered))
    b.metric("High Risk", submitted_high)
    c.metric("Moderate Risk", submitted_moderate)
    d.metric("Require Review", review_count)

    if review_count > 0:
        st.error(
            f"{review_count} submitted report(s) require priority review."
        )

    if submitted_moderate > 0:
        st.warning(
            f"{submitted_moderate} submitted report(s) "
            "have Moderate predicted risk."
        )

    if submitted_filtered.empty:
        st.info("No submitted reports match the selected filters.")
        return

    # Submitted-report table.
    st.subheader("Submitted Report Register")

    submitted_display = submitted_filtered[
        [
            "id",
            "station_name",
            "state",
            "reading_date",
            "risk_level",
            "Model Alert",
            "prediction_mode",
            "Recommended Action",
        ]
    ].rename(
        columns={
            "id": "Report ID",
            "station_name": "Location",
            "state": "State",
            "reading_date": "Reading Date",
            "risk_level": "Predicted Risk",
            "prediction_mode": "Prediction Method",
        }
    )

    st.dataframe(
        submitted_display,
        use_container_width=True,
        hide_index=True,
    )

    # Individual report details.
    st.subheader("Report Details")

    report_ids = submitted_filtered["id"].tolist()

    selected_report_id = st.selectbox(
        "Select a report to inspect",
        report_ids,
        format_func=lambda x: f"Report #{x}",
        key="selected_submitted_report",
    )

    selected_report = submitted_filtered[
        submitted_filtered["id"] == selected_report_id
    ].iloc[0]

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Location:**", selected_report["station_name"])
        st.write("**State:**", selected_report["state"])
        st.write("**Predicted risk:**", selected_report["risk_level"])
        st.write("**Prediction method:**", selected_report["prediction_mode"])

    with col2:
        st.write("**Latitude:**", selected_report["latitude"])
        st.write("**Longitude:**", selected_report["longitude"])
        st.write("**Model alert:**", selected_report["Model Alert"])
        st.write("**Report ID:**", selected_report["id"])

    with st.expander("View complete submitted report and model output"):
        import json

        st.markdown("**Original submitted readings**")
        st.json(json.loads(selected_report["reading_data"]))

        st.markdown("**Model prediction output**")
        st.json(json.loads(selected_report["prediction_data"]))

    # Export submitted alerts.
    st.subheader("Export Submitted Report Alerts")

    export = submitted_filtered[
        [
            "id",
            "station_name",
            "state",
            "reading_date",
            "latitude",
            "longitude",
            "risk_level",
            "high_risk_alert",
            "prediction_mode",
            "Recommended Action",
        ]
    ].rename(
        columns={
            "id": "report_id",
            "station_name": "location",
            "reading_date": "reading_date",
            "latitude": "latitude",
            "longitude": "longitude",
            "risk_level": "predicted_risk",
            "high_risk_alert": "model_alert_raised",
            "prediction_mode": "prediction_method",
        }
    )

    st.download_button(
        "Download Submitted Report Alerts (CSV)",
        data=export.to_csv(index=False).encode("utf-8"),
        file_name="jal_rakshak_submitted_report_alerts.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.caption(
        "Submitted report alerts are model-generated decision-support "
        "estimates. They do not confirm contamination, pathogen presence "
        "or a disease outbreak. Confirmatory laboratory testing is required."
    )

