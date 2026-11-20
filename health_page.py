
import streamlit as st
from datetime import date

from health_reports_store import save_health_report


def render_health_page():

    st.title("Community Health Reporting")

    st.write(
        "Submit community-level health observations "
        "to support public-health monitoring."
    )

    st.info(
        "Submit aggregated symptom information only. "
        "Do not enter patient names, phone numbers or other "
        "personal identifying information. This form does "
        "not diagnose diseases."
    )

    with st.form("community_health_form"):

        st.subheader("Location Information")

        col1, col2 = st.columns(2)

        with col1:
            state = st.text_input(
                "State *",
                placeholder="Enter state"
            )

            district = st.text_input(
                "District *",
                placeholder="Enter district"
            )

        with col2:
            village = st.text_input(
                "Village / Community",
                placeholder="Enter village or area"
            )

            report_date = st.date_input(
                "Date of observation",
                value=date.today()
            )

        st.divider()

        st.subheader("Community Health Information")

        people_affected = st.number_input(
            "Number of people reporting symptoms *",
            min_value=1,
            max_value=100000,
            value=1,
            step=1
        )

        st.write("**Select reported symptoms:**")

        symptom_options = [
            "Diarrhoea",
            "Vomiting",
            "Fever",
            "Abdominal pain",
            "Dehydration",
            "Jaundice",
            "Bloody stool",
            "Skin rash",
            "Other"
        ]

        symptoms = st.multiselect(
            "Symptoms reported",
            options=symptom_options,
            placeholder="Choose one or more symptoms"
        )

        st.divider()

        st.subheader("Water Source Information")

        water_source = st.selectbox(
            "Main water source",
            [
                "Unknown",
                "River",
                "Well",
                "Borewell",
                "Pond",
                "Tap water",
                "Hand pump",
                "Other"
            ]
        )

        additional_notes = st.text_area(
            "Additional observations (optional)",
            placeholder=(
                "Enter general community-level observations. "
                "Do not include personal information."
            )
        )

        submitted = st.form_submit_button(
            "Submit Health Report",
            use_container_width=True
        )

        if submitted:

            if not state.strip() or not district.strip():
                st.error(
                    "Please enter both State and District."
                )

            elif not symptoms:
                st.error(
                    "Please select at least one reported symptom."
                )

            else:

                report = {
                    "report_date": report_date,
                    "state": state.strip(),
                    "district": district.strip(),
                    "village": village.strip(),
                    "people_affected": int(people_affected),
                    "symptoms": symptoms,
                    "water_source": water_source,
                    "additional_notes": additional_notes.strip()
                }

                try:
                    report_id = save_health_report(report)

                    st.success(
                        f"Health report #{report_id} "
                        "submitted successfully!"
                    )

                    st.info(
                        "The report has been saved for "
                        "community-level monitoring."
                    )

                except Exception as error:
                    st.error(
                        f"Could not save the report: {error}"
                    )
