# schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any

class PatientCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone_number: str
    status: Optional[str] = "Active"

class PatientResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone_number: str
    status: Optional[str] = "Active"

    class Config:
        from_attributes = True

class MedicalRecordCreate(BaseModel):
    patient_id: int
    visit_date: str
    visit_type: str
    diagnosis: str
    treatment: str
    prescription: Optional[str] = None
    vital_signs: Optional[Dict[str, Any]] = None
    booking_id: Optional[int] = None
    extended_data: Optional[Dict[str, Any]] = None

class MedicalRecordResponse(BaseModel):
    id: int
    patient_id: int
    doctor_username: str
    visit_date: str
    visit_type: str
    diagnosis: str
    treatment: str
    prescription: Optional[str] = None
    vital_signs: Optional[Dict[str, Any]] = None
    booking_id: Optional[int] = None
    extended_data: Optional[Dict[str, Any]] = None
    created_at: str

    class Config:
        from_attributes = True

class PatientWithRecords(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone_number: str
    status: Optional[str] = "Active"
    last_visit: Optional[str] = None
    records: List[MedicalRecordResponse]
