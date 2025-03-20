# export_data.py

import pandas as pd
from app import db
from app.models import User, Appointment, Availability
from app import create_app

# Initialize Flask App
app = create_app()

with app.app_context():
    # ------------------- USERS -------------------
    users = User.query.all()
    user_data = [{
        "ID": user.id,
        "Username": user.username,
        "Email": user.email,
        "Specialization": user.specialization,
        "Years of Working": user.years_of_working
    } for user in users]
    df_users = pd.DataFrame(user_data)

    # ------------------- APPOINTMENTS -------------------
    appointments = Appointment.query.all()
    appointment_data = [{
        "ID": appt.id,
        "Doctor ID": appt.doctor_id,
        "Patient ID": appt.patient_id,
        "Date": appt.date,
        "Time": appt.time,
        "Status": appt.status
    } for appt in appointments]
    df_appointments = pd.DataFrame(appointment_data)

    # ------------------- AVAILABILITY -------------------
    slots = Availability.query.all()
    availability_data = [{
        "ID": slot.id,
        "Doctor ID": slot.doctor_id,
        "Start Time": slot.start_time,
        "End Time": slot.end_time,
        "Is Booked": slot.is_booked
    } for slot in slots]
    df_availability = pd.DataFrame(availability_data)

    # ------------------- EXPORT TO EXCEL -------------------
    with pd.ExcelWriter("hospital_data_export.xlsx", engine='openpyxl') as writer:
        df_users.to_excel(writer, sheet_name="Users", index=False)
        df_appointments.to_excel(writer, sheet_name="Appointments", index=False)
        df_availability.to_excel(writer, sheet_name="Availability", index=False)

    print("✅ Export completed: hospital_data_export.xlsx")
