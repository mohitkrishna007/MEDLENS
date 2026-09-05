import re
from typing import Tuple, Optional

def parse_numeric(val_str: str) -> Optional[float]:
    """Extracts first numeric float from string e.g. '11.2 g/dL' -> 11.2"""
    if not val_str:
        return None
    # match patterns like 12, 12.5, .5
    match = re.search(r"[-+]?\d*\.\d+|\d+", str(val_str))
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return None
    return None

def classify_lab_result(val_str: str, ref_range: Optional[str]) -> Tuple[str, Optional[float]]:
    """
    Classifies a lab test value against the source-provided reference range.
    Returns (status, numeric_val)
    Possible statuses:
    - "LOW"
    - "NORMAL"
    - "HIGH"
    - "UNKNOWN" (Unable to determine from source)
    
    STRICT RULE: If ref_range is missing, empty, or 'Not provided', returns "UNKNOWN".
    Never manufactures external reference ranges!
    """
    numeric_val = parse_numeric(val_str)
    
    if not ref_range or ref_range.strip().lower() in ["not provided", "none", "n/a", "", "null", "unknown"]:
        return "UNKNOWN", numeric_val

    ref_clean = ref_range.strip()
    val_clean = val_str.strip().lower()
    
    # 1. Qualitative match (e.g. Positive, Negative, Non-Reactive)
    if val_clean in ["negative", "non-reactive", "normal", "absent", "clear"]:
        if "negative" in ref_clean.lower() or "non-reactive" in ref_clean.lower() or "normal" in ref_clean.lower():
            return "NORMAL", numeric_val
        elif "positive" in ref_clean.lower() or "reactive" in ref_clean.lower():
            return "LOW", numeric_val # Or abnormal
    elif val_clean in ["positive", "reactive", "detected"]:
        if "negative" in ref_clean.lower() or "non-reactive" in ref_clean.lower():
            return "HIGH", numeric_val # Abnormal flag

    if numeric_val is None:
        return "UNKNOWN", None

    # 2. Inequality in reference range e.g. "< 5.0", "<5", "<= 10", "> 10.0"
    less_than = re.search(r"<\s*=?\s*(\d*\.\d+|\d+)", ref_clean)
    if less_than:
        upper_limit = float(less_than.group(1))
        if numeric_val <= upper_limit:
            return "NORMAL", numeric_val
        else:
            return "HIGH", numeric_val

    greater_than = re.search(r">\s*=?\s*(\d*\.\d+|\d+)", ref_clean)
    if greater_than:
        lower_limit = float(greater_than.group(1))
        if numeric_val >= lower_limit:
            return "NORMAL", numeric_val
        else:
            return "LOW", numeric_val

    # 3. Numeric range e.g. "12.0 - 15.5", "12.0-15.5", "12 to 15.5", "12 – 15.5"
    range_match = re.search(r"(\d*\.\d+|\d+)\s*(?:-|to|–|—)\s*(\d*\.\d+|\d+)", ref_clean)
    if range_match:
        low_limit = float(range_match.group(1))
        high_limit = float(range_match.group(2))
        
        if numeric_val < low_limit:
            return "LOW", numeric_val
        elif numeric_val > high_limit:
            return "HIGH", numeric_val
        else:
            return "NORMAL", numeric_val

    # 4. Single upper bound limit e.g. "Up to 200" or "Max 150"
    up_to_match = re.search(r"(?:up\s+to|max|less\s+than)\s+(\d*\.\d+|\d+)", ref_clean, re.IGNORECASE)
    if up_to_match:
        max_val = float(up_to_match.group(1))
        if numeric_val <= max_val:
            return "NORMAL", numeric_val
        else:
            return "HIGH", numeric_val

    return "UNKNOWN", numeric_val
