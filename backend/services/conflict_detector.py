from typing import List, Dict, Any
from backend.models import Patient, LabResult, Conflict

def detect_patient_conflicts(patient: Patient, db_session) -> List[Dict[str, Any]]:
    """
    Scans patient documents, manual intake, and lab results for inconsistencies.
    Returns list of conflict dicts to be stored or displayed.
    """
    detected_conflicts = []
    
    # 1. Demographics Check: Intake Age vs Document Extractions
    intake_age = patient.age
    if intake_age:
        for doc in patient.documents:
            if doc.raw_text:
                # search for age in raw text
                import re
                age_match = re.search(r"\bAge\s*:\s*(\d{1,3})\b", doc.raw_text, re.IGNORECASE)
                if age_match:
                    doc_age = int(age_match.group(1))
                    if doc_age != intake_age:
                        conflict_item = {
                            "patient_id": patient.id,
                            "conflict_type": "Demographic",
                            "field_name": "Patient Age",
                            "source_a_name": "User Profile Intake",
                            "source_a_value": f"{intake_age} years",
                            "source_b_name": f"Document: {doc.filename}",
                            "source_b_value": f"{doc_age} years",
                            "description": f"Patient age in profile ({intake_age}) differs from age stated in {doc.filename} ({doc_age}).",
                            "severity": "MEDIUM",
                            "status": "Unresolved"
                        }
                        detected_conflicts.append(conflict_item)

    # 2. Duplicate Lab Test Conflict Check (Same test name on same date with different values)
    lab_results = patient.lab_results
    tests_by_key = {}
    for res in lab_results:
        key = f"{res.test_name.strip().lower()}_{res.test_date or 'no_date'}"
        if key not in tests_by_key:
            tests_by_key[key] = []
        tests_by_key[key].append(res)
        
    for key, items in tests_by_key.items():
        if len(items) > 1:
            first_val = items[0].value.strip()
            for second in items[1:]:
                if second.value.strip() != first_val:
                    conflict_item = {
                        "patient_id": patient.id,
                        "conflict_type": "Lab Result Discrepancy",
                        "field_name": items[0].test_name,
                        "source_a_name": items[0].source_document_name or "Report A",
                        "source_a_value": f"{items[0].value} {items[0].unit or ''}",
                        "source_b_name": second.source_document_name or "Report B",
                        "source_b_value": f"{second.value} {second.unit or ''}",
                        "description": f"Conflicting values found for {items[0].test_name} on date {items[0].test_date or 'unspecified'}.",
                        "severity": "HIGH",
                        "status": "Unresolved"
                    }
                    detected_conflicts.append(conflict_item)

    # 3. Medication Dosage Conflicts
    meds = patient.medications or []
    med_names = {}
    for m in meds:
        name = m.get("name", "").strip().lower()
        if name:
            if name not in med_names:
                med_names[name] = m
            else:
                prev_dose = med_names[name].get("dose")
                curr_dose = m.get("dose")
                if prev_dose and curr_dose and prev_dose != curr_dose:
                    conflict_item = {
                        "patient_id": patient.id,
                        "conflict_type": "Medication Dosage Mismatch",
                        "field_name": f"Medication: {m.get('name')}",
                        "source_a_name": f"Source ({med_names[name].get('source', 'Intake')})",
                        "source_a_value": prev_dose,
                        "source_b_name": f"Source ({m.get('source', 'Report')})",
                        "source_b_value": curr_dose,
                        "description": f"Conflicting dosages listed for medication {m.get('name')}.",
                        "severity": "HIGH",
                        "status": "Unresolved"
                    }
                    detected_conflicts.append(conflict_item)

    return detected_conflicts
