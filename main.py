# sentracare-be-patient/main.py
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import httpx
from database import engine, SessionLocal, Base
from models import MedicalRecord, Patient
from schemas import PatientWithRecords
from auth import require_role
from schemas import MedicalRecordCreate, MedicalRecordResponse

Base.metadata.create_all(bind=engine)

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# === Endpoint internal untuk menerima push dari Booking Service ===
@app.post("/patients/internal-register")
async def internal_register(patient: dict, db: Session = Depends(get_db)):
    try:
        existing = db.query(Patient).filter(Patient.booking_id == patient.get("booking_id")).first()
        if existing:
            return {"message": "Pasien sudah terdaftar", "patient_id": existing.id}

        tgl = None
        if patient.get("tanggal_pemeriksaan"):
            try:
                tgl = datetime.strptime(patient.get("tanggal_pemeriksaan"), "%Y-%m-%d").date()
            except Exception:
                pass

        new_patient = Patient(
            full_name=patient.get("full_name"),
            email=patient.get("email"),
            phone_number=patient.get("phone_number") or "-",
            gender=patient.get("gender") or "Laki-laki",
            age=patient.get("age") or 0,
            address=patient.get("address") or "-",
            status="Active",
            tipe_layanan=patient.get("tipe_layanan"),
            tanggal_pemeriksaan=tgl,
            jam_pemeriksaan=patient.get("jam_pemeriksaan"),
            booking_id=patient.get("booking_id"),
            doctor_email=patient.get("doctor_email"),
            doctor_full_name=patient.get("doctor_name"),
        )
        db.add(new_patient)
        db.commit()
        db.refresh(new_patient)
        return {"message": "Pasien berhasil diregister", "patient_id": new_patient.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# === Endpoint untuk list pasien sesuai dokter login ===
@app.get("/patients", response_model=List[PatientWithRecords])
def list_patients(
    db: Session = Depends(get_db),
    claims: dict = Depends(require_role(["Dokter", "SuperAdmin"]))
):
    query = db.query(Patient)
    if claims.get("role") == "Dokter":
        query = query.filter(Patient.doctor_email == claims.get("email"))
    patients = query.all()
    return patients

# === Endpoint detail pasien berdasarkan email ===
@app.get("/patients/{email}", response_model=PatientWithRecords)
def get_patient(
    email: str,
    db: Session = Depends(get_db),
    claims: dict = Depends(require_role(["Dokter", "SuperAdmin"]))
):
    query = db.query(Patient)
    if claims.get("role") == "Dokter":
        query = query.filter(Patient.doctor_email == claims.get("email"))
    patient = query.filter(Patient.email == email).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Pasien tidak ditemukan")
    return patient

# === Endpoint sinkronisasi fallback dari Booking Service ===
@app.post("/patients/sync-from-booking")
async def sync_patients_from_booking(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(require_role(["Dokter", "SuperAdmin"]))
):
    active_doctor = claims.get("full_name")
    auth_header = request.headers.get("Authorization")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "http://host.docker.internal:8001/api/bookings/emr-patients",
                headers={"Authorization": auth_header},
                timeout=10
            )
            all_bookings = response.json()
        except Exception:
            raise HTTPException(status_code=500, detail="Gagal kontak Booking Service")

    synced_count = 0
    for b in all_bookings:
        if b.get("doctorName") == active_doctor or claims.get("role") == "SuperAdmin":
            existing_entry = db.query(Patient).filter(Patient.booking_id == b.get("id")).first()
            if not existing_entry:
                tgl = None
                if b.get("tanggalPemeriksaan"):
                    tgl = datetime.strptime(b.get("tanggalPemeriksaan"), "%Y-%m-%d").date()
                new_patient = Patient(
                    full_name=b.get("full_name"),
                    email=b.get("email"),
                    phone_number=b.get("phone_number") or "-",
                    gender=b.get("gender") or "Laki-laki",
                    age=b.get("age") or 0,
                    address=b.get("alamat") or "-",
                    status="Active",
                    tipe_layanan=b.get("tipeLayanan"),
                    tanggal_pemeriksaan=tgl,
                    jam_pemeriksaan=b.get("jamPemeriksaan"),
                    booking_id=b.get("id"),
                    doctor_email=b.get("doctor_email"),
                    doctor_full_name=b.get("doctorName"),
                )
                db.add(new_patient)
                synced_count += 1

    db.commit()
    return {"message": f"Berhasil sinkronisasi {synced_count} antrean pasien"}

@app.post("/records", response_model=MedicalRecordResponse)
def add_record(
    data: MedicalRecordCreate, 
    db: Session = Depends(get_db), 
    claims: dict = Depends(require_role(["Dokter"]))
):
    # Ambil info dokter dari token JWT
    doctor_username = claims.get("sub")
    doctor_full_name = claims.get("full_name")
    
    new_record = MedicalRecord(
        patient_id=data.patient_id,
        booking_id=data.booking_id,
        doctor_username=doctor_username,
        doctor_full_name=doctor_full_name,
        visit_date=data.visit_date,
        visit_type=data.visit_type,
        diagnosis=data.diagnosis,
        treatment=data.treatment,
        prescription=data.prescription,
        vital_signs=data.vital_signs,
        extended_data=data.extended_data
    )
    
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record











