# schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List

class PatientCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone_number: str

class PatientResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone_number: str

    class Config:
        from_attributes = True

class MedicalRecordCreate(BaseModel):
    patient_id: int
    diagnosis: str
    notes: Optional[str] = None
    booking_id: Optional[int] = None

class MedicalRecordResponse(BaseModel):
    id: int
    patient_id: int
    doctor_username: str
    diagnosis: str
    notes: Optional[str] = None
    booking_id: Optional[int] = None
    created_at: str

    class Config:
        from_attributes = True

class PatientWithRecords(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone_number: str
    records: List[MedicalRecordResponse]
