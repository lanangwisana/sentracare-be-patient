# graphql_schema.py
from datetime import date, datetime
import strawberry
from typing import List, Optional, Dict, Any
from strawberry.fastapi import GraphQLRouter
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Patient, MedicalRecord
import json

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
class BookingInfoType:
    tipe_layanan: Optional[str] = None
    tanggal_pemeriksaan: Optional[str] = None
    jam_pemeriksaan: Optional[str] = None
    dokter_nama: Optional[str] = None

@strawberry.type
class MedicalRecordType:
    id: int
    patient_id: int
    doctor_username: str
    doctor_full_name: Optional[str] = None
    visit_date: str
    visit_type: str
    diagnosis: str
    treatment: str
    prescription: Optional[str] = None
    vital_signs: Optional[VitalSignsType] = None
    booking_id: Optional[int] = None
    extended_data: Optional[JSON] = None
    created_at: str
    updated_at: Optional[str] = None

@strawberry.type
class PatientType:
    id: int
    full_name: str
    email: str
    phone_number: str
    status: Optional[str] = None
    blood_type: Optional[str] = None
    gender: Optional[str] = None
    allergies: Optional[str] = None
    emergency_contact: Optional[str] = None
    address: Optional[str] = None
    age: Optional[int] = None
    last_visit: Optional[str] = None
    records_count: Optional[int] = 0
    booking: Optional[BookingInfoType] = None
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
        doctor_full_name=r.doctor_full_name,
        visit_date=r.visit_date.isoformat(),
        visit_type=r.visit_type,
        diagnosis=r.diagnosis,
        treatment=r.treatment,
        prescription=r.prescription,
        vital_signs=vital_signs,
        booking_id=r.booking_id,
        extended_data=r.extended_data,
        created_at=r.created_at.isoformat(),
        updated_at=r.updated_at.isoformat() if r.updated_at else None,
    )

def to_patient_type(p: Patient) -> PatientType:
    last_visit = max((r.visit_date for r in p.records), default=None)
    
    # Hitung usia jika ada birth_date
    age = p.age
    if not age and p.birth_date:
        age = (date.today() - p.birth_date).days // 365
    
    # Booking info
    booking_info = None
    if p.tipe_layanan:
        booking_info = BookingInfoType(
            tipe_layanan=p.tipe_layanan,
            tanggal_pemeriksaan=p.tanggal_pemeriksaan.isoformat() if p.tanggal_pemeriksaan else None,
            jam_pemeriksaan=p.jam_pemeriksaan,
        )
    
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
        age=age,
        last_visit=last_visit.isoformat() if last_visit else None,
        records_count=len(p.records),
        booking=booking_info,
        records=[to_record_type(r) for r in p.records],
    )

