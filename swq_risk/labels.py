import numpy as np
from .config import DO_LOW_MIN, DO_MODERATE_MIN, NH3N_HIGH_MAX

def risk_class(do, nh3n=None):
    """0 Low / 1 Moderate / 2 High from laboratory DO (and NH3-N if available). NaN if DO unknown."""
    if do is None or (isinstance(do, float) and np.isnan(do)):
        return np.nan
    r = 0 if do >= DO_LOW_MIN else (1 if do >= DO_MODERATE_MIN else 2)
    if nh3n is not None and not (isinstance(nh3n, float) and np.isnan(nh3n)) and nh3n > NH3N_HIGH_MAX:
        r = 2
    return float(r)
