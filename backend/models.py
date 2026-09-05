from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_id_code = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=False)
    age = Column(Integer, nullable=True)
    sex = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Manual Intake Fields (User Provided)
    symptoms = Column(JSON, default=list)        # list of dicts: {"name": ..., "source": "USER_PROVIDED"}
    conditions = Column(JSON, default=list)      # list of dicts: {"name": ..., "source": "USER_PROVIDED"}
    allergies = Column(JSON, default=list)       # list of dicts: {"name": ..., "source": "USER_PROVIDED"}
    medications = Column(JSON, default=list)     # list of dicts: {"name": ..., "dose": ..., "source": "USER_PROVIDED"}
    medical_history = Column(Text, nullable=True)

    # Relationships
    documents = relationship("Document", back_populates="patient", cascade="all, delete-orphan")
    lab_results = relationship("LabResult", back_populates="patient", cascade="all, delete-orphan")
    conflicts = relationship("Conflict", back_populates="patient", cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEvent", back_populates="patient", cascade="all, delete-orphan")
    summaries = relationship("AISummary", back_populates="patient", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    doc_type = Column(String, default="General Report") # e.g. Blood Test, Prescription, Summary
    file_size = Column(Integer, default=0)
    mime_type = Column(String, default="application/pdf")
    processing_status = Column(String, default="PENDING") # PENDING, PROCESSED, FAILED
    page_count = Column(Integer, default=1)
    extracted_field_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    raw_text = Column(Text, nullable=True)

    patient = relationship("Patient", back_populates="documents")
    lab_results = relationship("LabResult", back_populates="document", cascade="all, delete-orphan")

class LabResult(Base):
    __tablename__ = "lab_results"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    test_name = Column(String, index=True, nullable=False)
    value = Column(String, nullable=False)          # Original text value e.g. "11.2", "> 5.0", "Negative"
    numeric_value = Column(Float, nullable=True)    # Extracted float for charting if possible
    unit = Column(String, nullable=True)            # e.g. "g/dL", "mg/dL"
    reference_range = Column(String, nullable=True) # Source provided exact string e.g. "12.0 - 15.5" or None
    status = Column(String, default="UNKNOWN")      # LOW, NORMAL, HIGH, UNKNOWN
    test_date = Column(String, nullable=True)       # ISO format YYYY-MM-DD or readable
    source_label = Column(String, default="AI EXTRACTED") # USER PROVIDED, AI EXTRACTED, DOCUMENT SOURCE
    source_document_name = Column(String, nullable=True)
    confidence = Column(String, default="High")     # High, Medium, Low
    verification_status = Column(String, default="AI Extracted") # AI Extracted, User Verified, User Edited
    text_snippet = Column(Text, nullable=True)      # Original snippet from OCR/PDF for side-by-side view
    page_number = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="lab_results")
    document = relationship("Document", back_populates="lab_results")

class Conflict(Base):
    __tablename__ = "conflicts"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    conflict_type = Column(String, nullable=False) # Demographic, Medication, Lab Result, Date, Allergy
    field_name = Column(String, nullable=False)
    source_a_name = Column(String, nullable=False)
    source_a_value = Column(String, nullable=False)
    source_b_name = Column(String, nullable=False)
    source_b_value = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String, default="MEDIUM") # HIGH, MEDIUM, LOW
    status = Column(String, default="Unresolved") # Unresolved, Resolved
    resolution_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="conflicts")

class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    event_type = Column(String, nullable=False) # Report Upload, Lab Test, Prescription, Condition, Intake
    event_date = Column(String, nullable=False) # YYYY-MM-DD
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    source_document_id = Column(Integer, nullable=True)
    source_document_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="timeline_events")

class AISummary(Base):
    __tablename__ = "ai_summaries"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    reviewed_items_count = Column(Integer, default=0)
    text_summary = Column(Text, nullable=False)
    disclaimer = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="summaries")
