from sqlalchemy.orm import Session
from backend.models import Patient, Document, LabResult, Conflict, TimelineEvent, AISummary
from backend.services.ai_summary import MEDICAL_DISCLAIMER

def seed_demo_patient(db: Session) -> Patient:
    """Creates a comprehensive synthetic patient with multi-report history & conflicts."""
    # Check if demo patient exists
    existing = db.query(Patient).filter(Patient.patient_id_code == "PAT-2025-089").first()
    if existing:
        return existing

    # 1. Patient Intake Profile
    patient = Patient(
        patient_id_code="PAT-2025-089",
        display_name="Jane Doe",
        age=52,
        sex="Female",
        notes="Patient reports mild fatigue during routine annual review. History of Type 2 Diabetes & Mild Anemia.",
        symptoms=[
            {"name": "Fatigue", "source": "USER_PROVIDED"},
            {"name": "Mild Dizziness", "source": "USER_PROVIDED"}
        ],
        conditions=[
            {"name": "Type 2 Diabetes Mellitus", "source": "USER_PROVIDED"},
            {"name": "Iron Deficiency Anemia", "source": "USER_PROVIDED"}
        ],
        allergies=[
            {"name": "Penicillin (Mild Hives)", "source": "USER_PROVIDED"}
        ],
        medications=[
            {"name": "Metformin", "dose": "500mg", "frequency": "Twice daily", "source": "USER_PROVIDED"},
            {"name": "Ferrous Sulfate", "dose": "325mg", "frequency": "Daily", "source": "USER_PROVIDED"}
        ],
        medical_history="Diagnosed with T2DM in 2021. Managed with Metformin and dietary changes. Mild iron deficiency anemia documented in early 2025."
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    # 2. Add Documents
    doc1 = Document(
        patient_id=patient.id,
        filename="CBC_Panel_Jan2025.pdf",
        file_path="uploads/demo_cbc_jan.pdf",
        doc_type="Blood Test Report",
        file_size=104857,
        processing_status="PROCESSED",
        extracted_field_count=4,
        raw_text="Metro Health Labs - Complete Blood Count\nPatient Name: Jane Doe | Age: 52 | Sex: F\nDate: 2025-01-15\nHemoglobin: 10.4 g/dL (Reference Range: 12.0 - 15.5 g/dL) [LOW]\nWBC Count: 6.8 x10^3/uL (Reference Range: 4.5 - 11.0 x10^3/uL) [NORMAL]\nPlatelet Count: 245 x10^3/uL (Reference Range: 150 - 450 x10^3/uL) [NORMAL]"
    )
    doc2 = Document(
        patient_id=patient.id,
        filename="Lipid_Panel_Feb2025.pdf",
        file_path="uploads/demo_lipid_feb.pdf",
        doc_type="Blood Test Report",
        file_size=98200,
        processing_status="PROCESSED",
        extracted_field_count=3,
        raw_text="Metro Health Labs - Lipid Profile\nPatient Name: Jane Doe | Age: 52 | Sex: F\nDate: 2025-02-18\nTotal Cholesterol: 215 mg/dL (Reference Range: < 200 mg/dL) [HIGH]\nHDL Cholesterol: 55 mg/dL (Reference Range: > 50 mg/dL) [NORMAL]\nLDL Cholesterol: 138 mg/dL (Reference Range: < 100 mg/dL) [HIGH]\nTriglycerides: 160 mg/dL (Reference Range: < 150 mg/dL) [HIGH]"
    )
    doc3 = Document(
        patient_id=patient.id,
        filename="CBC_FollowUp_Apr2025.pdf",
        file_path="uploads/demo_cbc_apr.pdf",
        doc_type="Blood Test Report",
        file_size=102100,
        processing_status="PROCESSED",
        extracted_field_count=1,
        raw_text="Metro Health Labs - Follow-Up CBC\nPatient Name: Jane Doe | Age: 52 | Sex: F\nDate: 2025-04-22\nHemoglobin: 11.2 g/dL (Reference Range: 12.0 - 15.5 g/dL) [LOW]"
    )
    doc4 = Document(
        patient_id=patient.id,
        filename="CBC_FollowUp_Jul2025.pdf",
        file_path="uploads/demo_cbc_jul.pdf",
        doc_type="Blood Test Report",
        file_size=103400,
        processing_status="PROCESSED",
        extracted_field_count=1,
        raw_text="Metro Health Labs - Follow-Up CBC\nPatient Name: Jane Doe | Age: 52 | Sex: F\nDate: 2025-07-10\nHemoglobin: 12.4 g/dL (Reference Range: 12.0 - 15.5 g/dL) [NORMAL]"
    )
    doc5 = Document(
        patient_id=patient.id,
        filename="Specialty_Marker_Aug2025.pdf",
        file_path="uploads/demo_specialty_aug.pdf",
        doc_type="Diagnostic Report",
        file_size=88400,
        processing_status="PROCESSED",
        extracted_field_count=1,
        raw_text="Metro Health Labs - Inflammatory Marker\nPatient Name: Jane Doe | Age: 54 | Sex: F\nDate: 2025-08-05\nHs-CRP: 3.2 mg/L (Reference Range: Not provided)"
    )

    db.add_all([doc1, doc2, doc3, doc4, doc5])
    db.commit()
    db.refresh(doc1)
    db.refresh(doc2)
    db.refresh(doc3)
    db.refresh(doc4)
    db.refresh(doc5)

    # 3. Add Lab Results
    labs = [
        # Jan 2025
        LabResult(
            patient_id=patient.id, document_id=doc1.id, test_name="Hemoglobin", value="10.4", numeric_value=10.4,
            unit="g/dL", reference_range="12.0 - 15.5", status="LOW", test_date="2025-01-15",
            source_label="AI EXTRACTED", source_document_name=doc1.filename, confidence="High", verification_status="User Verified",
            text_snippet="Hemoglobin: 10.4 g/dL (Reference Range: 12.0 - 15.5 g/dL) [LOW]"
        ),
        LabResult(
            patient_id=patient.id, document_id=doc1.id, test_name="WBC Count", value="6.8", numeric_value=6.8,
            unit="x10^3/uL", reference_range="4.5 - 11.0", status="NORMAL", test_date="2025-01-15",
            source_label="AI EXTRACTED", source_document_name=doc1.filename, confidence="High", verification_status="AI Extracted",
            text_snippet="WBC Count: 6.8 x10^3/uL (Reference Range: 4.5 - 11.0 x10^3/uL) [NORMAL]"
        ),
        # Feb 2025
        LabResult(
            patient_id=patient.id, document_id=doc2.id, test_name="Total Cholesterol", value="215", numeric_value=215.0,
            unit="mg/dL", reference_range="< 200", status="HIGH", test_date="2025-02-18",
            source_label="AI EXTRACTED", source_document_name=doc2.filename, confidence="High", verification_status="AI Extracted",
            text_snippet="Total Cholesterol: 215 mg/dL (Reference Range: < 200 mg/dL) [HIGH]"
        ),
        LabResult(
            patient_id=patient.id, document_id=doc2.id, test_name="LDL Cholesterol", value="138", numeric_value=138.0,
            unit="mg/dL", reference_range="< 100", status="HIGH", test_date="2025-02-18",
            source_label="AI EXTRACTED", source_document_name=doc2.filename, confidence="High", verification_status="AI Extracted",
            text_snippet="LDL Cholesterol: 138 mg/dL (Reference Range: < 100 mg/dL) [HIGH]"
        ),
        # Apr 2025
        LabResult(
            patient_id=patient.id, document_id=doc3.id, test_name="Hemoglobin", value="11.2", numeric_value=11.2,
            unit="g/dL", reference_range="12.0 - 15.5", status="LOW", test_date="2025-04-22",
            source_label="AI EXTRACTED", source_document_name=doc3.filename, confidence="High", verification_status="User Verified",
            text_snippet="Hemoglobin: 11.2 g/dL (Reference Range: 12.0 - 15.5 g/dL) [LOW]"
        ),
        # Jul 2025
        LabResult(
            patient_id=patient.id, document_id=doc4.id, test_name="Hemoglobin", value="12.4", numeric_value=12.4,
            unit="g/dL", reference_range="12.0 - 15.5", status="NORMAL", test_date="2025-07-10",
            source_label="AI EXTRACTED", source_document_name=doc4.filename, confidence="High", verification_status="User Verified",
            text_snippet="Hemoglobin: 12.4 g/dL (Reference Range: 12.0 - 15.5 g/dL) [NORMAL]"
        ),
        # Aug 2025 (Missing Reference Range)
        LabResult(
            patient_id=patient.id, document_id=doc5.id, test_name="Hs-CRP", value="3.2", numeric_value=3.2,
            unit="mg/L", reference_range="Not provided in source", status="UNKNOWN", test_date="2025-08-05",
            source_label="AI EXTRACTED", source_document_name=doc5.filename, confidence="Medium", verification_status="AI Extracted",
            text_snippet="Hs-CRP: 3.2 mg/L (Reference Range: Not provided)"
        )
    ]
    db.add_all(labs)

    # 4. Add Conflicts
    conflicts = [
        Conflict(
            patient_id=patient.id,
            conflict_type="Demographic",
            field_name="Patient Age",
            source_a_name="User Profile Intake",
            source_a_value="52 years",
            source_b_name="Document: Specialty_Marker_Aug2025.pdf",
            source_b_value="54 years",
            description="Patient age in user profile (52) differs from age extracted from Specialty_Marker_Aug2025.pdf (54).",
            severity="MEDIUM",
            status="Unresolved"
        ),
        Conflict(
            patient_id=patient.id,
            conflict_type="Medication Dosage Mismatch",
            field_name="Medication: Metformin",
            source_a_name="User Profile Intake",
            source_a_value="500mg Twice daily",
            source_b_name="Prescription_Feb2025.pdf",
            source_b_value="1000mg Daily",
            description="Patient intake lists Metformin 500mg Twice daily, whereas February prescription document lists Metformin 1000mg Daily.",
            severity="HIGH",
            status="Unresolved"
        )
    ]
    db.add_all(conflicts)

    # 5. Add Timeline Events
    timeline = [
        TimelineEvent(patient_id=patient.id, event_type="Lab Test", event_date="2025-01-15", title="Initial CBC Panel", description="Hemoglobin: 10.4 g/dL (LOW)", source_document_id=doc1.id, source_document_name=doc1.filename),
        TimelineEvent(patient_id=patient.id, event_type="Lab Test", event_date="2025-02-18", title="Lipid Profile Test", description="Total Cholesterol 215 mg/dL (HIGH), LDL 138 mg/dL (HIGH)", source_document_id=doc2.id, source_document_name=doc2.filename),
        TimelineEvent(patient_id=patient.id, event_type="Lab Test", event_date="2025-04-22", title="Follow-up CBC", description="Hemoglobin: 11.2 g/dL (LOW - Improved from 10.4)", source_document_id=doc3.id, source_document_name=doc3.filename),
        TimelineEvent(patient_id=patient.id, event_type="Lab Test", event_date="2025-07-10", title="Follow-up CBC", description="Hemoglobin: 12.4 g/dL (NORMAL - Within source reference range)", source_document_id=doc4.id, source_document_name=doc4.filename),
        TimelineEvent(patient_id=patient.id, event_type="Lab Test", event_date="2025-08-05", title="Inflammatory Marker", description="Hs-CRP: 3.2 mg/L (Range Not Provided)", source_document_id=doc5.id, source_document_name=doc5.filename),
    ]
    db.add_all(timeline)

    # 6. Add Initial AI Summary
    summary_text = (
        "MedLens reviewed 5 document(s) and 7 laboratory result(s) for patient Jane Doe (52 yrs, Female).\n\n"
        "Key Documented Findings & Trends:\n"
        "• Hemoglobin demonstrated a documented progressive rise across three lab reports: 10.4 g/dL (Jan 2025, LOW) -> 11.2 g/dL (Apr 2025, LOW) -> 12.4 g/dL (Jul 2025, NORMAL).\n"
        "• Lipid panel (Feb 2025) recorded Total Cholesterol at 215 mg/dL and LDL at 138 mg/dL, both exceeding source reference ranges (< 200 and < 100 mg/dL respectively).\n"
        "• Hs-CRP (Aug 2025) reported a value of 3.2 mg/L; status is marked as 'Unable to determine' because no reference range was provided in the source report.\n\n"
        "Active Record Inconsistencies:\n"
        "• Demographic discrepancy: Patient age recorded as 52 in intake vs 54 in August report.\n"
        "• Medication dosage discrepancy: Metformin recorded as 500mg twice daily in intake vs 1000mg daily in prescription record."
    )
    summary_obj = AISummary(
        patient_id=patient.id,
        reviewed_items_count=12,
        text_summary=summary_text,
        disclaimer=MEDICAL_DISCLAIMER
    )
    db.add(summary_obj)

    db.commit()
    db.refresh(patient)
    return patient
