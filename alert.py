print(" THIS ALERT.PY IS RUNNING ")
import smtplib
import os
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from twilio.rest import Client
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────
# 🔐 Load Credentials
# ─────────────────────────────────────
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")
EMERGENCY_PHONE = os.getenv("EMERGENCY_PHONE")

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
POLICE_EMAIL = os.getenv("POLICE_EMAIL")

# Multiple hospitals
HOSPITAL_EMAILS = [
    {"name": "CityCare Hospital", "email": os.getenv("HOSPITAL_1")},
    {"name": "Metro Trauma Center", "email": os.getenv("HOSPITAL_2")},
    {"name": "LifeLine Medical", "email": os.getenv("HOSPITAL_3")},
]

ACCIDENT_LOCATION = "NH 66, Ernakulam, Kerala — 10.0159° N, 76.3419° E"
MAPS_LINK = "https://maps.google.com/?q=10.0159,76.3419"

# ─────────────────────────────────────
# 🧠 ACTIVE CASE STORAGE
# ─────────────────────────────────────
ACTIVE_CASES = {}

# ─────────────────────────────────────
# 📲 SMS ALERT (FULL DEBUG VERSION)
# ─────────────────────────────────────
def send_sms_alert(vehicles):
    try:
        print("\n🔎 ===== SMS DEBUG START =====")
        print("TWILIO_SID:", TWILIO_SID)
        print("TWILIO_PHONE:", TWILIO_PHONE)
        print("EMERGENCY_PHONE:", EMERGENCY_PHONE)

        # Validate credentials
        if not TWILIO_SID or not TWILIO_TOKEN:
            print("❌ Twilio credentials missing in .env")
            return False

        if not TWILIO_PHONE:
            print("❌ TWILIO_PHONE missing in .env")
            return False

        if not EMERGENCY_PHONE:
            print("❌ EMERGENCY_PHONE missing in .env")
            return False

        # Ensure correct phone format
        if not TWILIO_PHONE.startswith("+"):
            print("❌ TWILIO_PHONE must start with + and country code")
            return False

        if not EMERGENCY_PHONE.startswith("+"):
            print("❌ EMERGENCY_PHONE must start with + and country code")
            return False

        client = Client(TWILIO_SID, TWILIO_TOKEN)

        vehicle_list = ", ".join([v["type"] for v in vehicles])

        message = client.messages.create(
            body=f"""🚨 ACCIDENT DETECTED
Time: {datetime.now().strftime("%H:%M:%S")}
Location: {ACCIDENT_LOCATION}
Vehicles: {vehicle_list}
Maps: {MAPS_LINK}
⚡ Dispatch ambulance immediately!""",
            from_=TWILIO_PHONE,
            to=EMERGENCY_PHONE
        )

        print("✅ SMS SENT SUCCESSFULLY")
        print("Message SID:", message.sid)
        print("🔎 ===== SMS DEBUG END =====\n")

        return True

    except Exception as e:
        print("\n❌ ===== SMS FAILED =====")
        print("Full Error:", str(e))
        print("🔎 ===== END ERROR =====\n")
        return False


# ─────────────────────────────────────
# 📞 VOICE CALL ALERT
# ─────────────────────────────────────
def make_emergency_call():
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)

        call = client.calls.create(
            twiml=f"""
<Response>
    <Say voice="alice">
        Emergency Alert. Road accident detected at {ACCIDENT_LOCATION}.
        Immediate ambulance dispatch required.
    </Say>
</Response>
""",
            from_=TWILIO_PHONE,
            to=EMERGENCY_PHONE
        )

        print(f"✅ Call initiated: {call.sid}")
        return True

    except Exception as e:
        print("❌ Call failed:", str(e))
        return False


