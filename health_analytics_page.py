
import streamlit as st
import pandas as pd
from importlib import import_module

try:
    px = import_module("plotly.express")
except ImportError:
    px = None

from health_reports_store import get_health_reports


def render_health_analytics_page():

    st.title("Community Health Dashboard")

    reports = get_health_reports()

    if not reports:
        st.info(
            "No community health reports available yet. "
            "Submit a report to view analytics."
        )
        return

    df = pd.DataFrame(reports)

    df["report_date"] = pd.to_datetime(
        df["report_date"], errors="coerce"
    )

    df["people_affected"] = pd.to_numeric(
        df["people_affected"], errors="coerce"
    ).fillna(0)

    # Filters
    st.subheader("Filters")

    col1, col2 = st.columns(2)

    with col1:
        states = sorted(df["state"].dropna().unique().tolist())
        selected_states = st.multiselect(
            "Select states",
            states,
            default=states
        )

    with col2:
        districts = sorted(
            df[df["state"].isin(selected_states)]
            ["district"].dropna().unique().tolist()
        )

        selected_districts = st.multiselect(
            "Select districts",
            districts,
            default=districts
        )

    filtered = df[
        df["state"].isin(selected_states)
        & df["district"].isin(selected_districts)
    ].copy()

    if filtered.empty:
        st.warning("No reports match the selected filters.")
        return

    # Summary metrics
    total_reports = len(filtered)
    total_people = int(filtered["people_affected"].sum())
    total_districts = filtered["district"].nunique()

    symptom_list = [
        symptom
        for symptoms in filtered["symptoms"]
        if isinstance(symptoms, list)
        for symptom in symptoms
    ]

    most_common = (
        pd.Series(symptom_list).value_counts().index[0]
        if symptom_list else "None"
    )

    st.subheader("Community Health Overview")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Reports", total_reports)
    c2.metric("People Reported Affected", total_people)
    c3.metric("Districts", total_districts)
    c4.metric("Most Reported Symptom", most_common)

    st.divider()

    # Symptom distribution
    st.subheader("Symptom Distribution")

    if symptom_list and px is not None:
        symptom_df = (
            pd.Series(symptom_list)
            .value_counts()
            .rename_axis("Symptom")
            .reset_index(name="Reports")
        )

        fig_symptoms = px.bar(
            symptom_df,
            x="Symptom",
            y="Reports",
            color="Symptom",
            title="Reported Symptoms"
        )

        st.plotly_chart(
            fig_symptoms,
            use_container_width=True
        )
    else:
        st.info("No symptoms available for analysis.")

    # Reports over time
    st.subheader("Health Reports Over Time")

    date_df = filtered.dropna(subset=["report_date"]).copy()

    if not date_df.empty and px is not None:
        date_df["Month"] = (
            date_df["report_date"].dt.to_period("M").astype(str)
        )

        monthly = (
            date_df.groupby("Month")
            .size()
            .reset_index(name="Reports")
        )

        fig_monthly = px.line(
            monthly,
            x="Month",
            y="Reports",
            markers=True,
            title="Monthly Community Health Reports"
        )

        st.plotly_chart(
            fig_monthly,
            use_container_width=True
        )

    # District-wise reports
    st.subheader("District-wise Reporting")

    district_df = (
        filtered.groupby("district")["people_affected"]
        .sum()
        .reset_index()
        .sort_values("people_affected", ascending=False)
    )

    if px is not None:
        fig_district = px.bar(
            district_df,
            x="district",
            y="people_affected",
            title="People Reported Affected by District",
            labels={
                "district": "District",
                "people_affected": "People Reported Affected"
            }
        )

        st.plotly_chart(
            fig_district,
            use_container_width=True
        )

    # Report register
    st.subheader("Community Health Report Register")

    display_df = filtered.drop(
        columns=["symptoms"],
        errors="ignore"
    ).copy()

    display_df["Symptoms"] = filtered["symptoms"].apply(
        lambda x: ", ".join(x) if isinstance(x, list) else ""
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    # CSV download
    csv = display_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download Health Reports (CSV)",
        data=csv,
        file_name="community_health_reports.csv",
        mime="text/csv"
    )

    st.caption(
        "These are community-submitted symptom reports. "
        "They are not confirmed diagnoses or verified disease outbreaks."
    )
