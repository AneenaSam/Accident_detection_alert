import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

EMAIL_SENDER   = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
POLICE_EMAIL   = os.getenv("POLICE_EMAIL")

CRIME_LOCATION = "Pimpri-Chinchwad, Pune, Maharashtra"
MAPS_LINK      = "https://maps.google.com/?q=18.6298,73.7997"

SEVERITY_COLOR = {
    "CRITICAL": "🔴",
    "HIGH":     "🟠",
    "MEDIUM":   "🟡",
}


def send_crime_alert_email(snapshot_path, crimes):
    """Send crime alert email to police with snapshot."""
    try:
        crime_lines = "\n".join(
            f"  {SEVERITY_COLOR.get(c['severity'], '⚪')} [{c['severity']}] {c['label']}\n     → {c['detail']}"
            for c in crimes
        )

        most_severe = crimes[0]["severity"] if crimes else "UNKNOWN"

        msg = MIMEMultipart()
        msg["From"]    = EMAIL_SENDER
        msg["To"]      = POLICE_EMAIL
        msg["Subject"] = f"🚔 CRIME ALERT [{most_severe}] — CCTV Detection | {CRIME_LOCATION}"

        body = f"""
╔══════════════════════════════════════════╗
   AUTOMATED CRIME DETECTION ALERT
╚══════════════════════════════════════════╝

Time     : {datetime.now().strftime("%d-%m-%Y %H:%M:%S")}
Location : {CRIME_LOCATION}
Maps     : {MAPS_LINK}
Severity : {most_severe}

━━━━━━ CRIMES DETECTED ━━━━━━
{crime_lines}

━━━━━━ ACTION REQUIRED ━━━━━━
Please dispatch police unit to the location immediately.
Snapshot of the incident is attached to this email.

-- Automated Alert by AccidentAI Crime Detection System
   Powered by YOLOv8 Computer Vision
        """

        msg.attach(MIMEText(body, "plain"))

        if snapshot_path and os.path.exists(snapshot_path):
            with open(snapshot_path, "rb") as f:
                img = MIMEImage(f.read(), name="crime_snapshot.jpg")
                msg.attach(img)

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, POLICE_EMAIL, msg.as_string())

        print(f"✅ Crime alert email sent to police: {POLICE_EMAIL}")
        return True

    except Exception as e:
        print(f"❌ Crime email failed: {e}")
        return False
