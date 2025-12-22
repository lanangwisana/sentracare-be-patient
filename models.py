# models.py
from sqlalchemy import JSON, Column, Date, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone_number = Column(String(20), nullable=False)
    status = Column(String(20), nullable=True, default="Active")
    blood_type = Column(String(5), nullable=True)
    gender = Column(String(20), nullable=True)
    allergies = Column(Text, nullable=True)
    emergency_contact = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    birth_date = Column(Date, nullable=True)

    records = relationship("MedicalRecord", back_populates="patient", cascade="all, delete-orphan")

class MedicalRecord(Base):
    __tablename__ = "medical_records"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    booking_id = Column(Integer, nullable=True)
    doctor_username = Column(String(50), nullable=False)
    visit_date = Column(Date, nullable=False)
    visit_type = Column(String(50), nullable=False)
    diagnosis = Column(Text, nullable=False)
    treatment = Column(Text, nullable=False)
    prescription = Column(Text, nullable=True)
    vital_signs = Column(JSON, nullable=True)
    extended_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="records")
