import os
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()  # loads your .env file

TWILIO_SID   = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")
EMERGENCY_PHONE = os.getenv("EMERGENCY_PHONE")

client = Client(TWILIO_SID, TWILIO_TOKEN)

try:
    message = client.messages.create(
        body="Test alert",
        from_=TWILIO_PHONE,
        to=EMERGENCY_PHONE
    )
    print("✅ Success:", message.sid)
except Exception as e:
    print("❌ ERROR:", e)