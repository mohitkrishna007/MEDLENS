import re
from typing import Tuple, Optional

def parse_numeric(val_str: str) -> Optional[float]:
    """Extracts first numeric float from string e.g. '250,000 /uL' -> 250000.0 or '1,250.5 mg/dL' -> 1250.5"""
    if not val_str:
        return None
    clean = str(val_str).replace(",", "")
    match = re.search(r"[-+]?\d*\.\d+|\d+", clean)
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
    
    if not ref_range or ref_range.strip().lower() in ["not provided", "not provided in source", "none", "n/a", "", "null", "unknown"]:
        return "UNKNOWN", numeric_val

    ref_clean = ref_range.strip().replace(",", "")
    val_clean = val_str.strip().lower()
    
    # 1. Qualitative match (e.g. Positive, Negative, Non-Reactive)
    if val_clean in ["negative", "non-reactive", "normal", "absent", "clear", "nil"]:
        if any(tok in ref_clean.lower() for tok in ["negative", "non-reactive", "normal", "absent", "nil", "clear"]):
            return "NORMAL", numeric_val
        elif any(tok in ref_clean.lower() for tok in ["positive", "reactive", "detected"]):
            return "LOW", numeric_val
    elif val_clean in ["positive", "reactive", "detected"]:
        if any(tok in ref_clean.lower() for tok in ["negative", "non-reactive", "normal", "absent"]):
            return "HIGH", numeric_val

    if numeric_val is None:
        return "UNKNOWN", None

    # Strip prefix descriptors like "Desirable: < 200", "Optimal: < 100", "Normal: 70-99", "Ref: 13.0-17.0"
    ref_body = re.sub(r"^(?:desirable|optimal|normal|reference|ref|range|target)\s*[:|-]?\s*", "", ref_clean, flags=re.IGNORECASE).strip()

    # 2. Greater Than Inequality e.g. ">= 40", "> 40", "≥ 40"
    greater_than = re.search(r"(?:>=|≥|>)\s*(\d*\.\d+|\d+)", ref_body)
    if greater_than:
        lower_limit = float(greater_than.group(1))
        if numeric_val >= lower_limit:
            return "NORMAL", numeric_val
        else:
            return "LOW", numeric_val

    # 3. Less Than Inequality e.g. "< 200", "<= 100", "≤ 100"
    less_than = re.search(r"(?:<=|≤|<)\s*(\d*\.\d+|\d+)", ref_body)
    if less_than:
        upper_limit = float(less_than.group(1))
        if numeric_val <= upper_limit:
            return "NORMAL", numeric_val
        else:
            return "HIGH", numeric_val

    # 4. Numeric range e.g. "13.0 - 17.0", "12.0-15.5", "12 to 15.5", "12 – 15.5"
    range_match = re.search(r"(\d*\.\d+|\d+)\s*(?:-|to|–|—)\s*(\d*\.\d+|\d+)", ref_body)
    if range_match:
        low_limit = float(range_match.group(1))
        high_limit = float(range_match.group(2))
        
        if numeric_val < low_limit:
            return "LOW", numeric_val
        elif numeric_val > high_limit:
            return "HIGH", numeric_val
        else:
            return "NORMAL", numeric_val

    # 5. Single upper bound limit e.g. "Up to 200" or "Max 150"
    up_to_match = re.search(r"(?:up\s+to|max|less\s+than)\s+(\d*\.\d+|\d+)", ref_body, re.IGNORECASE)
    if up_to_match:
        max_val = float(up_to_match.group(1))
        if numeric_val <= max_val:
            return "NORMAL", numeric_val
        else:
            return "HIGH", numeric_val

    return "UNKNOWN", numeric_val
