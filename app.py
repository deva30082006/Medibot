from flask import Flask, render_template, request, jsonify
import pandas as pd
import joblib
import sqlite3
from datetime import datetime

# ---------------- MEDICINE REMINDER ----------------
from medicine_reminder import start_scheduler_thread, start_medicine_reminder

app = Flask(__name__)

# ---------------- START REMINDER SCHEDULER ----------------
# This runs in background and loads existing reminders from DB
start_scheduler_thread()

# ---------------- LOAD ML ASSETS ----------------
model = joblib.load('disease_model.joblib')
encoder = joblib.load('disease_encoder.joblib')
symptoms = joblib.load('symptom_list.joblib')  # list of strings like 'cold', 'cough'

# ---------------- HOME ----------------
@app.route('/')
def home():
    pretty_symptoms = [s.replace('_', ' ') for s in symptoms]
    return render_template('index.html', symptoms=pretty_symptoms)


# ---------------- DISEASE PREDICTION ----------------
@app.route('/predict', methods=['POST'])
def predict():
    user_input = request.form.get('symptoms', '').strip().lower()

    entered_symptoms = [
        s.strip().replace(' ', '_') for s in user_input.split(',') if s.strip()
    ]

    user_vals = [0] * len(symptoms)
    unknown = []

    for s in entered_symptoms:
        if s in symptoms:
            idx = symptoms.index(s)
            user_vals[idx] = 1
        else:
            unknown.append(s)

    user_df = pd.DataFrame([user_vals], columns=symptoms)

    pred_enc = model.predict(user_df)
    disease = encoder.inverse_transform(pred_enc)[0]

    try:
        proba = model.predict_proba(user_df)[0]
        top_idx = proba.argsort()[::-1][:3]
        top_labels = encoder.inverse_transform(top_idx)
        top_scores = [round(float(proba[i]) * 100, 2) for i in top_idx]
        top3 = list(zip(top_labels, top_scores))
    except Exception:
        top3 = None

    return render_template(
        'result.html',
        disease=disease,
        top3=top3,
        entered=", ".join([s.replace('_', ' ') for s in entered_symptoms]) or "None",
        unknown=", ".join([u.replace('_', ' ') for u in unknown]) if unknown else None
    )


# ---------------- MEDICINE REMINDER ROUTE ----------------
@app.route('/set_reminder', methods=['POST'])
def set_reminder():
    medicine_name = request.form.get('medicine')
    reminder_time = request.form.get('time')  # Expected format: HH:MM
    duration_days = request.form.get('days')
    phone_number = request.form.get('phone')

    # Validate inputs
    if not all([medicine_name, reminder_time, duration_days, phone_number]):
        return jsonify({
            "status": "error",
            "message": "Missing reminder details"
        })

    try:
        # Validate time format
        datetime.strptime(reminder_time, "%H:%M")
        duration_days = int(duration_days)
        if duration_days <= 0:
            raise ValueError
    except ValueError:
        return jsonify({
            "status": "error",
            "message": "Invalid time or duration format"
        })

    # Schedule the reminder
    start_medicine_reminder(
        medicine_name=medicine_name,
        reminder_time=reminder_time,
        duration_days=duration_days,
        phone_number=phone_number
    )

    return jsonify({
        "status": "success",
        "message": f"Reminder set for {medicine_name} at {reminder_time} for {duration_days} day(s)"
    })


# ---------------- RUN APP ----------------
if __name__ == '__main__':
    app.run(debug=True)