@strawberry.type
class Query:
    @strawberry.field
    def patients_by_doctor(self, doctor_username: str) -> List[PatientType]:
        """Get patients assigned to a specific doctor"""
        db: Session = next(get_db())
        patients = (
            db.query(Patient)
            .join(MedicalRecord)
            .filter(MedicalRecord.doctor_username == doctor_username)
            .distinct()
            .all()
        )
        return [to_patient_type(p) for p in patients]

    @strawberry.field
    def patient_by_email(self, email: str) -> Optional[PatientType]:
        """Get patient by email"""
        db: Session = next(get_db())
        p = db.query(Patient).filter(Patient.email == email).first()
        return to_patient_type(p) if p else None

    @strawberry.field
    def patient_by_id(self, patient_id: int) -> Optional[PatientType]:
        """Get patient by ID"""
        db: Session = next(get_db())
        p = db.query(Patient).filter(Patient.id == patient_id).first()
        return to_patient_type(p) if p else None

    @strawberry.field
    def search_patients(
        self, 
        search_term: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[PatientType]:
        """Search patients with filters"""
        db: Session = next(get_db())
        query = db.query(Patient)
        
        if search_term:
            query = query.filter(
                (Patient.full_name.ilike(f"%{search_term}%")) |
                (Patient.email.ilike(f"%{search_term}%")) |
                (Patient.phone_number.ilike(f"%{search_term}%"))
            )
        
        if status and status != "all":
            query = query.filter(Patient.status == status)
        
        patients = query.all()
        return [to_patient_type(p) for p in patients]

    @strawberry.field
    def patient_stats(self, doctor_username: Optional[str] = None) -> JSON:
        """Get patient statistics"""
        db: Session = next(get_db())
        
        query = db.query(Patient)
        if doctor_username:
            query = query.join(MedicalRecord).filter(MedicalRecord.doctor_username == doctor_username)
        
        total = query.count()
        active = query.filter(Patient.status == "Active").count()
        follow_up = query.filter(Patient.status == "Follow-up").count()
        
        # Count new this month
        current_month = date.today().month
        current_year = date.today().year
        new_this_month = 0
        
        all_patients = query.all()
        for patient in all_patients:
            if patient.records:
                last_record = max(patient.records, key=lambda r: r.visit_date)
                if (last_record.visit_date.month == current_month and 
                    last_record.visit_date.year == current_year):
                    new_this_month += 1
        
        return {
            "total": total,
            "active": active,
            "follow_up": follow_up,
            "new_this_month": new_this_month
        }

@strawberry.type
class Mutation:
    @strawberry.field
    def upsert_patient(
        self,
        full_name: str,
        email: str,
        phone_number: str,
        status: Optional[str] = "Active",
        blood_type: Optional[str] = None,
        gender: Optional[str] = None,
        allergies: Optional[str] = None,
        emergency_contact: Optional[str] = None,
        address: Optional[str] = None,
        birth_date: Optional[str] = None,
        age: Optional[int] = None,
        booking_id: Optional[int] = None,
        tipe_layanan: Optional[str] = None,
        tanggal_pemeriksaan: Optional[str] = None,
        jam_pemeriksaan: Optional[str] = None,
    ) -> PatientType:
        """Create or update patient"""
        db: Session = next(get_db())
        
        # Parse dates
        birth_date_obj = None
        if birth_date:
            try:
                birth_date_obj = date.fromisoformat(birth_date)
            except ValueError:
                pass
        
        tanggal_pemeriksaan_obj = None
        if tanggal_pemeriksaan:
            try:
                tanggal_pemeriksaan_obj = date.fromisoformat(tanggal_pemeriksaan)
            except ValueError:
                pass
        
        p = db.query(Patient).filter(Patient.email == email).first()
        if p:
            # Update existing
            p.full_name = full_name
            p.phone_number = phone_number
            p.status = status
            p.blood_type = blood_type
            p.gender = gender
            p.allergies = allergies
            p.emergency_contact = emergency_contact
            p.address = address
            p.birth_date = birth_date_obj
            p.age = age
            p.booking_id = booking_id
            p.tipe_layanan = tipe_layanan
            p.tanggal_pemeriksaan = tanggal_pemeriksaan_obj
            p.jam_pemeriksaan = jam_pemeriksaan
        else:
            # Create new
            p = Patient(
                full_name=full_name,
                email=email,
                phone_number=phone_number,
                status=status,
                blood_type=blood_type,
                gender=gender,
                allergies=allergies,
                emergency_contact=emergency_contact,
                address=address,
                birth_date=birth_date_obj,
                age=age,
                booking_id=booking_id,
                tipe_layanan=tipe_layanan,
                tanggal_pemeriksaan=tanggal_pemeriksaan_obj,
                jam_pemeriksaan=jam_pemeriksaan,
            )
            db.add(p)
        
        db.commit()
        db.refresh(p)
        return to_patient_type(p)

    @strawberry.field
    def add_medical_record(
        self,
        patient_id: int,
        doctor_username: str,
        visit_date: str,
        visit_type: str,
        diagnosis: str,
        treatment: str,
        doctor_full_name: Optional[str] = None,
        prescription: Optional[str] = None,
        vital_signs: Optional[JSON] = None,
        extended_data: Optional[JSON] = None,
        booking_id: Optional[int] = None,
    ) -> MedicalRecordType:
        """Add new medical record"""
        db: Session = next(get_db())
        
        # Verify patient exists
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise Exception("Patient not found")
        
        record = MedicalRecord(
            patient_id=patient_id,
            doctor_username=doctor_username,
            doctor_full_name=doctor_full_name,
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
        
        # Update patient's last visit date in booking info
        if not patient.tanggal_pemeriksaan or date.fromisoformat(visit_date) > patient.tanggal_pemeriksaan:
            patient.tanggal_pemeriksaan = date.fromisoformat(visit_date)
            db.commit()
        
        return to_record_type(record)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

schema = strawberry.Schema(query=Query, mutation=Mutation)

def get_context():
    db = SessionLocal()
    return {"db": db}

graphql_app = GraphQLRouter(schema, context_getter=get_context)