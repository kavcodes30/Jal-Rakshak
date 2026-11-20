from datetime import date, datetime
from pathlib import Path
import streamlit as st
from map_page import render_map_page
from alerts_page import render_alerts_page
from reports_store import save_report
from analytics_page import render_analytics_page
from health_analytics_page import render_health_analytics_page
from early_warning_page import render_early_warning_page
from health_page import render_health_page

from swq_risk.inference import RiskPredictor
from swq_risk.config import STATES, WATER_BODY_TYPES

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "models"

st.set_page_config(
    page_title="JAL-RAKSHAK | Water Risk Monitoring",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>

/* Sidebar background and width */
[data-testid="stSidebar"] {
    min-width: 290px;
    max-width: 290px;
    background: linear-gradient(180deg, #F4F9FF 0%, #FFFFFF 100%);
    border-right: 1px solid #DCE8F5;
}

/* Sidebar padding */
[data-testid="stSidebar"] > div:first-child {
    padding: 2rem 1rem 1rem 1rem;
}

/* Sidebar headings */
[data-testid="stSidebar"] h1 {
    color: #123B63;
    font-size: 25px;
    font-weight: 800;
}

/* Sidebar caption */
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: #71849A;
}

/* Navigation labels */
[data-testid="stSidebar"] div[role="radiogroup"] label {
    background: transparent;
    padding: 9px 12px;
    border-radius: 10px;
    margin-bottom: 5px;
    transition: all 0.2s ease;
}

/* Hover effect */
[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    background: #E5F1FF;
}

/* Selected navigation item */
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
    background: #DCEEFF;
    border: 1px solid #B8D8FA;
    color: #12569A;
    font-weight: 700;
}

/* Navigation text */
[data-testid="stSidebar"] div[role="radiogroup"] label p {
    font-size: 14px;
}

/* Sidebar divider */
[data-testid="stSidebar"] hr {
    border-color: #DCE8F5;
    margin-top: 25px;
    margin-bottom: 25px;
}

</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_predictor():
    return RiskPredictor(model_dir=str(MODEL_DIR))

def risk_color(level):
    return {"Low": "#16865B", "Moderate": "#C58A19", "High": "#C33D45"}.get(level, "#64748b")

def probability_chart(probabilities):
    labels = ["Low", "Moderate", "High"]
    return [
        (label, probabilities.get(label, 0) * 100, risk_color(label))
        for label in labels
    ]

