"""Feature engineering. ONE implementation used by both training and inference (no train/serve skew)."""
import re
import numpy as np
import pandas as pd
from .config import *
from .labels import risk_class

def infer_water_body(name):
    n = str(name).upper()
    if re.search(r"GROUND|WELL|BORE|HAND ?PUMP|TUBE", n): return "groundwater"
    if re.search(r"\bSEA\b|CREEK|ESTUARY|\bBAY\b|COAST", n): return "coastal"
    if re.search(r"CANAL|DRAIN|NALA|NALLA|NALLAH|\bSTP\b|EFFLUENT", n): return "canal_drain"
    if re.search(r"LAKE|TALAB|POND|TANK|\bDAM\b|RESERVOIR|SAGAR|BACKWATER|JALASHAY", n): return "lake_reservoir"
    if re.search(r"RIVER|\bR\b|NADI|NEAR|AT |D/S|U/S", n): return "river"
    return "other"

def _clean(v, key=None):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return np.nan
    if np.isnan(v): return np.nan
    if key in VALID_RANGES:
        lo, hi = VALID_RANGES[key]
        if v < lo or v > hi: return np.nan
    return v

def history_features(history, now_ts, ph_now):
    """history: list of dicts {timestamp, ph?, do?, nh3n?} - STRICTLY earlier than now_ts."""
    f = {k: np.nan for k in NUM_HISTORY}; f["n_prev"] = 0
    if not history: return f
    h = pd.DataFrame(history)
    h["t"] = pd.to_datetime(h["timestamp"]);
    h = h[h["t"] < now_ts].sort_values("t")
    if h.empty: return f
    for c in ("ph", "do", "nh3n"):
        h[c] = [ _clean(x, c) for x in h[c]] if c in h else np.nan
    h["risk"] = [risk_class(d, n) for d, n in zip(h["do"], h["nh3n"])]
    f["n_prev"] = len(h); f["days_since_last"] = (now_ts - h["t"].iloc[-1]).days
    r = h["risk"].dropna()
    if len(r):
        f.update(last_risk=r.iloc[-1], mean_risk=r.mean(), max_risk=r.max(), last3_mean_risk=r.iloc[-3:].mean())
    d = h["do"].dropna()
    if len(d): f.update(last_do=d.iloc[-1], mean_do=d.mean(), min_do=d.min())
    p = h["ph"].dropna()
    if len(p):
        f.update(last_ph=p.iloc[-1], mean_ph=p.mean())
        if not np.isnan(ph_now): f.update(ph_delta_last=ph_now - p.iloc[-1], ph_vs_hist=ph_now - p.mean())
    return f

def build_row(reading, history=None):
    """reading keys: timestamp, ph, [ec, tds, turbidity, colour, odour], lat, lon, state, [station_name | water_body]"""
    ts = pd.to_datetime(reading["timestamp"])
    ph = _clean(reading.get("ph"), "ph"); ec = _clean(reading.get("ec"), "ec")
    tds = _clean(reading.get("tds"), "tds"); tu = _clean(reading.get("turbidity"), "turbidity")
    cond = ec if not np.isnan(ec) else (tds / 0.65 if not np.isnan(tds) else np.nan)
    colour = str(reading.get("colour") or "").strip().lower(); odour = str(reading.get("odour") or "").strip().lower()
    wb = reading.get("water_body") or infer_water_body(reading.get("station_name", ""))
    if wb not in WATER_BODY_TYPES: wb = "other"
    m = ts.month
    row = dict(
        ph=ph, ph_dev=abs(ph - 7.5) if not np.isnan(ph) else np.nan,
        ph_out_of_range=float(ph < 6.5 or ph > 8.5) if not np.isnan(ph) else np.nan,
        ec_log=np.log1p(ec) if not np.isnan(ec) else np.nan, tds_log=np.log1p(tds) if not np.isnan(tds) else np.nan,
        turb_log=np.log1p(tu) if not np.isnan(tu) else np.nan, cond_log=np.log1p(cond) if not np.isnan(cond) else np.nan,
        ec_tds_ratio=(tds / ec) if (not np.isnan(ec) and not np.isnan(tds) and ec > 0) else np.nan,
        has_ec=float(not np.isnan(ec)), has_tds=float(not np.isnan(tds)), has_turb=float(not np.isnan(tu)),
        colour_abnormal=float(colour not in ("", "clear", "nan", "-")), odour_flag=float(odour not in ("", "nan", "-", "none")),
        lat=_clean(reading.get("lat")), lon=_clean(reading.get("lon")),
        month_sin=np.sin(2 * np.pi * m / 12), month_cos=np.cos(2 * np.pi * m / 12), monsoon=float(m in MONSOON_MONTHS),
        water_body=wb, state=reading.get("state") if reading.get("state") in STATES else "other")
    row.update(history_features(history, ts, ph))
    return row

def to_frame(rows):
    df = pd.DataFrame(rows)
    for c in NUM_STATIC + NUM_HISTORY:
        if c not in df: df[c] = np.nan
    return df[NUM_STATIC + NUM_HISTORY + CAT]
