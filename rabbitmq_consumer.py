# sentracare-be-patient/rabbitmq_consumer.py
# import aio_pika
# import os
# import asyncio
# import json
# from database import SessionLocal
# from models import Patient
# from datetime import datetime

# RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
# RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
# RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")

# async def process_booking_confirmed(message: aio_pika.IncomingMessage):
#     async with message.process():
#         try:
#             payload = json.loads(message.body.decode())
#             db = SessionLocal()
#             try:
#                 existing = db.query(Patient).filter(Patient.booking_id == payload["booking_id"]).first()
#                 if not existing:
#                     tgl = None
#                     if payload.get("tanggal_pemeriksaan"):
#                         tgl = datetime.strptime(payload["tanggal_pemeriksaan"], "%Y-%m-%d").date()
#                     new_patient = Patient(
#                         full_name=payload["full_name"],
#                         email=payload["email"],
#                         phone_number=payload["phone_number"],
#                         gender=payload["gender"],
#                         age=payload["age"],
#                         address=payload["address"],
#                         status="Active",
#                         tipe_layanan=payload["tipe_layanan"],
#                         tanggal_pemeriksaan=tgl,
#                         jam_pemeriksaan=payload["jam_pemeriksaan"],
#                         booking_id=payload["booking_id"],
#                         doctor_email=payload["doctor_email"],
#                         doctor_full_name=payload["doctor_name"],
#                     )
#                     db.add(new_patient)
#                     db.commit()
#                     db.refresh(new_patient)
#                     print(f"Patient registered from booking {payload['booking_id']}")
#             finally:
#                 db.close()
#         except Exception as e:
#             print(f"Error processing booking.confirmed: {e}")

# async def consume():
#     connection = await aio_pika.connect_robust(
#         f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}/"
#     )
#     async with connection:
#         channel = await connection.channel()
#         exchange = await channel.declare_exchange("booking", aio_pika.ExchangeType.TOPIC)
#         queue = await channel.declare_queue("patient-service-queue", durable=True)
#         await queue.bind(exchange, routing_key="booking.confirmed")
#         await queue.consume(process_booking_confirmed)
#         print("Patient Service listening for booking.confirmed events...")
#         await asyncio.Future()