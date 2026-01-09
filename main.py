# sentracare-be-patient/main.py
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
import httpx
from database import engine, SessionLocal, Base
from models import MedicalRecord, Patient, Prescription
from schemas import PatientWithRecords, PrescriptionCreate, PrescriptionResponse
from auth import require_role
from schemas import MedicalRecordCreate, MedicalRecordResponse
from graphql_schema import graphql_app 

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sentracare Patient Service",
    description="API untuk management rekam medis dan resep obat di SentraCare", 
    version="1.0.0"
)

# CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# === Router GraphQL ===
app.include_router(
    graphql_app, 
    prefix="/patients/graphql",
    tags=["GraphQL"],)

# === Endpoint internal untuk menerima push dari Booking Service ===
@app.post("/patients/internal-register",
    tags=["Patient"],
    summary="Internal Register Pasien",
    description="Endpoint internal untuk mendaftarkan pasien dari Booking Service")
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
@app.get(
    "/patients/patients-list", 
    tags=["Patient"],
    summary="List Pasien",  
    description="Mengambil daftar pasien yang terdaftar sesuai dengan dokter yang login",
    response_model=List[PatientWithRecords])
def list_patients(
    db: Session = Depends(get_db),
    claims: dict = Depends(require_role(["Dokter", "SuperAdmin"]))
):
    query = db.query(Patient)
    if claims.get("role") == "Dokter":
        query = query.filter(Patient.doctor_email == claims.get("email"))
    patients = query.all()
    return patients

# === Endpoint sinkronisasi fallback dari Booking Service ===
@app.post(
    "/patients/sync-from-booking",
    tags=["Patient"],
    summary="Sinkronisasi Pasien",
    description="Endpoint untuk sinkronisasi data pasien dari Booking Service")
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

@app.post(
    "/patients/records",
    tags=["Medical Record"], 
    summary="Tambah Rekam Medis",
    description="Menambahkan rekam medis baru untuk pasien",
    response_model=MedicalRecordResponse)
def add_record(
    data: MedicalRecordCreate, 
    db: Session = Depends(get_db), 
    claims: dict = Depends(require_role(["Dokter"]))
):
    doctor_username = claims.get("sub")
    doctor_full_name = claims.get("full_name") or claims.get("sub")
    
    new_record = MedicalRecord(
        patient_id=data.patient_id,
        booking_id=data.booking_id,
        doctor_username=doctor_username,
        doctor_full_name=doctor_full_name,
        visit_date=data.visit_date,
        visit_type=data.visit_type,
        diagnosis=data.diagnosis,
        treatment=data.treatment,
        vital_signs=data.vital_signs,
        extended_data=data.extended_data
    )
    
    db.add(new_record)

    # Update status pasien
    patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
    if patient:
        if hasattr(data, 'status') and data.status:
            patient.status = data.status
        else:
            patient.status = "Control"
    
    db.commit()
    db.refresh(new_record)
    return new_record

@app.post(
    "/patients/prescriptions", 
    tags=["Prescription"],
    summary="Tambah atau Update Resep Obat",
    description="Menambahkan atau memperbarui resep obat untuk pasien. Jika resep dengan nomor yang sama sudah ada, maka akan diperbarui.",
    response_model=PrescriptionResponse)
def add_prescription(
    data: PrescriptionCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(require_role(["Dokter"]))
):
    doctor_username = claims.get("sub")
    doctor_full_name = claims.get("full_name") or claims.get("sub")

    existing_prescription = db.query(Prescription).filter(
        or_(
            Prescription.prescription_number == data.prescription_number,
            (Prescription.record_id == data.record_id) & (Prescription.record_id != None) & (Prescription.patient_id == data.patient_id)
        )
    ).first()

    if existing_prescription:

        existing_prescription.medicines = data.medicines
        existing_prescription.instructions = data.instructions
        existing_prescription.doctor_username = doctor_username
        existing_prescription.doctor_name = doctor_full_name

        if data.record_id:
            existing_prescription.record_id = data.record_id
            
        db.commit()
        db.refresh(existing_prescription)
        target = existing_prescription
    else:
        # Jika benar-benar baru, lakukan INSERT
        new_prescription = Prescription(
            patient_id=data.patient_id,
            record_id=data.record_id,
            doctor_username=doctor_username,
            doctor_name=doctor_full_name,
            medicines=data.medicines,
            instructions=data.instructions,
            prescription_number=data.prescription_number,
        )
        db.add(new_prescription)
        db.commit()
        db.refresh(new_prescription)
        target = new_prescription

    return PrescriptionResponse( 
        id=target.id, 
        patient_id=target.patient_id, 
        record_id=target.record_id, 
        doctor_name=target.doctor_name, 
        doctor_username=target.doctor_username, 
        medicines=target.medicines, 
        instructions=target.instructions, 
        prescription_number=target.prescription_number, 
        created_at=target.created_at.isoformat())