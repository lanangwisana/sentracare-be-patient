# sentracare-be-patient/models.py
from sqlalchemy import JSON, Column, Date, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), index=True, nullable=False)
    phone_number = Column(String(20), nullable=False)
    status = Column(String(20), default="Active")
    gender = Column(String(20))  # "Laki-laki" / "Perempuan"
    age = Column(Integer)
    address = Column(Text)
    tipe_layanan = Column(String(50))
    tanggal_pemeriksaan = Column(Date, nullable=True)
    jam_pemeriksaan = Column(String(20), nullable=True)
    booking_id = Column(Integer, index=True, nullable=True)

    # Tambahan untuk assign dokter
    doctor_email = Column(String(100), index=True, nullable=True)
    doctor_full_name = Column(String(100), nullable=True)

    records = relationship("MedicalRecord", back_populates="patient", cascade="all, delete-orphan")

class MedicalRecord(Base):
    __tablename__ = "medical_records"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    booking_id = Column(Integer, nullable=True)
    doctor_username = Column(String(50), nullable=False)
    doctor_full_name = Column(String(100), nullable=True)
    visit_date = Column(Date, nullable=False)
    visit_type = Column(String(50), nullable=False)
    diagnosis = Column(Text, nullable=False)
    treatment = Column(Text, nullable=False)
    prescription = Column(Text, nullable=True)
    vital_signs = Column(JSON, nullable=True)
    extended_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("Patient", back_populates="records")