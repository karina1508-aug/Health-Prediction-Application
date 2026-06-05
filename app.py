# app.py
import streamlit as st
import pandas as pd
import mysql.connector
import joblib
import numpy as np
import re
from datetime import date

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="Health Prediction App",
    layout="wide"
)

# -----------------------------
# LOAD MODEL
# -----------------------------
try:
    model = joblib.load("health_model.pkl")
except Exception as e:
    st.error(f"Error loading model: {e}")
    st.stop()

# -----------------------------
# MYSQL CONNECTION
# -----------------------------
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Kari1508",   # <-- replace with your MySQL password
    database="Health_Prediction_Data"
)
cursor = conn.cursor()

# Create table if not exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS patients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    dob DATE,
    email VARCHAR(100),
    glucose FLOAT,
    haemoglobin FLOAT,
    cholesterol FLOAT,
    remarks VARCHAR(50)
)
""")

# -----------------------------
# VALIDATION FUNCTIONS
# -----------------------------
def validate_email(email: str) -> bool:
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def validate_dob(dob: date) -> bool:
    return date(1985, 1, 1) <= dob <= date(2035, 12, 31)

def validate_blood_values(glucose, haemoglobin, cholesterol) -> bool:
    return (70 <= glucose <= 200) and (10 <= haemoglobin <= 17) and (150 <= cholesterol <= 300)

# -----------------------------
# PREDICTION FUNCTION
# -----------------------------
def predict_health(glucose, haemoglobin, cholesterol):
    try:
        features = np.array([[glucose, haemoglobin, cholesterol]])
        prediction = model.predict(features)[0]
        remarks_map = {
            0: "Healthy",
            1: "Diabetes Risk",
            2: "Anaemia Risk",
            3: "Heart Risk"
        }
        return remarks_map.get(prediction, "Unknown")
    except Exception as e:
        return f"Prediction Error: {e}"

# -----------------------------
# APP TITLE
# -----------------------------
st.title("🏥 Health Prediction Application")

# -----------------------------
# SIDEBAR MENU
# -----------------------------
menu = ["Add Patient", "View Patients", "Update Patient", "Delete Patient"]
choice = st.sidebar.selectbox("Menu", menu)

# =====================================================
# ADD PATIENT
# =====================================================
if choice == "Add Patient":
    st.subheader("➕ Add Patient")

    with st.form("add_form"):
        full_name = st.text_input("Full Name")
        dob = st.date_input(
            "Date of Birth",
            value=date(1985, 1, 1),
            min_value=date(1985, 1, 1),
            max_value=date(2035, 12, 31)
        )
        email = st.text_input("Email Address")
        glucose = st.number_input("Glucose", min_value=0.0, format="%.2f")
        haemoglobin = st.number_input("Haemoglobin", min_value=0.0, format="%.2f")
        cholesterol = st.number_input("Cholesterol", min_value=0.0, format="%.2f")
        submit = st.form_submit_button("Predict & Save")

    if submit:
        if full_name.strip() == "":
            st.error("Full Name is required")
        elif not validate_email(email):
            st.error("Invalid Email Address")
        elif not validate_dob(dob):
            st.error("DOB must be between 1985 and 2035")
        elif not validate_blood_values(glucose, haemoglobin, cholesterol):
            st.error("Values out of valid range (Glucose 70–200, Haemoglobin 10–17, Cholesterol 150–300)")
        else:
            remark = predict_health(glucose, haemoglobin, cholesterol)
            cursor.execute("""
                INSERT INTO patients (name, dob, email, glucose, haemoglobin, cholesterol, remarks)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (full_name, dob, email, glucose, haemoglobin, cholesterol, remark))
            conn.commit()
            st.success("Patient Saved Successfully")
            st.write("### Prediction Result")
            st.write("Remark:", remark)

# =====================================================
# VIEW PATIENTS
# =====================================================
elif choice == "View Patients":
    st.subheader("📋 Patient Records")
    cursor.execute("SELECT * FROM patients")
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=["ID","Name","DOB","Email","Glucose","Haemoglobin","Cholesterol","Remarks"])
    if len(df) > 0:
        st.metric("Total Patients", len(df))
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No patient records found")

# =====================================================
# UPDATE PATIENT
# =====================================================
elif choice == "Update Patient":
    st.subheader("✏ Update Patient")
    cursor.execute("SELECT * FROM patients")
    rows = cursor.fetchall()
    patient_ids = [row[0] for row in rows]

    if patient_ids:
        selected_id = st.selectbox("Select Patient ID", patient_ids)
        cursor.execute("SELECT * FROM patients WHERE id=%s", (selected_id,))
        patient = cursor.fetchone()

        with st.form("update_form"):
            full_name = st.text_input("Full Name", patient[1])
            dob = st.date_input(
                "Date of Birth",
                value=patient[2],
                min_value=date(1985, 1, 1),
                max_value=date(2035, 12, 31)
            )
            email = st.text_input("Email", patient[3])
            glucose = st.number_input("Glucose", value=patient[4])
            haemoglobin = st.number_input("Haemoglobin", value=patient[5])
            cholesterol = st.number_input("Cholesterol", value=patient[6])
            update_btn = st.form_submit_button("Update")

        if update_btn:
            if not validate_email(email):
                st.error("Invalid Email Address")
            elif not validate_dob(dob):
                st.error("DOB must be between 1985 and 2035")
            elif not validate_blood_values(glucose, haemoglobin, cholesterol):
                st.error("Values out of valid range")
            else:
                remark = predict_health(glucose, haemoglobin, cholesterol)
                cursor.execute("""
                    UPDATE patients 
                    SET name=%s, dob=%s, email=%s, glucose=%s, haemoglobin=%s, cholesterol=%s, remarks=%s 
                    WHERE id=%s
                """, (full_name, dob, email, glucose, haemoglobin, cholesterol, remark, selected_id))
                conn.commit()
                st.success("Patient record updated successfully!")

# =====================================================
# DELETE PATIENT
# =====================================================
elif choice == "Delete Patient":
    st.subheader("🗑 Delete Patient")
    cursor.execute("SELECT * FROM patients")
    rows = cursor.fetchall()
    patient_ids = [row[0] for row in rows]

    if patient_ids:
        selected_id = st.selectbox("Select Patient ID to Delete", patient_ids)
        if st.button("Delete"):
            cursor.execute("DELETE FROM patients WHERE id=%s", (selected_id,))
            conn.commit()
            st.warning(f"Patient ID {selected_id} deleted successfully")
