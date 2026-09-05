import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import shutil
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.database import engine, get_db, Base
from backend.models import Patient, Document, LabResult, Conflict, TimelineEvent, AISummary
from backend import schemas
from backend.services.pdf_parser import extract_text_from_file
from backend.services.ai_extractor import extract_structured_data
from backend.services.range_classifier import classify_lab_result
from backend.services.conflict_detector import detect_patient_conflicts
from backend.services.ai_summary import generate_patient_summary
from backend.services.demo_data import seed_demo_patient
from backend.services.pdf_export import generate_patient_pdf
import re
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

# Ensure DB tables exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MedLens API",
    description="Evidence-backed Clinical Information Intelligence & Record Organization Platform",
    version="1.0.0"
)

# Compression Middleware for Response Efficiency
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Secure CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False, # Secure setting for wildcard origins
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# HTTP Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline' 'unsafe-eval' https: data:;"
    return response

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ----------------------------
# Health Check Endpoint
# ----------------------------
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "MedLens Clinical Intelligence API", "version": "1.0.0"}

# ----------------------------
# Authentication & Login API
# ----------------------------
@app.post("/api/auth/login")
def login_patient(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    code_clean = payload.patient_id_code.strip()
    patient = db.query(Patient).filter(Patient.patient_id_code.ilike(code_clean)).first()
    
    if not patient:
        if code_clean.upper() in ["PAT-2025-089", "JANE DOE", "DEMO", "PATIENT"]:
            patient = seed_demo_patient(db)
        elif payload.display_name and payload.display_name.strip():
            patient = Patient(
                patient_id_code=code_clean,
                display_name=payload.display_name.strip(),
                notes="Created via patient portal login."
            )
            db.add(patient)
            db.commit()
            db.refresh(patient)
            
            t_event = TimelineEvent(
                patient_id=patient.id,
                event_type="Intake",
                event_date=patient.created_at.strftime("%Y-%m-%d"),
                title="Patient Intake Registered",
                description=f"Patient portal account created for {patient.display_name}."
            )
            db.add(t_event)
            db.commit()
        else:
            raise HTTPException(status_code=404, detail=f"No patient record found for ID '{code_clean}'. Enter your Display Name below to create your intake profile.")

    return {
        "success": True,
        "message": f"Welcome back, {patient.display_name}",
        "patient": schemas.PatientOut.model_validate(patient)
    }

# ----------------------------
# Seed Demo Endpoint
# ----------------------------
@app.post("/api/demo/seed")
def seed_demo_data(db: Session = Depends(get_db)):
    patient = seed_demo_patient(db)
    
    documents = db.query(Document).filter(Document.patient_id == patient.id).all()
    lab_results = db.query(LabResult).filter(LabResult.patient_id == patient.id).all()
    conflicts = db.query(Conflict).filter(Conflict.patient_id == patient.id).all()
    timeline = db.query(TimelineEvent).filter(TimelineEvent.patient_id == patient.id).order_by(TimelineEvent.event_date.asc()).all()
    summary = db.query(AISummary).filter(AISummary.patient_id == patient.id).order_by(AISummary.created_at.desc()).first()

    return {
        "message": "Demo data successfully seeded",
        "patient_id": patient.id,
        "patient_code": patient.patient_id_code,
        "record": {
            "patient": schemas.PatientOut.model_validate(patient),
            "documents": [schemas.DocumentOut.model_validate(d) for d in documents],
            "lab_results": [schemas.LabResultOut.model_validate(l) for l in lab_results],
            "conflicts": [schemas.ConflictOut.model_validate(c) for c in conflicts],
            "timeline": [schemas.TimelineEventOut.model_validate(t) for t in timeline],
            "summary": schemas.AISummaryOut.model_validate(summary) if summary else None
        }
    }

# ----------------------------
# Patient Management
# ----------------------------
@app.get("/api/patients", response_model=List[schemas.PatientOut])
def get_patients(db: Session = Depends(get_db)):
    patients = db.query(Patient).order_by(Patient.updated_at.desc()).all()
    if not patients:
        demo = seed_demo_patient(db)
        patients = [demo]
    return patients

@app.post("/api/patients", response_model=schemas.PatientOut)
def create_patient(payload: schemas.PatientCreate, db: Session = Depends(get_db)):
    existing = db.query(Patient).filter(Patient.patient_id_code.ilike(payload.patient_id_code.strip())).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Patient ID '{payload.patient_id_code}' already exists.")
        
    patient = Patient(
        patient_id_code=payload.patient_id_code.strip(),
        display_name=payload.display_name.strip(),
        age=payload.age,
        sex=payload.sex,
        notes=payload.notes,
        symptoms=[s.model_dump() for s in payload.symptoms],
        conditions=[c.model_dump() for c in payload.conditions],
        allergies=[a.model_dump() for a in payload.allergies],
        medications=[m.model_dump() for m in payload.medications],
        medical_history=payload.medical_history
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    
    t_event = TimelineEvent(
        patient_id=patient.id,
        event_type="Intake",
        event_date=patient.created_at.strftime("%Y-%m-%d"),
        title="Patient Intake Created",
        description=f"Manual profile created for {patient.display_name}."
    )
    db.add(t_event)
    db.commit()
    
    return patient

@app.get("/api/patients/{patient_id}/record")
def get_patient_record(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        patient = db.query(Patient).filter(Patient.patient_id_code == "PAT-2025-089").first()
    if not patient:
        patient = seed_demo_patient(db)
        
    patient_id = patient.id

    documents = db.query(Document).filter(Document.patient_id == patient_id).all()
    lab_results = db.query(LabResult).filter(LabResult.patient_id == patient_id).all()
    conflicts = db.query(Conflict).filter(Conflict.patient_id == patient_id).all()
    timeline = db.query(TimelineEvent).filter(TimelineEvent.patient_id == patient_id).order_by(TimelineEvent.event_date.asc()).all()
    summary = db.query(AISummary).filter(AISummary.patient_id == patient_id).order_by(AISummary.created_at.desc()).first()

    return {
        "patient": schemas.PatientOut.model_validate(patient),
        "documents": [schemas.DocumentOut.model_validate(d) for d in documents],
        "lab_results": [schemas.LabResultOut.model_validate(l) for l in lab_results],
        "conflicts": [schemas.ConflictOut.model_validate(c) for c in conflicts],
        "timeline": [schemas.TimelineEventOut.model_validate(t) for t in timeline],
        "summary": schemas.AISummaryOut.model_validate(summary) if summary else None
    }

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".csv"}

# ----------------------------
# Document Upload & Extraction Pipeline
# ----------------------------
@app.post("/api/patients/{patient_id}/documents")
def upload_document(patient_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        patient = seed_demo_patient(db)
        patient_id = patient.id

    # Security: Sanitize filename against path traversal
    safe_filename = os.path.basename(file.filename or "document.pdf")
    safe_filename = re.sub(r"[^\w\.-]", "_", safe_filename)
    
    ext = os.path.splitext(safe_filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File format '{ext}' is not supported. Permitted extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    file_path = os.path.join(UPLOAD_DIR, f"{patient_id}_{safe_filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_path)

    extracted_text_info = extract_text_from_file(file_path)
    raw_text = extracted_text_info.get("text", "")

    doc = Document(
        patient_id=patient_id,
        filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=file.content_type or "application/pdf",
        processing_status="PROCESSING",
        page_count=extracted_text_info.get("page_count", 1),
        raw_text=raw_text
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    extracted_payload = extract_structured_data(raw_text, file.filename)
    doc.doc_type = extracted_payload.get("doc_type", "General Report")

    header_info = extracted_payload.get("header_info", {})
    if header_info.get("patient_name") and (not patient.display_name or patient.display_name in ["Jane Doe", "New Patient", "Patient", ""]):
        patient.display_name = header_info["patient_name"]
    if header_info.get("age"):
        patient.age = header_info["age"]
    if header_info.get("sex"):
        patient.sex = header_info["sex"]

    extracted_labs = extracted_payload.get("lab_results", [])
    doc.extracted_field_count = len(extracted_labs)
    
    for l_data in extracted_labs:
        lab_obj = LabResult(
            patient_id=patient_id,
            document_id=doc.id,
            test_name=l_data.get("test_name", "Lab Test"),
            value=str(l_data.get("value", "")),
            numeric_value=l_data.get("numeric_value"),
            unit=l_data.get("unit"),
            reference_range=l_data.get("reference_range", "Not provided in source"),
            status=l_data.get("status", "UNKNOWN"),
            test_date=l_data.get("test_date") or doc.uploaded_at.strftime("%Y-%m-%d"),
            source_label="AI EXTRACTED",
            source_document_name=file.filename,
            confidence=l_data.get("confidence", "High"),
            verification_status="AI Extracted",
            text_snippet=l_data.get("text_snippet"),
            page_number=l_data.get("page_number", 1)
        )
        db.add(lab_obj)

    doc.processing_status = "PROCESSED"
    db.commit()

    report_date = extracted_payload.get("header_info", {}).get("report_date") or doc.uploaded_at.strftime("%Y-%m-%d")
    t_event = TimelineEvent(
        patient_id=patient_id,
        event_type="Report Upload",
        event_date=report_date,
        title=f"Uploaded {file.filename}",
        description=f"Extracted {len(extracted_labs)} test results from {doc.doc_type}.",
        source_document_id=doc.id,
        source_document_name=file.filename
    )
    db.add(t_event)

    db.refresh(patient)
    new_conflicts = detect_patient_conflicts(patient, db)
    for c_item in new_conflicts:
        dup = db.query(Conflict).filter(
            Conflict.patient_id == patient_id,
            Conflict.field_name == c_item["field_name"],
            Conflict.source_a_value == c_item["source_a_value"],
            Conflict.source_b_value == c_item["source_b_value"]
        ).first()
        if not dup:
            c_obj = Conflict(**c_item)
            db.add(c_obj)

    db.commit()
    db.refresh(patient)
    summary_data = generate_patient_summary(patient)
    sum_obj = AISummary(
        patient_id=patient_id,
        reviewed_items_count=summary_data["reviewed_items_count"],
        text_summary=summary_data["summary_text"],
        disclaimer=summary_data["disclaimer"]
    )
    db.add(sum_obj)
    db.commit()

    return {"message": "Document processed successfully", "document_id": doc.id, "extracted_count": len(extracted_labs)}

# ----------------------------
# Human-in-the-Loop Verification
# ----------------------------
@app.patch("/api/lab-results/{result_id}")
def update_lab_result(result_id: int, payload: schemas.LabResultUpdate, db: Session = Depends(get_db)):
    result = db.query(LabResult).filter(LabResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Lab result not found.")

    if payload.test_name is not None:
        result.test_name = payload.test_name
    if payload.value is not None:
        result.value = payload.value
    if payload.unit is not None:
        result.unit = payload.unit
    if payload.reference_range is not None:
        result.reference_range = payload.reference_range
    if payload.test_date is not None:
        result.test_date = payload.test_date

    status, num_val = classify_lab_result(result.value, result.reference_range)
    result.status = status
    result.numeric_value = num_val
    result.verification_status = payload.verification_status

    db.commit()
    db.refresh(result)
    return result

# ----------------------------
# Conflict Resolution
# ----------------------------
@app.post("/api/patients/{patient_id}/conflicts/{conflict_id}/resolve")
def resolve_conflict(patient_id: int, conflict_id: int, resolution_note: Optional[str] = Form(None), db: Session = Depends(get_db)):
    conflict = db.query(Conflict).filter(Conflict.id == conflict_id, Conflict.patient_id == patient_id).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found.")
        
    conflict.status = "Resolved"
    conflict.resolution_note = resolution_note or "Marked resolved by user."
    db.commit()
    return {"message": "Conflict resolved", "conflict_id": conflict_id}

# ----------------------------
# Longitudinal Trends API
# ----------------------------
@app.get("/api/patients/{patient_id}/trends")
def get_longitudinal_trends(patient_id: int, db: Session = Depends(get_db)):
    labs = db.query(LabResult).filter(LabResult.patient_id == patient_id).order_by(LabResult.test_date.asc()).all()
    if not labs:
        patient = seed_demo_patient(db)
        labs = db.query(LabResult).filter(LabResult.patient_id == patient.id).order_by(LabResult.test_date.asc()).all()

    grouped = {}
    for l in labs:
        test = l.test_name.strip()
        if test not in grouped:
            grouped[test] = []
        grouped[test].append({
            "id": l.id,
            "date": l.test_date or "Unknown Date",
            "value": l.value,
            "numeric_value": l.numeric_value,
            "unit": l.unit or "",
            "reference_range": l.reference_range or "Not provided",
            "status": l.status,
            "source": l.source_document_name or "Source Document"
        })
    return grouped

# ----------------------------
# PDF Export Endpoint
# ----------------------------
@app.get("/api/patients/{patient_id}/export")
def export_patient_pdf(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        patient = seed_demo_patient(db)
        
    pdf_bytes = generate_patient_pdf(patient)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=MedLens_Record_{patient.patient_id_code}.pdf"}
    )

# ----------------------------
# Static Files & Frontend SPA Mount
# ----------------------------
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)
