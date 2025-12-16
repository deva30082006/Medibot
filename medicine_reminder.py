import schedule
import time
import threading
import sqlite3
import os
from datetime import datetime, timedelta
from plyer import notification
from twilio.rest import Client

# ------------------ CONFIG ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "reminders.db")

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")

# ------------------ DATABASE ------------------
def init_db():
    """Create reminders table if not exists"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine TEXT NOT NULL,
            time TEXT NOT NULL,
            days INTEGER NOT NULL,
            phone TEXT,
            start_date TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def save_reminder_to_db(medicine, time_str, days, phone):
    """Save a new reminder to the database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    start_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO reminders (medicine, time, days, phone, start_date)
        VALUES (?, ?, ?, ?, ?)
    """, (medicine, time_str, days, phone, start_date))
    conn.commit()
    conn.close()

def load_reminders_from_db():
    """Load reminders from SQLite and schedule them"""
    if not os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT medicine, time, days, phone, start_date FROM reminders")
    reminders = cursor.fetchall()
    conn.close()

    for med, time_str, days, phone, start_date in reminders:
        schedule_reminder(med, time_str, days, phone, start_date=start_date)

# ------------------ NOTIFICATIONS ------------------
def show_notification(medicine):
    """Desktop notification"""
    try:
        notification.notify(
            title="💊 Medicine Reminder",
            message=f"It's time to take {medicine}",
            timeout=10
        )
    except Exception as e:
        print("Notification failed:", e)

def send_sms(medicine, phone):
    """Send SMS using Twilio"""
    if not all([TWILIO_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, phone]):
        return  # skip if Twilio not configured or phone missing
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=f"💊 Reminder: Take your medicine - {medicine}",
            from_=TWILIO_FROM_NUMBER,
            to=phone
        )
    except Exception as e:
        print("SMS failed:", e)

# ------------------ SCHEDULER ------------------
def validate_time_format(time_str):
    """Check HH:MM format"""
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False

def schedule_reminder(medicine, time_str, days, phone, start_date=None):
    """Schedule a medicine reminder"""
    if not validate_time_format(time_str):
        raise ValueError("Time must be in HH:MM format")

    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
    else:
        start_dt = datetime.now()

    end_date = start_dt + timedelta(days=int(days))

    def job():
        if datetime.now() <= end_date:
            show_notification(medicine)
            send_sms(medicine, phone)
        else:
            return schedule.CancelJob

    schedule.every().day.at(time_str).do(job)

def start_medicine_reminder(medicine, time_str, days, phone):
    """
    Schedule a new reminder from Flask.
    Saves to DB and schedules in background.
    """
    save_reminder_to_db(medicine, time_str, days, phone)
    schedule_reminder(medicine, time_str, days, phone)

# ------------------ RUNNER ------------------
def run_scheduler():
    """Run scheduler loop"""
    init_db()
    load_reminders_from_db()
    while True:
        schedule.run_pending()
        time.sleep(1)

def start_scheduler_thread():
    """Start scheduler in background thread"""
    thread = threading.Thread(target=run_scheduler, daemon=True)
    thread.start()
    print("✅ Medicine reminder scheduler started")
