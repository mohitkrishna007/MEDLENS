from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime

class SymptomItem(BaseModel):
    name: str
    source: str = "USER_PROVIDED"

class ConditionItem(BaseModel):
    name: str
    source: str = "USER_PROVIDED"

class AllergyItem(BaseModel):
    name: str
    source: str = "USER_PROVIDED"

class MedicationItem(BaseModel):
    name: str
    dose: Optional[str] = None
    frequency: Optional[str] = None
    source: str = "USER_PROVIDED"

class PatientCreate(BaseModel):
    patient_id_code: str
    display_name: str
    age: Optional[int] = None
    sex: Optional[str] = None
    notes: Optional[str] = None
    symptoms: List[SymptomItem] = []
    conditions: List[ConditionItem] = []
    allergies: List[AllergyItem] = []
    medications: List[MedicationItem] = []
    medical_history: Optional[str] = None

class PatientOut(BaseModel):
    id: int
    patient_id_code: str
    display_name: str
    age: Optional[int] = None
    sex: Optional[str] = None
    notes: Optional[str] = None
    symptoms: List[Any] = []
    conditions: List[Any] = []
    allergies: List[Any] = []
    medications: List[Any] = []
    medical_history: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    patient_id_code: str
    display_name: Optional[str] = None

class LabResultOut(BaseModel):
    id: int
    patient_id: int
    document_id: Optional[int] = None
    test_name: str
    value: str
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    status: str
    test_date: Optional[str] = None
    source_label: str
    source_document_name: Optional[str] = None
    confidence: str
    verification_status: str
    text_snippet: Optional[str] = None
    page_number: int

    class Config:
        from_attributes = True

class LabResultUpdate(BaseModel):
    test_name: Optional[str] = None
    value: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    test_date: Optional[str] = None
    verification_status: str = "User Verified"

class ConflictOut(BaseModel):
    id: int
    patient_id: int
    conflict_type: str
    field_name: str
    source_a_name: str
    source_a_value: str
    source_b_name: str
    source_b_value: str
    description: str
    severity: str
    status: str
    resolution_note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class TimelineEventOut(BaseModel):
    id: int
    patient_id: int
    event_type: str
    event_date: str
    title: str
    description: Optional[str] = None
    source_document_name: Optional[str] = None

    class Config:
        from_attributes = True

class DocumentOut(BaseModel):
    id: int
    patient_id: int
    filename: str
    doc_type: str
    file_size: int
    processing_status: str
    extracted_field_count: int
    uploaded_at: datetime

    class Config:
        from_attributes = True

class AISummaryOut(BaseModel):
    id: int
    patient_id: int
    reviewed_items_count: int
    text_summary: str
    disclaimer: str
    created_at: datetime

    class Config:
        from_attributes = True
