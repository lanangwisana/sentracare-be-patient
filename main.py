# main.py
from datetime import date
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal
from models import Patient, MedicalRecord
from schemas import (
    PatientCreate,
    PatientResponse,
    MedicalRecordCreate,
    MedicalRecordResponse,
    PatientWithRecords,
)
from graphql_schema import graphql_app
from auth import require_role

app = FastAPI(
    title="Sentracare Patient Service",
    description="API untuk rekam medis elektronik dan data pasien",
    version="1.0.0",
)

# GraphQL router
app.include_router(graphql_app, prefix="/graphql")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000",
        "http://host.docker.internal:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin"],
)

# DB init
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- REST minimal ---

@app.post("/patients", response_model=PatientResponse, tags=["patients"])
def create_patient(
    data: PatientCreate,
    db: Session = Depends(get_db),
    _claims: dict = Depends(require_role(["Dokter", "SuperAdmin"]))
):
    exists = db.query(Patient).filter(Patient.email == data.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Patient already exists")
    p = Patient(
        full_name=data.full_name,
        email=data.email,
        phone_number=data.phone_number,
        status=data.status,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p

@app.get("/patients/{patient_id}", response_model=PatientWithRecords, tags=["patients"])
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    _claims: dict = Depends(require_role(["Dokter", "SuperAdmin"]))
):
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")

    records = [
        MedicalRecordResponse(
            id=r.id,
            patient_id=r.patient_id,
            doctor_username=r.doctor_username,
            visit_date=r.visit_date.isoformat(),
            visit_type=r.visit_type,
            diagnosis=r.diagnosis,
            treatment=r.treatment,
            prescription=r.prescription,
            vital_signs=r.vital_signs,
            extended_data=r.extended_data,
            booking_id=r.booking_id,
            created_at=r.created_at.isoformat(),
        )
        for r in p.records
    ]
    last_visit = max((r.visit_date for r in p.records), default=None)
    return {
        "id": p.id,
        "full_name": p.full_name,
        "email": p.email,
        "phone_number": p.phone_number,
        "status": p.status,
        "last_visit": last_visit.isoformat() if last_visit else None,
        "records": records,
    }

@app.post("/records", response_model=MedicalRecordResponse, tags=["records"])
def add_record(
    data: MedicalRecordCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(require_role(["Dokter", "SuperAdmin"]))
):
    doctor_username = claims.get("sub")
    if not doctor_username:
        raise HTTPException(status_code=401, detail="Invalid token: subject missing")

    patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    try:
        visit_date = date.fromisoformat(data.visit_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="visit_date must be ISO format YYYY-MM-DD")

    r = MedicalRecord(
        patient_id=data.patient_id,
        booking_id=data.booking_id,
        doctor_username=doctor_username,
        visit_date=visit_date,
        visit_type=data.visit_type,
        diagnosis=data.diagnosis,
        treatment=data.treatment,
        prescription=data.prescription,
        vital_signs=data.vital_signs,
        extended_data=data.extended_data,
    )
    db.add(r)
    db.commit()
    db.refresh(r)

    return MedicalRecordResponse(
        id=r.id,
        patient_id=r.patient_id,
        doctor_username=r.doctor_username,
        visit_date=r.visit_date.isoformat(),
        visit_type=r.visit_type,
        diagnosis=r.diagnosis,
        treatment=r.treatment,
        prescription=r.prescription,
        vital_signs=r.vital_signs,
        booking_id=r.booking_id,
        extended_data=r.extended_data,
        created_at=r.created_at.isoformat(),
    )
