# graphql_schema.py
from datetime import date
import strawberry
from typing import List, Optional, Dict, Any
from strawberry.fastapi import GraphQLRouter
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Patient, MedicalRecord

JSON = strawberry.scalar( 
        dict, description="Generic JSON object", 
        serialize=lambda v: v, 
        parse_value=lambda v: v, 
    )
@strawberry.type
class VitalSignsType:
    blood_pressure: Optional[str]
    heart_rate: Optional[str]
    temperature: Optional[str]
    weight: Optional[str]
    height: Optional[str]

@strawberry.type
class MedicalRecordType:
    id: int
    patient_id: int
    doctor_username: str
    visit_date: str
    visit_type: str
    diagnosis: str
    treatment: str
    prescription: Optional[str]
    vital_signs: Optional[VitalSignsType]
    booking_id: Optional[int]
    extended_data: Optional[JSON] = None
    created_at: str

@strawberry.type
class PatientType:
    id: int
    full_name: str
    email: str
    phone_number: str
    status: Optional[str]
    blood_type: Optional[str]
    gender: Optional[str]
    allergies: Optional[str]
    emergency_contact: Optional[str]
    address: Optional[str]
    birth_date: Optional[str]
    age: Optional[int]
    last_visit: Optional[str]
    records: List[MedicalRecordType]

def to_record_type(r: MedicalRecord) -> MedicalRecordType:
    vital_signs = None 
    if r.vital_signs: 
      vital_signs = VitalSignsType( 
        blood_pressure=r.vital_signs.get("blood_pressure"), 
        heart_rate=r.vital_signs.get("heart_rate"), 
        temperature=r.vital_signs.get("temperature"), 
        weight=r.vital_signs.get("weight"), 
        height=r.vital_signs.get("height"), 
        )
    return MedicalRecordType(
        id=r.id,
        patient_id=r.patient_id,
        doctor_username=r.doctor_username,
        visit_date=r.visit_date.isoformat(),
        visit_type=r.visit_type,
        diagnosis=r.diagnosis,
        treatment=r.treatment,
        prescription=r.prescription,
        vital_signs=vital_signs,
        booking_id=r.booking_id,
        extended_data=r.extended_data,
        created_at=r.created_at.isoformat(),
    )

def to_patient_type(p: Patient) -> PatientType:
    last_visit = max((r.visit_date for r in p.records), default=None)
    age = None
    if p.birth_date:
        age = (date.today() - p.birth_date).days // 365
    return PatientType(
        id=p.id,
        full_name=p.full_name,
        email=p.email,
        phone_number=p.phone_number,
        status=p.status,
        blood_type=p.blood_type,
        gender=p.gender,
        allergies=p.allergies,
        emergency_contact=p.emergency_contact,
        address=p.address,
        birth_date=p.birth_date.isoformat() if p.birth_date else None,
        age=age,
        last_visit=last_visit.isoformat() if last_visit else None,
        records=[to_record_type(r) for r in p.records],
    )

@strawberry.type
class Query:
    @strawberry.field
    def patients_by_doctor(self, info, doctor_username: str) -> List[PatientType]:
        db: Session = info.context["db"]
        patients = (
            db.query(Patient)
            .join(MedicalRecord)
            .filter(MedicalRecord.doctor_username == doctor_username)
            .all()
        )
        return [to_patient_type(p) for p in patients]

    @strawberry.field
    def patient_by_email(self, info, email: str) -> Optional[PatientType]:
        db: Session = info.context["db"]
        p = db.query(Patient).filter(Patient.email == email).first()
        return to_patient_type(p) if p else None

@strawberry.type
class Mutation:
    @strawberry.field
    def upsert_patient(
        self,
        info,
        full_name: str,
        email: str,
        phone_number: str,
        status: Optional[str] = "Active",
    ) -> PatientType:
        db: Session = info.context["db"]
        p = db.query(Patient).filter(Patient.email == email).first()
        if p:
            p.full_name = full_name
            p.phone_number = phone_number
            p.status = status
        else:
            p = Patient(full_name=full_name, email=email, phone_number=phone_number, status=status)
            db.add(p)
        db.commit()
        db.refresh(p)
        return to_patient_type(p)

    @strawberry.field
    def add_medical_record(
        self,
        info,
        patient_id: int,
        doctor_username: str,
        visit_date: str,
        visit_type: str,
        diagnosis: str,
        treatment: str,
        prescription: Optional[str] = None,
        vital_signs: Optional[JSON] = None,
        extended_data: Optional[JSON] = None,
        booking_id: Optional[int] = None,
    ) -> MedicalRecordType:
        db: Session = info.context["db"]
        record = MedicalRecord(
            patient_id=patient_id,
            doctor_username=doctor_username,
            visit_date=date.fromisoformat(visit_date),
            visit_type=visit_type,
            diagnosis=diagnosis,
            treatment=treatment,
            prescription=prescription,
            vital_signs=vital_signs,
            extended_data=extended_data,
            booking_id=booking_id,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return to_record_type(record)

schema = strawberry.Schema(query=Query, mutation=Mutation)

def get_context():
    db = SessionLocal()
    return {"db": db}

graphql_app = GraphQLRouter(schema, context_getter=get_context)
