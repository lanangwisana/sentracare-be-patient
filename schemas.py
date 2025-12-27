# sentracare-be-patient/schemas.py
from datetime import date
from pydantic import BaseModel, ConfigDict
from typing import Dict, Optional, List, Any

class MedicalRecordResponse(BaseModel):
    id: int
    patient_id: int
    doctor_username: str
    doctor_full_name: Optional[str] = None
    visit_date: Any
    visit_type: str
    diagnosis: str
    treatment: str
    prescription: Optional[str] = None
    vital_signs: Optional[Any] = None
    extended_data: Optional[Any] = None
    created_at: Any

    model_config = ConfigDict(from_attributes=True)

class PatientWithRecords(BaseModel):
    id: int
    full_name: str
    email: str
    phone_number: str
    status: str
    gender: Optional[str] = None
    age: Optional[int] = None
    address: Optional[str] = None
    tipe_layanan: Optional[str] = None
    tanggal_pemeriksaan: Optional[Any] = None
    jam_pemeriksaan: Optional[Any] = None
    booking_id: Optional[int] = None

    # Tambahan untuk dokter yang di-assign
    doctor_email: Optional[str] = None
    doctor_full_name: Optional[str] = None

    records: List[MedicalRecordResponse] = []

    model_config = ConfigDict(from_attributes=True)
    
class MedicalRecordCreate(BaseModel):
    patient_id: int
    visit_date: date
    visit_type: str
    diagnosis: str
    treatment: str
    prescription: Optional[str] = None
    vital_signs: Optional[Dict[str, Any]] = None
    extended_data: Optional[Dict[str, Any]] = None
    booking_id: Optional[int] = None
    
class PrescriptionCreate(BaseModel):
    patient_id: int
    record_id: Optional[int] = None
    medicines: List[dict]   # [{name, dosage, frequency, duration, notes}]
    instructions: Optional[str] = None
    prescription_number: Optional[str] = None

class PrescriptionResponse(BaseModel):
    id: int
    patient_id: int
    record_id: Optional[int]
    doctor_name: str
    doctor_username: str
    medicines: List[dict]
    instructions: Optional[str]
    prescription_number: Optional[str]
    created_at: str

    class Config:
        orm_mode = True
