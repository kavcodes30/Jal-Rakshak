
import streamlit as st
import pandas as pd

from reports_store import get_submitted_reports
from health_reports_store import get_health_reports


def render_early_warning_page():

    st.title("Combined Early Warning Dashboard")

    st.write(
        "Monitor water-quality risks alongside community-reported "
        "health symptoms to identify areas requiring investigation."
    )

    st.info(
        "This dashboard identifies co-occurring reports for review. "
        "It does not establish a causal relationship or confirm "
        "a disease outbreak."
    )

    # --------------------------------------------------
    # 1. Load water-quality reports
    # --------------------------------------------------

    water_reports = get_submitted_reports()
    health_reports = get_health_reports()

    if not water_reports and not health_reports:
        st.info(
            "No reports are available yet. Submit water-quality "
            "and community health reports to begin monitoring."
        )
        return

    water_df = pd.DataFrame(water_reports)
    health_df = pd.DataFrame(health_reports)

    # --------------------------------------------------
    # 2. Prepare water-quality data
    # --------------------------------------------------

    if not water_df.empty:

        water_df["state"] = (
            water_df["state"].fillna("").astype(str).str.strip()
        )

        water_df["risk_level"] = (
            water_df["risk_level"].fillna("Unknown")
            .astype(str).str.title()
        )

        water_df["high_risk_alert"] = (
            pd.to_numeric(
                water_df["high_risk_alert"],
                errors="coerce"
            ).fillna(0).astype(int)
        )

        water_df["submitted_at"] = pd.to_datetime(
            water_df["submitted_at"], errors="coerce"
        )

    # --------------------------------------------------
    # 3. Prepare community health data
    # --------------------------------------------------

    if not health_df.empty:

        health_df["state"] = (
            health_df["state"].fillna("").astype(str).str.strip()
        )

        health_df["district"] = (
            health_df["district"].fillna("").astype(str).str.strip()
        )

        health_df["people_affected"] = pd.to_numeric(
            health_df["people_affected"],
            errors="coerce"
        ).fillna(0)

        health_df["report_date"] = pd.to_datetime(
            health_df["report_date"], errors="coerce"
        )

    # --------------------------------------------------
    # 4. Summary metrics
    # --------------------------------------------------

    total_water = len(water_df)
    total_health = len(health_df)

    total_people = (
        int(health_df["people_affected"].sum())
        if not health_df.empty else 0
    )

    high_water_reports = (
        int(
            (
                (water_df["risk_level"] == "High")
                | (water_df["high_risk_alert"] == 1)
            ).sum()
        )
        if not water_df.empty else 0
    )

    st.subheader("Overall Monitoring Summary")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Water Reports", total_water)
    c2.metric("Health Reports", total_health)
    c3.metric("People Reported Affected", total_people)
    c4.metric("Water Reports Requiring Review", high_water_reports)

    st.divider()

    # --------------------------------------------------
    # 5. Water-quality risk distribution
    # --------------------------------------------------

    st.subheader("Water Quality Risk Distribution")

    if not water_df.empty:

        risk_counts = (
            water_df["risk_level"]
            .value_counts()
            .rename_axis("Risk Level")
            .reset_index(name="Reports")
        )

        st.caption("Submitted Water Reports by Risk")
        st.bar_chart(
            risk_counts.set_index("Risk Level")["Reports"]
        )

    else:
        st.info("No submitted water-quality reports available.")

    st.divider()

    # --------------------------------------------------
    # 6. Community symptom distribution
    # --------------------------------------------------

    st.subheader("Community Symptom Distribution")

    if not health_df.empty:

        symptoms = [
            symptom
            for symptom_list in health_df["symptoms"]
            if isinstance(symptom_list, list)
            for symptom in symptom_list
        ]

        if symptoms:

            symptom_counts = (
                pd.Series(symptoms)
                .value_counts()
                .rename_axis("Symptom")
                .reset_index(name="Reports")
            )

            st.caption("Reported Community Symptoms")
            st.bar_chart(
                symptom_counts.set_index("Symptom")["Reports"]
            )

        else:
            st.info("No symptom information available.")

    else:
        st.info("No community health reports available.")

    st.divider()

    # --------------------------------------------------
    # 7. State-level combined monitoring
    # --------------------------------------------------

    st.subheader("Combined State-wise Monitoring")

    if not water_df.empty and not health_df.empty:

        water_state = (
            water_df[water_df["state"] != ""]
            .groupby("state")
            .agg(
                water_reports=("state", "size"),
                high_or_alert_reports=(
                    "high_risk_alert",
                    "sum"
                )
            )
            .reset_index()
        )

        high_class_counts = (
            water_df[
                (water_df["state"] != "")
                & (water_df["risk_level"] == "High")
            ]
            .groupby("state")
            .size()
            .to_dict()
        )

        water_state["high_or_alert_reports"] += (
            water_state["state"]
            .map(high_class_counts)
            .fillna(0)
            .astype(int)
        )

        # A report meeting both High classification and
        # alert threshold is counted only once.
        water_state["high_or_alert_reports"] = (
            water_df.assign(
                review_required=(
                    (water_df["risk_level"] == "High")
                    | (water_df["high_risk_alert"] == 1)
                )
            )
            .groupby("state")["review_required"]
            .sum()
            .reindex(water_state["state"])
            .fillna(0)
            .astype(int)
            .values
        )

        health_state = (
            health_df[health_df["state"] != ""]
            .groupby("state")
            .agg(
                health_reports=("state", "size"),
                people_affected=("people_affected", "sum")
            )
            .reset_index()
        )

        combined = pd.merge(
            water_state,
            health_state,
            on="state",
            how="outer"
        ).fillna(0)

        for col in [
            "water_reports",
            "high_or_alert_reports",
            "health_reports",
            "people_affected"
        ]:
            combined[col] = combined[col].astype(int)

        def assign_status(row):

            if (
                row["high_or_alert_reports"] > 0
                and row["health_reports"] > 0
            ):
                return "Priority for review"

            if (
                row["high_or_alert_reports"] > 0
                or row["health_reports"] > 0
            ):
                return "Requires monitoring"

            return "No combined reports"

        combined["Monitoring Status"] = combined.apply(
            assign_status,
            axis=1
        )

        combined = combined.sort_values(
            ["high_or_alert_reports", "health_reports"],
            ascending=False
        )

        st.dataframe(
            combined.rename(
                columns={
                    "state": "State",
                    "water_reports": "Water Reports",
                    "high_or_alert_reports": "High / Alert Water Reports",
                    "health_reports": "Health Reports",
                    "people_affected": "People Reported Affected"
                }
            ),
            use_container_width=True,
            hide_index=True
        )

        priority = combined[
            combined["Monitoring Status"] == "Priority for review"
        ]

        st.subheader("Areas Prioritised for Investigation")

        if not priority.empty:

            for _, row in priority.iterrows():

                st.warning(
                    f"**{row['state']}** — "
                    f"{row['high_or_alert_reports']} high/alert "
                    f"water report(s) and "
                    f"{row['health_reports']} community health "
                    f"report(s). Further investigation is recommended."
                )

        else:
            st.success(
                "No state currently meets the combined review "
                "condition based on submitted reports."
            )

        csv = combined.to_csv(index=False).encode("utf-8")

        st.download_button(
            "Download Combined Monitoring Report",
            data=csv,
            file_name="jal_rakshak_combined_monitoring.csv",
            mime="text/csv"
        )

    else:

        st.info(
            "Combined state-level comparison requires at least "
            "one water-quality report and one community health "
            "report. Submit both types to enable this section."
        )

    st.caption(
        "State-level comparison only. Reports may concern "
        "different districts or dates. Co-occurrence does not "
        "demonstrate causation or confirm an outbreak."
    )