# ─────────────────────────────────────
# 🏥 HOSPITAL EMAIL
# ─────────────────────────────────────
def send_hospital_email(snapshot_path, vehicles, hospital_name, hospital_email, case_id):
    try:
        vehicle_list = "\n".join(
            f"- {v['type'].upper()} (confidence: {v['confidence']})"
            for v in vehicles
        )

        accept_link = f"http://localhost:8501/?case_id={case_id}&hospital={hospital_name}"

        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = hospital_email
        msg["Subject"] = f"🚨 EMERGENCY CASE #{case_id}"

        body = f"""
EMERGENCY ACCIDENT CASE

Case ID  : {case_id}
Time     : {datetime.now().strftime("%d-%m-%Y %H:%M:%S")}
Location : {ACCIDENT_LOCATION}
Maps     : {MAPS_LINK}

Vehicles:
{vehicle_list}

To ACCEPT this case click:
{accept_link}
"""

        msg.attach(MIMEText(body, "plain"))

        if snapshot_path and os.path.exists(snapshot_path):
            with open(snapshot_path, "rb") as f:
                img = MIMEImage(f.read(), name="snapshot.jpg")
                msg.attach(img)

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, hospital_email, msg.as_string())

        print(f"✅ Sent to {hospital_name}")
        return True

    except Exception as e:
        print(f"❌ Hospital email failed for {hospital_name}:", str(e))
        return False


# ─────────────────────────────────────
# 👮 POLICE EMAIL
# ─────────────────────────────────────
def send_police_email(snapshot_path, vehicles, case_id):
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = POLICE_EMAIL
        msg["Subject"] = f"🚔 ACCIDENT CASE #{case_id}"

        body = f"""
ACCIDENT ALERT

Case ID  : {case_id}
Location : {ACCIDENT_LOCATION}
Maps     : {MAPS_LINK}

Police intervention required immediately.
"""

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, POLICE_EMAIL, msg.as_string())

        print("✅ Police email sent")
        return True

    except Exception as e:
        print("❌ Police email failed:", str(e))
        return False


# ─────────────────────────────────────
# 🚨 MAIN TRIGGER
# ─────────────────────────────────────
def trigger_all_alerts(vehicles, snapshot_path):

    case_id = str(uuid.uuid4())[:8]

    ACTIVE_CASES[case_id] = {
        "status": "OPEN",
        "accepted_by": None
    }

    results = {
        "case_id": case_id,
        "sms": send_sms_alert(vehicles),
        "call": make_emergency_call(),
        "hospitals": {},
        "police_email": send_police_email(snapshot_path, vehicles, case_id)
    }

    for hospital in HOSPITAL_EMAILS:
        result = send_hospital_email(
            snapshot_path,
            vehicles,
            hospital["name"],
            hospital["email"],
            case_id
        )
        results["hospitals"][hospital["name"]] = result

    return results


# ─────────────────────────────────────
# 🏥 ACCEPT CASE
# ─────────────────────────────────────
def accept_case(case_id, hospital_name):

    if case_id not in ACTIVE_CASES:
        return "INVALID"

    if ACTIVE_CASES[case_id]["status"] == "ACCEPTED":
        return "ALREADY_ACCEPTED"

    ACTIVE_CASES[case_id]["status"] = "ACCEPTED"
    ACTIVE_CASES[case_id]["accepted_by"] = hospital_name

    notify_other_hospitals(case_id, hospital_name)

    return "SUCCESS"


def notify_other_hospitals(case_id, accepted_hospital):
    for hospital in HOSPITAL_EMAILS:
        if hospital["name"] != accepted_hospital:
            send_case_handled_email(
                hospital["email"],
                case_id,
                accepted_hospital
            )


def send_case_handled_email(email, case_id, accepted_by):
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = email
        msg["Subject"] = f"Case #{case_id} Handled"

        body = f"""
Case {case_id} has been ACCEPTED by {accepted_by}.

No action required from your side.
"""

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, email, msg.as_string())

    except Exception as e:
        print("❌ Case handled email failed:", str(e))