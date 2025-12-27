# sentracare-be-patient/graphql_schema.py
from datetime import date, datetime
import strawberry
from typing import List, Optional, Dict, Any
from strawberry.fastapi import GraphQLRouter
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Patient, MedicalRecord, Prescription

# Definisi JSON Scalar
JSON = strawberry.scalar( 
    dict, 
    description="Generic JSON object", 
    serialize=lambda v: v, 
    parse_value=lambda v: v, 
)

@strawberry.type
class VitalSignsType:
    blood_pressure: Optional[str] = None
    heart_rate: Optional[str] = None
    temperature: Optional[str] = None
    weight: Optional[str] = None
    height: Optional[str] = None

@strawberry.type
class MedicalRecordType:
    id: int
    patient_id: int
    doctor_username: str
    doctor_full_name: Optional[str] = None
    visit_date: str # Akan muncul sebagai visitDate di frontend
    visit_type: str # Akan muncul sebagai visitType di frontend
    diagnosis: str
    treatment: str
    vital_signs: Optional[VitalSignsType] = None # Akan muncul sebagai vitalSigns
    booking_id: Optional[int] = None
    extended_data: Optional[JSON] = None # type: ignore
    created_at: str

@strawberry.type
class BookingInfoType:
    tipe_layanan: Optional[str] = None
    tanggal_pemeriksaan: Optional[str] = None
    jam_pemeriksaan: Optional[str] = None

@strawberry.type
class PrescriptionType:
    id: int 
    record_id: Optional[int] = None 
    patient_id: int 
    doctor_name: str 
    doctor_username: str 
    prescription_number: Optional[str] = None 
    medicines: Optional[JSON] = None  # type: ignore
    instructions: Optional[str] = None 
    created_at: str

@strawberry.type
class PatientType:
    id: int
    full_name: str
    email: str
    phone_number: str
    status: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    tipe_layanan: Optional[str] = None
    records: List[MedicalRecordType]
    prescriptions: List[PrescriptionType]

# --- Helper Functions ---
def to_record_type(r: MedicalRecord) -> MedicalRecordType:
    vs = r.vital_signs or {}
    vital_signs = VitalSignsType(
        blood_pressure=vs.get("blood_pressure"),
        heart_rate=vs.get("heart_rate"),
        temperature=vs.get("temperature"),
        weight=vs.get("weight"),
        height=vs.get("height"),
    )
    
    return MedicalRecordType(
        id=r.id,
        patient_id=r.patient_id,
        doctor_username=r.doctor_username,
        doctor_full_name=r.doctor_full_name,
        visit_date=r.visit_date.isoformat() if r.visit_date else "",
        visit_type=r.visit_type,
        diagnosis=r.diagnosis,
        treatment=r.treatment,
        vital_signs=vital_signs,
        booking_id=r.booking_id,
        extended_data=r.extended_data,
        created_at=r.created_at.isoformat() if r.created_at else "",
    )

def to_prescription_type(p: Prescription) -> PrescriptionType:
    return PrescriptionType(
        id=p.id, 
        record_id=p.record_id, 
        patient_id=p.patient_id, 
        doctor_name=p.doctor_name, 
        doctor_username=p.doctor_username, 
        prescription_number=p.prescription_number, 
        medicines=p.medicines, 
        instructions=p.instructions, 
        created_at=p.created_at.isoformat() if p.created_at else ""
    )

def to_patient_type(p: Patient) -> PatientType:
    return PatientType(
        id=p.id,
        full_name=p.full_name,
        email=p.email,
        phone_number=p.phone_number,
        status=p.status,
        gender=p.gender,
        age=p.age,
        tipe_layanan=p.tipe_layanan,
        records=[to_record_type(r) for r in sorted(p.records, key=lambda x: x.visit_date, reverse=True)],
        prescriptions=[to_prescription_type(pr) for pr in p.prescriptions],
    )
@strawberry.type
class Query:
    @strawberry.field
    def patient_by_email(self, info, email: str) -> Optional[PatientType]:
        db: Session = info.context["db"]
        p = db.query(Patient).filter(Patient.email == email).first()
        return to_patient_type(p) if p else None

    @strawberry.field
    def patients_by_doctor(self, info, doctor_email: str) -> List[PatientType]:
        db: Session = info.context["db"]
        patients = db.query(Patient).filter(Patient.doctor_email == doctor_email).all()
        return [to_patient_type(p) for p in patients]

@strawberry.type
class Mutation:
    @strawberry.field
    def delete_record(self, info, record_id: int) -> str:
        db: Session = info.context["db"]
        record = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
        if record:
            db.delete(record)
            db.commit()
            return "Success"
        return "Not Found"

schema = strawberry.Schema(query=Query, mutation=Mutation)

async def get_context():
    db = SessionLocal()
    return {"db": db}

graphql_app = GraphQLRouter(schema, context_getter=get_context)