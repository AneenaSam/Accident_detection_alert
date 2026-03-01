"""
Run this ONCE before starting the app:
    pip install gtts
    python generate_alerts.py

It creates audio/accident_alert.mp3 and audio/crime_alert.mp3 etc.
"""
import os
os.makedirs("audio", exist_ok=True)

try:
    from gtts import gTTS

    alerts = {
        "accident_alert":      "Warning! Road accident detected. Dispatching ambulance immediately.",
        "fight_alert":         "Alert! Fight detected. Police have been notified.",
        "weapon_alert":        "Critical alert! Weapon detected on camera. Police are on the way.",
        "theft_alert":         "Warning! Theft pattern detected. Police have been alerted.",
    }

    for name, text in alerts.items():
        path = f"audio/{name}.mp3"
        gTTS(text=text, lang="en", slow=False).save(path)
        print(f"✅ Generated: {path}")

    print("\nAll audio files ready. Now run: streamlit run app.py")

except ImportError:
    print("❌ gTTS not installed. Run: pip install gtts")