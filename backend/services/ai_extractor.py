import os
import json
import re
from typing import List, Dict, Any, Optional
from backend.services.range_classifier import classify_lab_result

# System prompt for optional Gemini API extraction
EXTRACTION_PROMPT = """
You are a specialized medical document processing AI for MedLens.
Extract structured clinical information from the provided document text.

CRITICAL MEDICAL SAFETY RULES:
1. Extract ONLY information explicitly present in the document.
2. DO NOT invent test values, units, dates, or reference ranges.
3. If a reference range is NOT explicitly stated in the source text, set reference_range to "Not provided in source".
4. Extract patient header info: patient_name, age, sex, report_date.

Return a valid JSON object matching this schema:
{
  "doc_type": "Blood Test Report" | "Prescription" | "Diagnostic Summary" | "General Report",
  "header_info": {
    "patient_name": string or null,
    "age": integer or null,
    "sex": string or null,
    "report_date": string or null
  },
  "lab_results": [
    {
      "test_name": string,
      "value": string,
      "unit": string or null,
      "reference_range": string or null,
      "test_date": string or null,
      "snippet": string,
      "confidence": "High" | "Medium"
    }
  ],
  "medications": [],
  "conditions": []
}
"""

LAB_TEST_MAP = [
    ("hemoglobin", "Hemoglobin"),
    ("hgb", "Hemoglobin"),
    ("wbc", "WBC"),
    ("white blood cell", "WBC"),
    ("platelets", "Platelets"),
    ("platelet count", "Platelets"),
    ("fasting glucose", "Fasting Glucose"),
    ("fasting blood sugar", "Fasting Glucose"),
    ("glucose, fasting", "Fasting Glucose"),
    ("glucose", "Glucose"),
    ("total cholesterol", "Total Cholesterol"),
    ("cholesterol, total", "Total Cholesterol"),
    ("cholesterol", "Total Cholesterol"),
    ("ldl cholesterol", "LDL"),
    ("ldl", "LDL"),
    ("hdl cholesterol", "HDL"),
    ("hdl", "HDL"),
    ("triglycerides", "Triglycerides"),
    ("serum creatinine", "Creatinine"),
    ("creatinine", "Creatinine"),
    ("alt", "ALT"),
    ("sgpt", "ALT"),
    ("ast", "AST"),
    ("sgot", "AST"),
    ("hba1c", "HbA1c"),
    ("bun", "BUN"),
    ("tsh", "TSH"),
    ("vitamin d", "Vitamin D"),
    ("vitamin b12", "Vitamin B12"),
    ("hs-crp", "Hs-CRP"),
    ("crp", "Hs-CRP"),
    ("bilirubin", "Bilirubin"),
    ("iron", "Iron"),
    ("ferritin", "Ferritin")
]

UNITS_REGEX_STR = r"(g/dL|mg/dL|U/L|IU/L|10\^3/uL|10\^3/µL|x10\^3/uL|x10\^3/µL|10\^6/uL|cells/mcL|mcg/dL|ng/mL|pg/mL|mIU/L|uIU/mL|µIU/mL|mmol/L|umol/L|µmol/L|mEq/L|%|/\s*uL|/\s*µL|k/uL|M/uL)"