st.markdown("""
<style>
.block-container {padding-top: 1.6rem; padding-bottom: 2rem; max-width: 1500px;}
.hero {background: linear-gradient(115deg,#102f46,#155b70); padding: 1.35rem 1.6rem;
       border-radius: 15px; color: white; margin-bottom: 1rem;}
.hero h1 {color:white; margin:0; font-size:2rem;}
.hero p {color:#d5e9ef; margin:.35rem 0 0 0;}
.metric-card {background:var(--secondary-background); border:1px solid var(--border-color);
              padding:1rem 1.1rem; border-radius:12px; min-height:100px;}
.muted {color:var(--text-color); opacity:.68; font-size:.88rem;}
.result {border-left:6px solid var(--risk); background:var(--secondary-background);
         border-radius:10px; padding:1rem 1.2rem; margin:.5rem 0 1rem 0;}
.small-note {font-size:.82rem; opacity:.75;}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("##  JAL-RAKSHAK")
    st.caption("Community Water Quality Risk Monitoring")
    page = st.radio("NAVIGATION", ["Overview", "Risk prediction","Monitoring map","Risk alerts","Historical analytics",
                                    "Community Health Reporting","Community Health Dashboard","Combined Early Warning Dashboard","About the model"], label_visibility="visible")
    st.divider()
    st.caption("Prototype • Decision-support only")

st.markdown("""
<div class="hero">
  <h1>JAL-RAKSHAK</h1>
  <p>Smart community water-quality monitoring and early risk warning platform</p>
</div>
""", unsafe_allow_html=True)

try:
    predictor = load_predictor()
    model_ready = True
except Exception as exc:
    model_ready = False
    predictor = None
    st.error("The model could not be loaded. Check the folder structure and installed package versions.")
    st.exception(exc)

if page == "Overview":
    st.subheader("Monitoring overview")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="metric-card"><div class="muted">Prediction engine</div><h3>Ready</h3><div class="muted">Existing trained models</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="metric-card"><div class="muted">Risk categories</div><h3>3 levels</h3><div class="muted">Low • Moderate • High</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="metric-card"><div class="muted">Model variants</div><h3>2 variants</h3><div class="muted">Cold-start and historical</div></div>', unsafe_allow_html=True)
    st.write("")
    st.info("This first version runs individual site assessments. Community-wide counts and maps will be added after we connect a verified monitoring-station dataset.")
    st.markdown("### What this prototype can do")
    a, b = st.columns(2)
    with a:
        st.markdown("**Water-quality risk assessment**")
        st.write("Enter site details and available readings to run the existing prediction pipeline.")
        st.markdown("**Model-estimated class scores**")
        st.write("View Low, Moderate and High scores returned by the trained classifier.")
    with b:
        st.markdown("**Early-warning flag**")
        st.write("Display the alert decision and warnings returned by the inference module.")
        st.markdown("**Audit-friendly output**")
        st.write("Show which inference path was used and the model's limitations.")
    if not model_ready:
        st.warning("Model status: not loaded. Resolve the error above before using predictions.")

elif page == "Risk prediction":
    st.subheader("Site risk assessment")
    st.caption("Enter a monitoring-site reading.")

    st.markdown("### Optional water-quality measurements")

    optional_col1, optional_col2 = st.columns(2)

    with optional_col1:
        tds_enabled = st.checkbox(
            "I have TDS (optional)", value=False
        )

    with optional_col2:
        turb_enabled = st.checkbox(
            "I have turbidity (optional)", value=False
        )

    with st.form("prediction_form"):
        left, right = st.columns(2)
        with left:
            station = st.text_input("Monitoring station name", value="Demo River Station")
            state = st.selectbox("State / Union Territory", STATES)
            water_body = st.selectbox("Water-body type", WATER_BODY_TYPES)
            reading_date = st.date_input("Reading date", value=date.today())
            ph = st.number_input("pH", min_value=0.0, max_value=14.0, value=7.2, step=0.1)
            ec_enabled = st.checkbox("I have electrical conductivity (EC)", value=True)
            ec = st.number_input("Electrical conductivity (µS/cm)", min_value=1.0, max_value=60000.0, value=640.0, step=10.0, disabled=not ec_enabled)
            lat = st.number_input("Latitude", min_value=-90.0, max_value=90.0, value=18.5204, format="%.6f")
        with right:
            
            tds = st.number_input("TDS (mg/L)", min_value=1.0, max_value=100000.0, value=450.0, disabled=not tds_enabled)
            
            turbidity = st.number_input("Turbidity (NTU)", min_value=0.0, max_value=1000.0, value=2.0, disabled=not turb_enabled)
            colour = st.selectbox("Water colour", ["clear", "yellowish", "brown", "green", "other"])
            odour = st.selectbox("Water odour", ["none", "unusual", "foul", "chemical"])
            lon = st.number_input("Longitude", min_value=-180.0, max_value=180.0, value=73.8567, format="%.6f")

        st.markdown("#### Optional laboratory measurements")
        lab_enabled = st.checkbox("I have laboratory dissolved oxygen (DO) / ammonia-N results", value=False)
        lab1, lab2 = st.columns(2)
        with lab1:
            do_value = st.number_input("Dissolved oxygen (mg/L)", min_value=0.0, max_value=20.0, value=6.0, step=0.1, disabled=not lab_enabled)
        with lab2:
            nh3n_value = st.number_input("Ammonia-N (mg/L)", min_value=0.0, max_value=100.0, value=0.2, step=0.1, disabled=not lab_enabled)

        submitted = st.form_submit_button("Run water-quality risk assessment", type="primary", use_container_width=True)

    if submitted:
        if not model_ready:
            st.error("Model is not loaded. Fix the loading error before predicting.")
        else:
            reading = {
                "timestamp": datetime.combine(reading_date, datetime.min.time()).isoformat(),
                "station_name": station,
                "state": state,
                "water_body": water_body,
                "ph": ph,
                "ec": ec if ec_enabled else None,
                "tds": tds if tds_enabled else None,
                "turbidity": turbidity if turb_enabled else None,
                "colour": colour,
                "odour": odour,
                "lat": lat,
                "lon": lon,
            }
            if lab_enabled:
                reading["do"] = do_value
                reading["nh3n"] = nh3n_value
            try:
                result = predictor.predict(reading)
                report_id = save_report(reading, result)
                st.success(f"Report #{report_id} submitted and saved successfully!")
                level = result["risk_level"]
                color = risk_color(level)
                st.markdown(
                    f'<div class="result" style="--risk:{color}"><div class="muted">PREDICTED WATER-QUALITY RISK</div>'
                    f'<h2 style="margin:.2rem 0;color:{color}">{level}</h2>'
                    f'<div class="small-note">Station: {station} · Method: {result["mode"]}</div></div>',
                    unsafe_allow_html=True,
                )
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.markdown("**Model-estimated class scores**")
                    for label, value, color in probability_chart(result["probabilities"]):
                        st.progress(
                            min(max(value / 100, 0.0), 1.0),
                            text=f"{label}: {value:.1f}%",
                        )
                with col2:
                    st.markdown("**Early-warning status**")
                    if result["alert"]:
                        st.error(result["alert_message"] or "High-risk alert raised.")
                    else:
                        st.success("No high-risk alert was raised by the configured threshold.")
                    st.markdown("**Recommended next step**")
                    if level == "High" or result["alert"]:
                        st.write("Prioritize confirmatory laboratory testing and investigate possible contamination.")
                    elif level == "Moderate":
                        st.write("Increase monitoring frequency and review nearby contamination sources.")
                    else:
                        st.write("Continue routine monitoring and retain the reading for trend analysis.")
                if result["warnings"]:
                    st.markdown("**Model input warnings**")
                    for warning in result["warnings"]:
                        st.warning(warning)
                with st.expander("Technical prediction details"):
                    st.json(result)
                st.caption(result["disclaimer"])
            except Exception as exc:
                st.error(f"Prediction failed: {exc}")

elif page == "Monitoring map":
    render_map_page("data/model_ready_dataset.csv")     

elif page == "Risk alerts":
    render_alerts_page(
        ROOT / "data" / "model_ready_dataset.csv"
    )          

elif page == "Historical analytics":
    render_analytics_page(
        ROOT / "data" / "model_ready_dataset.csv"
    )  

elif page == "Community Health Reporting":
    render_health_page()     
elif page == "Community Health Dashboard":
    render_health_analytics_page()      
elif page == "Combined Early Warning Dashboard":
    render_early_warning_page()        

elif page == "About the model":
    st.subheader("Model information and responsible use")
    st.markdown("""
    **What the current model estimates**

    The supplied model classifies water-pollution risk into Low, Moderate and High categories. Its labels are derived from dissolved oxygen (DO) and ammonia-N criteria, not from confirmed human disease cases.

    **Inference paths**
    - `ml_cold`: uses the cold-start model when no earlier site readings are supplied.
    - `ml_full`: uses the historical model when earlier readings are supplied.
    - `rule_based_measured_DO`: applies the configured water-quality rule when laboratory DO / ammonia-N values are supplied.

    **Important input behaviour**
    - TDS and turbidity are accepted by the inference interface but the current model explicitly warns that they are not used.
    - Missing location information can reduce reliability.
    - States outside the training scope trigger a warning.
    """)
    st.warning("This is a decision-support estimate. It is not a medical diagnosis, does not detect pathogens, and does not confirm a waterborne-disease outbreak.")
    if model_ready:
        with st.expander("Loaded model metadata"):
            st.json(predictor.meta)
