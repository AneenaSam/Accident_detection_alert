import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from twilio.rest import Client
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Load credentials
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")
EMERGENCY_PHONE = os.getenv("EMERGENCY_PHONE")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
POLICE_EMAIL = os.getenv("POLICE_EMAIL")

ACCIDENT_LOCATION = "NH 66, Ernakulam, Kerala — 10.0159° N, 76.3419° E"
MAPS_LINK = "https://maps.google.com/?q=10.0159,76.3419"

def send_sms_alert(vehicles):
    """Send SMS to ambulance via Twilio"""
    try:
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
        print(f"✅ SMS sent: {message.sid}")
        return True
    except Exception as e:
        print(f"❌ SMS failed: {e}")
        return False


def make_emergency_call():
    """Make automated voice call to ambulance"""
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        call = client.calls.create(
            twiml=f"""<Response>
                <Say voice="alice">
                    Alert! Road accident detected at {ACCIDENT_LOCATION}.
                    Please dispatch an ambulance immediately.
                    Repeat. Accident detected. Immediate response required.
                </Say>
            </Response>""",
            from_=TWILIO_PHONE,
            to=EMERGENCY_PHONE
        )
        print(f"✅ Call initiated: {call.sid}")
        return True
    except Exception as e:
        print(f"❌ Call failed: {e}")
        return False


def send_email_alert(snapshot_path, vehicles, recipient_type="hospital"):
    """Send email with accident snapshot to hospital or police"""
    try:
        subject_map = {
            "hospital": "🚨 EMERGENCY: Road Accident — Prepare Trauma Team",
            "police": "🚔 ALERT: Road Accident — Vehicle Details Inside"
        }
        to_email = EMAIL_RECEIVER if recipient_type == "hospital" else POLICE_EMAIL
        vehicle_list = "\n".join([f"  - {v['type'].upper()} (confidence: {v['confidence']})" 
                                   for v in vehicles])

        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = to_email
        msg["Subject"] = subject_map[recipient_type]

        body = f"""
AUTOMATIC ACCIDENT DETECTION ALERT
=====================================
Time     : {datetime.now().strftime("%d-%m-%Y %H:%M:%S")}
Location : {ACCIDENT_LOCATION}
Maps     : {MAPS_LINK}

Vehicles Involved:
{vehicle_list}

{'Please prepare emergency trauma team for incoming patient.' if recipient_type == 'hospital' else 'Please dispatch police unit to the location immediately.'}

-- Automated Alert by AccidentAI System
        """
        msg.attach(MIMEText(body, "plain"))

        # Attach snapshot
        if snapshot_path and os.path.exists(snapshot_path):
            with open(snapshot_path, "rb") as f:
                img = MIMEImage(f.read(), name="accident_snapshot.jpg")
                msg.attach(img)

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, to_email, msg.as_string())

        print(f"✅ Email sent to {recipient_type}: {to_email}")
        return True
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False


def trigger_all_alerts(vehicles, snapshot_path):
    """Fire all alerts simultaneously"""
    print("\n🚨 TRIGGERING ALL EMERGENCY ALERTS...\n")
    results = {
        "sms": send_sms_alert(vehicles),
        "call": make_emergency_call(),
        "hospital_email": send_email_alert(snapshot_path, vehicles, "hospital"),
        "police_email": send_email_alert(snapshot_path, vehicles, "police"),
    }
    print("\n📊 Alert Summary:")
    for k, v in results.items():
        print(f"  {'✅' if v else '❌'} {k}")
    return results