def extract_structured_data(doc_text: str, filename: str = "document.pdf") -> Dict[str, Any]:
    """
    Main extraction function. Tries Gemini API if GEMINI_API_KEY set,
    otherwise uses deterministic, robust medical NLP extraction pipeline.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and len(api_key.strip()) > 5:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{EXTRACTION_PROMPT}\n\nDOCUMENT TEXT:\n{doc_text[:8000]}",
                config={"response_mime_type": "application/json"}
            )
            parsed_json = json.loads(response.text)
            processed = _post_process_extracted_data(parsed_json, filename)
            if len(processed.get("lab_results", [])) > 0:
                return processed
        except Exception as e:
            print(f"[Gemini Extraction Notice] Gemini API fallback to rule engine: {e}")

    # Robust Rule-Based Extraction Engine
    return _rule_based_extraction(doc_text, filename)

def _post_process_extracted_data(data: Dict[str, Any], filename: str) -> Dict[str, Any]:
    """Applies reference range classification engine to AI extractions."""
    lab_results = []
    header_info = data.get("header_info", {})
    report_date = header_info.get("report_date")

    for item in data.get("lab_results", []):
        val_str = str(item.get("value", "")).strip()
        ref_range = item.get("reference_range")
        if ref_range and str(ref_range).strip().lower() in ["none", "null", "undefined", "not provided"]:
            ref_range = "Not provided in source"
            
        status, num_val = classify_lab_result(val_str, ref_range)
        
        lab_results.append({
            "test_name": item.get("test_name", "Unknown Test"),
            "value": val_str,
            "numeric_value": num_val,
            "unit": item.get("unit"),
            "reference_range": ref_range if ref_range else "Not provided in source",
            "status": status,
            "test_date": item.get("test_date") or report_date,
            "source_label": "AI EXTRACTED",
            "source_document_name": filename,
            "confidence": item.get("confidence", "High"),
            "verification_status": "AI Extracted",
            "text_snippet": item.get("snippet") or f"{item.get('test_name')}: {val_str} {item.get('unit') or ''}",
            "page_number": 1
        })
        
    data["lab_results"] = lab_results
    return data

def _rule_based_extraction(doc_text: str, filename: str) -> Dict[str, Any]:
    """
    Robust medical lab report & demographics extraction pipeline.
    Parses patient header info and tabular test results.
    """
    lines = [line.strip() for line in doc_text.split("\n") if line.strip()]
    
    # ----------------------------
    # 1. Demographics Extraction
    # ----------------------------
    patient_name = None
    age = None
    sex = None
    report_date = None

    for line in lines:
        if not patient_name:
            nm = re.search(r"(?:Patient\s*Name|Patient|Name)\s*[:|-]\s*([A-Za-z .]{2,30})", line, re.IGNORECASE)
            if nm:
                cand = nm.group(1).strip()
                if cand.lower() not in ["details", "report", "info", "age", "gender", "sex", "id", "date"]:
                    patient_name = cand
        if not age:
            am = re.search(r"\bAge\b[^\n\d]*(\d{1,3})", line, re.IGNORECASE)
            if am:
                try:
                    age = int(am.group(1))
                except ValueError:
                    pass
        if not sex:
            sm = re.search(r"\b(?:Sex|Gender)\s*[:|-]?\s*(Male|Female|M|F)\b", line, re.IGNORECASE)
            if not sm:
                sm = re.search(r"/\s*(Male|Female|M|F)\b", line, re.IGNORECASE)
            if sm:
                raw_s = sm.group(1).upper()
                sex = "Male" if raw_s.startswith("M") else "Female"
        if not report_date:
            dm = re.search(r"\b(?:Date|Report Date|Sample Date|Collected Date)\s*[:|-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2}[-\s/]+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-\s/]+\d{2,4})\b", line, re.IGNORECASE)
            if dm:
                report_date = dm.group(1)

    # ----------------------------
    # 2. Lab Results Extraction
    # ----------------------------
    lab_results = []
    extracted_tests_seen = set()

    for idx, line in enumerate(lines):
        # Merge next line if line is just a test name
        full_line_context = line
        if idx + 1 < len(lines):
            full_line_context += " " + lines[idx + 1]

        # Check against test dictionary
        matched_test = None
        target_text = None
        for key_test, display_name in LAB_TEST_MAP:
            if display_name.lower() not in extracted_tests_seen:
                pattern = r"\b" + re.escape(key_test) + r"\b"
                if re.search(pattern, line, re.IGNORECASE):
                    matched_test = (key_test, display_name)
                    target_text = line
                    break
                elif not re.search(r"\d", line) and re.search(pattern, full_line_context, re.IGNORECASE):
                    matched_test = (key_test, display_name)
                    target_text = full_line_context
                    break

        if matched_test and target_text:
            key_test, display_name = matched_test
            
            # Extract numerical result value
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", target_text)
            if nums:
                val_str = nums[0]
                
                # Extract Unit
                unit_match = re.search(UNITS_REGEX_STR, target_text, re.IGNORECASE)
                unit = unit_match.group(1) if unit_match else ""

                # Extract Reference Range from source line
                range_match = re.search(
                    r"(\d+\.?\d*\s*(?:-|to|–|—)\s*\d+\.?\d*|(?:>=|<=|≥|≤|>|<)\s*=?\s*\d+\.?\d*|up\s+to\s+\d+\.?\d*|max\s+\d+\.?\d*)",
                    target_text,
                    re.IGNORECASE
                )
                
                ref_range = None
                if range_match:
                    found_range = range_match.group(1).strip()
                    if found_range != val_str:
                        ref_range = found_range

                status, num_val = classify_lab_result(val_str, ref_range)

                lab_results.append({
                    "test_name": display_name,
                    "value": val_str,
                    "numeric_value": num_val,
                    "unit": unit if unit else None,
                    "reference_range": ref_range if ref_range else "Not provided in source",
                    "status": status,
                    "test_date": report_date,
                    "source_label": "AI EXTRACTED",
                    "source_document_name": filename,
                    "confidence": "High" if ref_range else "Medium",
                    "verification_status": "AI Extracted",
                    "text_snippet": target_text,
                    "page_number": 1
                })
                extracted_tests_seen.add(display_name.lower())
                extracted_tests_seen.add(key_test.lower())
                for w in (key_test + " " + display_name).lower().split():
                    if len(w) > 2:
                        extracted_tests_seen.add(w)

    # General Row Parser Pass for tests not in hardcoded dictionary
    STOP_WORDS = {"patient", "age", "sex", "gender", "date", "report", "referred", "laboratory", "panel", "description", "result", "units", "reference", "range", "details", "metabolic", "blood", "count", "complete", "dr", "clinic"}
    generic_rows = re.findall(
        r"([A-Za-z\s]{3,25})\s+(\d+\.?\d*)\s*(g/dL|mg/dL|U/L|IU/L|10\^3/uL|x10\^3/uL|%|mmol/L)?\s*(\d+\.?\d*\s*[-–to]\s*\d+\.?\d*|[<>=≤≥]\s*\d+\.?\d*)?",
        doc_text,
        re.IGNORECASE
    )
    for g_name, g_val, g_unit, g_range in generic_rows:
        g_name_clean = g_name.strip()
        g_lower = g_name_clean.lower()
        if len(g_name_clean) > 2 and g_lower not in extracted_tests_seen:
            if not any(sw in g_lower for sw in STOP_WORDS):
                status, num_val = classify_lab_result(g_val, g_range)
                lab_results.append({
                    "test_name": g_name_clean.title(),
                    "value": g_val,
                    "numeric_value": num_val,
                    "unit": g_unit.strip() if g_unit else None,
                    "reference_range": g_range.strip() if g_range else "Not provided in source",
                    "status": status,
                    "test_date": report_date,
                    "source_label": "AI EXTRACTED",
                    "source_document_name": filename,
                    "confidence": "High" if g_range else "Medium",
                    "verification_status": "AI Extracted",
                    "text_snippet": f"{g_name_clean} {g_val} {g_unit or ''} {g_range or ''}".strip(),
                    "page_number": 1
                })
                extracted_tests_seen.add(g_lower)

    doc_type = "Blood Test Report" if len(lab_results) > 0 else "General Report"

    # Log Extraction Summary
    print(f"[Lab Extraction Pipeline] Candidate lab rows detected: {len(lines)}")
    print(f"[Lab Extraction Pipeline] Structured lab results: {len(lab_results)}")
    print(f"[Lab Extraction Pipeline] Patient fields detected: Name={patient_name}, Age={age}, Sex={sex}, Date={report_date}")

    return {
        "doc_type": doc_type,
        "header_info": {
            "patient_name": patient_name,
            "age": age,
            "sex": sex,
            "report_date": report_date
        },
        "lab_results": lab_results,
        "medications": [],
        "conditions": []
    }
