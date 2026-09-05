import os
import json
import re
from typing import List, Dict, Any, Optional
from backend.services.range_classifier import classify_lab_result

# Extraction system prompt instructing strict medical compliance
EXTRACTION_PROMPT = """
You are a specialized medical document processing AI for MedLens.
Extract structured clinical information from the provided document text.

CRITICAL MEDICAL SAFETY RULES:
1. Extract ONLY information explicitly present in the document.
2. DO NOT invent test values, units, dates, or reference ranges.
3. If a reference range is NOT explicitly stated in the source text, set reference_range to null or "Not provided". DO NOT use external medical knowledge to manufacture a reference range.
4. Extract test date if stated.

Return a valid JSON object matching this schema:
{
  "doc_type": "Blood Test Report" | "Prescription" | "Diagnostic Summary" | "General Report",
  "header_info": {
    "patient_name": string or null,
    "age": integer or null,
    "sex": string or null,
    "report_date": string (YYYY-MM-DD or readable) or null
  },
  "lab_results": [
    {
      "test_name": string,
      "value": string,
      "unit": string or null,
      "reference_range": string or null,
      "test_date": string or null,
      "snippet": string (exact text segment from document where extracted),
      "confidence": "High" | "Medium" | "Low"
    }
  ],
  "medications": [
    {
      "name": string,
      "dose": string or null,
      "frequency": string or null,
      "confidence": "High" | "Medium" | "Low"
    }
  ],
  "conditions": [
    {
      "name": string,
      "confidence": "High" | "Medium" | "Low"
    }
  ]
}
"""

def extract_structured_data(doc_text: str, filename: str = "document.pdf") -> Dict[str, Any]:
    """
    Main extraction function. Tries Gemini API if GEMINI_API_KEY set,
    otherwise uses intelligent rule-based extraction pipeline.
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
            return _post_process_extracted_data(parsed_json, filename)
        except Exception as e:
            print(f"[Gemini Extraction Notice] LLM extraction fallback to rule-engine: {e}")

    # Rule-Based NLP Extraction Fallback
    return _rule_based_extraction(doc_text, filename)

def _post_process_extracted_data(data: Dict[str, Any], filename: str) -> Dict[str, Any]:
    """Applies reference range classification engine to AI extractions."""
    lab_results = []
    for item in data.get("lab_results", []):
        val_str = str(item.get("value", "")).strip()
        ref_range = item.get("reference_range")
        if ref_range and str(ref_range).strip().lower() in ["none", "null", "undefined"]:
            ref_range = None
            
        status, num_val = classify_lab_result(val_str, ref_range)
        
        lab_results.append({
            "test_name": item.get("test_name", "Unknown Test"),
            "value": val_str,
            "numeric_value": num_val,
            "unit": item.get("unit"),
            "reference_range": ref_range if ref_range else "Not provided in source",
            "status": status,
            "test_date": item.get("test_date") or data.get("header_info", {}).get("report_date"),
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
    Intelligent medical regex parser for PDFs and scanned text.
    Extracts tabular test names, values, units, reference ranges, and header dates.
    """
    lines = doc_text.split("\n")
    lab_results = []
    medications = []
    conditions = []
    
    # 1. Extract report date from header
    date_match = re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4})\b", doc_text, re.IGNORECASE)
    report_date = date_match.group(1) if date_match else None

    # 2. Extract patient name/age if present
    age_match = re.search(r"Age\s*:\s*(\d{1,3})", doc_text, re.IGNORECASE)
    age = int(age_match.group(1)) if age_match else None
    
    sex_match = re.search(r"Sex\s*:\s*(Male|Female|M|F)", doc_text, re.IGNORECASE)
    sex = sex_match.group(1).upper() if sex_match else None

    # 3. Known Common Medical Lab Patterns (e.g. "Hemoglobin 11.2 g/dL (12.0 - 15.5)")
    # Pattern A: Test Name | Value | Unit | Reference Range
    common_tests = [
        "Hemoglobin", "HbA1c", "Fasting Blood Sugar", "Glucose", "Platelets", "WBC", "RBC", 
        "Cholesterol", "Triglycerides", "HDL", "LDL", "Serum Creatinine", "BUN", "TSH", 
        "Vitamin D", "Vitamin B12", "ALT", "AST", "Bilirubin", "Iron", "Ferritin"
    ]
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
            
        for test in common_tests:
            if re.search(r"\b" + re.escape(test) + r"\b", line_clean, re.IGNORECASE):
                # Search for numbers in line
                nums = re.findall(r"\d+\.\d+|\d+", line_clean)
                if nums:
                    val_str = nums[0]
                    # Check for units
                    unit_match = re.search(r"(g/dL|mg/dL|%|mmol/L|mIU/L|ng/mL|pg/mL|uIU/mL|/\s*uL|cells/mcL)", line_clean, re.IGNORECASE)
                    unit = unit_match.group(1) if unit_match else ""
                    
                    # Check for range in brackets or after
                    range_match = re.search(r"\(?\s*(\d+\.?\d*\s*[-–to]\s*\d+\.?\d*|<\s*\d+\.?\d*|>\s*\d+\.?\d*)\s*\)?", line_clean)
                    ref_range = range_match.group(1) if range_match else None
                    
                    status, num_val = classify_lab_result(val_str, ref_range)
                    
                    lab_results.append({
                        "test_name": test,
                        "value": val_str,
                        "numeric_value": num_val,
                        "unit": unit,
                        "reference_range": ref_range if ref_range else "Not provided in source",
                        "status": status,
                        "test_date": report_date,
                        "source_label": "AI EXTRACTED",
                        "source_document_name": filename,
                        "confidence": "High" if ref_range else "Medium",
                        "verification_status": "AI Extracted",
                        "text_snippet": line_clean,
                        "page_number": 1
                    })
                    break

        # Check for Medication lines e.g. "Metformin 500mg - Twice daily"
        med_match = re.search(r"(Metformin|Lisinopril|Atorvastatin|Amlodipine|Omeprazole|Levothyroxine|Aspirin)\s+(\d+\s*mg)", line_clean, re.IGNORECASE)
        if med_match:
            medications.append({
                "name": med_match.group(1),
                "dose": med_match.group(2),
                "frequency": "Daily",
                "confidence": "High"
            })

    doc_type = "Blood Test Report" if any("Blood" in l or "Hemoglobin" in l for l in lines) else "General Report"

    return {
        "doc_type": doc_type,
        "header_info": {
            "patient_name": None,
            "age": age,
            "sex": sex,
            "report_date": report_date
        },
        "lab_results": lab_results,
        "medications": medications,
        "conditions": conditions
    }
