"""Single source of truth: thresholds, enums, feature lists. Shared by training and serving."""
RISK_LABELS = ["Low", "Moderate", "High"]          # class ids 0,1,2
WATER_BODY_TYPES = ["river", "lake_reservoir", "canal_drain", "coastal", "groundwater", "other"]
STATES = ["Gujarat", "Jammu & Kashmir", "Kerala", "Madhya Pradesh", "Maharashtra", "Punjab", "West Bengal"]

# ---- Label definition (CPCB "designated best use" water-quality criteria) ----
# Class A/B (drinking after disinfection / bathing): DO >= 5-6 mg/L
# Class C/D (drinking after conventional treatment / propagation): DO >= 4 mg/L, NH3-N <= 1.2 mg/L
DO_LOW_MIN = 6.0        # DO >= 6          -> Low
DO_MODERATE_MIN = 4.0   # 4 <= DO < 6      -> Moderate ; DO < 4 -> High
NH3N_HIGH_MAX = 1.2     # NH3-N > 1.2 mg/L -> High (escalation)

# ---- physically plausible ranges; anything outside is a unit/entry error -> NaN ----
VALID_RANGES = {"ph": (0, 14), "do": (0, 20), "turbidity": (0, 1000), "ec": (1, 60000),
                "tds": (1, 100000), "nh3n": (0, 100)}
MONSOON_MONTHS = (6, 7, 8, 9)

NUM_STATIC = ["ph", "ph_dev", "ph_out_of_range", "ec_log", "tds_log", "turb_log", "cond_log", "ec_tds_ratio",
              "has_ec", "has_tds", "has_turb", "colour_abnormal", "odour_flag", "lat", "lon",
              "month_sin", "month_cos", "monsoon"]
NUM_HISTORY = ["n_prev", "days_since_last", "last_risk", "mean_risk", "max_risk", "last3_mean_risk",
               "last_do", "mean_do", "min_do", "last_ph", "mean_ph", "ph_delta_last", "ph_vs_hist"]
CAT = ["water_body", "state"]
