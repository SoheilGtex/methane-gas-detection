import math

def ppm_from_rs_ratio(rs_r0, a=1000.0, b=-1.7):
    """
    Very rough model: ppm ≈ a * (Rs/R0)^b
    'a' and 'b' must be fitted from the sensor datasheet curve for methane (CH4).
    This is NOT for industrial safety.
    """
    try:
        r = float(rs_r0)
        return float(a) * (r ** float(b))
    except Exception:
        return None
