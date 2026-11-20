"""Framework-agnostic inference. Import this from Flask / FastAPI / Streamlit, or call via CLI (see cli.py)."""
import json, os, warnings
import numpy as np, pandas as pd, joblib
from .config import RISK_LABELS, STATES, WATER_BODY_TYPES, VALID_RANGES
from .features import build_row, to_frame, _clean
from .labels import risk_class

DISCLAIMER = ("Decision-support estimate of water-pollution-based waterborne-disease RISK for a monitoring site. "
              "It is not a medical diagnosis and does not confirm an outbreak or the presence of pathogens.")

class RiskPredictor:
    def __init__(self, model_dir=None):
        model_dir = model_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
        self.meta = json.load(open(os.path.join(model_dir, "model_metadata.json")))
        self.models = {v: joblib.load(os.path.join(model_dir, f"risk_model_{v}.joblib")) for v in ("full", "cold")}
        self.features = {v: self.meta["variants"][v]["features"] for v in self.models}
        self.alert_thr = {v: self.meta["variants"][v]["alert_threshold_high"] for v in self.models}
        self.version = self.meta["versions"]; self.model_version = "1.0.0"

    # ------------------------------------------------------------------ public API
    def predict(self, reading: dict, history: list = None) -> dict:
        """reading: {timestamp, ph, [ec, tds, turbidity, colour, odour], lat, lon, state, [station_name|water_body],
                     [do, nh3n  -> if lab/sensor DO is supplied the standards rule is applied directly]}
           history: optional list of EARLIER readings of the same site: [{timestamp, ph?, do?, nh3n?}, ...]"""
        warns = self._validate(reading, history)
        do, nh3 = _clean(reading.get("do"), "do"), _clean(reading.get("nh3n"), "nh3n")
        r = risk_class(do, nh3)
        if np.isnan(r) and not np.isnan(nh3) and nh3 > 1.2: r = 2.0          # ammonia alone can prove High
        if not np.isnan(r):
            probs = [0.0, 0.0, 0.0]; probs[int(r)] = 1.0
            return self._out(int(r), probs, int(r) == 2, "rule_based_measured_DO", warns)
        variant = "full" if history and len(history) > 0 else "cold"
        X = to_frame([build_row(reading, history)])[self.features[variant]]
        p = self.models[variant].predict_proba(X)[0]
        probs = [0.0, 0.0, 0.0]
        for c, v in zip(self.models[variant].classes_, p): probs[int(c)] = float(v)
        cls = int(np.argmax(probs)); alert = probs[2] >= self.alert_thr[variant]
        if alert and cls != 2: warns.append(f"High-risk alert raised because P(High)={probs[2]:.2f} >= tuned threshold {self.alert_thr[variant]:.3f}.")
        return self._out(cls, probs, alert, f"ml_{variant}", warns)

    def predict_batch(self, items: list) -> list:
        """items: [{'reading': {...}, 'history': [...]}, ...]"""
        return [self.predict(i["reading"], i.get("history")) for i in items]

    # ------------------------------------------------------------------ internals
    def _out(self, cls, probs, alert, mode, warns):
        return {"risk_level": RISK_LABELS[cls], "risk_class": cls,
                "probabilities": {k: round(float(v), 4) for k, v in zip(RISK_LABELS, probs)},
                "alert": bool(alert), "alert_message": ("Potentially high-risk conditions - investigate / confirm with laboratory testing." if alert else None),
                "mode": mode, "warnings": warns, "model_version": self.model_version, "disclaimer": DISCLAIMER}

    def _validate(self, r, history):
        w = []
        if not r.get("timestamp"): raise ValueError("'timestamp' (ISO-8601) is required")
        try: pd.to_datetime(r["timestamp"])
        except Exception: raise ValueError("'timestamp' is not a valid date-time")
        if r.get("state") not in STATES: w.append(f"state not in training scope {STATES}; prediction is less reliable.")
        if r.get("lat") is None or r.get("lon") is None: w.append("lat/lon missing; location features are imputed.")
        if all(r.get(k) in (None, "") for k in ("ph", "ec", "tds", "turbidity", "do", "nh3n")): w.append("No measurements supplied; output reflects location/season prior only.")
        for k in ("ph", "ec", "tds", "turbidity", "do", "nh3n"):
            v = r.get(k)
            if v not in (None, "") and k in VALID_RANGES and np.isnan(_clean(v, k)): w.append(f"'{k}'={v} is outside the valid range {VALID_RANGES[k]} and was ignored.")
        if r.get("tds") not in (None, "") or r.get("turbidity") not in (None, ""): w.append("TDS and turbidity are accepted but not used by the model (never observed together with a DO label in training data).")
        if r.get("water_body") and r["water_body"] not in WATER_BODY_TYPES: w.append(f"water_body must be one of {WATER_BODY_TYPES}; treated as 'other'.")
        return w

if __name__ == "__main__":   # CLI: echo '{"reading": {...}}' | python -m swq_risk.inference
    import sys; p = RiskPredictor(); d = json.load(sys.stdin); print(json.dumps(p.predict(d["reading"], d.get("history")), indent=2))
