# GoldenResQ — Golden Hour Response System

> **AI-powered real-time road accident detection and multi-agency emergency alert system**  
> *Saving lives by acting within the critical Golden Hour*

---

## 📌 Overview

**GoldenResQ** is an intelligent emergency response system that uses computer vision to automatically detect road accidents from CCTV footage and instantly dispatch alerts to hospitals, police, and ambulance services — all within seconds.

The system is built around the concept of the **Golden Hour**: the critical 60-minute window after a traumatic accident where immediate medical intervention dramatically increases survival rates.

---

## 🎯 Key Features

- 🎥 **Real-Time Accident Detection** — YOLOv8-powered vehicle detection with 3-layer accident analysis
- 🏥 **Multi-Hospital Alert System** — Simultaneously notifies multiple hospitals with a one-click case acceptance link
- 📱 **SMS Alert** — Instant Twilio SMS to emergency responders
- 📞 **Automated Voice Call** — Twilio voice call with accident details
- 👮 **Police Notification** — Automatic email alert to police with location
- 📸 **Accident Snapshot** — Auto-captures and attaches the accident frame to all emails
- 🔊 **Audio Alarm** — Browser-based voice alert on accident detection
- 📋 **Event Log** — Full session history of all detected incidents

---

## 🧠 How Accident Detection Works

The detector uses **3 independent layers** to confirm an accident before triggering alerts — eliminating false positives:

| Layer | Method | Trigger |
|-------|--------|---------|
| 1 | Sudden Impact Motion | Large pixel change between frames (score > 18) |
| 2 | Vehicle Bounding Box Overlap | Two vehicles' boxes overlap by > 15% |
| 3 | Sudden Direction Change | Vehicle center jumps > 45px in 2 frames |

An alert is only fired when **2+ consecutive frames** confirm an accident.

---

## 🏗️ Project Structure

```
GoldenResQ/
│
├── app.py                  # Main Streamlit application
├── detector.py             # YOLOv8 accident detection engine
├── alert.py                # All alert functions (SMS, call, email)
├── generate_alerts.py       # Generate audio alert files (run once)
├── goldenresq_app.py 
├── sms.py                  # Standalone SMS test script
├── yolov8n.pt              # YOLOv8 nano model weights
│
├── audio/
│   └── accident_alert.mp3  # Browser audio alert (auto-generated)
│
├── static/
│   └── snapshots/          # Auto-saved accident frame images
│
├── .env                    # API credentials (never commit this!)
├── .gitignore
└── requirements.txt
```

---


## 🔑 API Setup Guide

### Gmail (Email Alerts)
1. Enable 2-Factor Authentication on your Google account
2. Go to **Google Account → Security → App Passwords**
3. Generate an App Password and use it as `EMAIL_PASSWORD`

### Twilio (SMS & Voice Call)
1. Sign up at [twilio.com](https://www.twilio.com)
2. Get your **Account SID**, **Auth Token**, and a **Twilio phone number**
3. For trial accounts, verify all recipient numbers at [Twilio Verified Numbers](https://www.twilio.com/console/phone-numbers/verified)

---

## 🌐 Making the Accept Link Public

The hospital accept link in emails must point to a **publicly accessible URL**, not `localhost`.

**Option 1 — Streamlit Cloud (Recommended, Free)**
1. Push project to GitHub
2. Deploy at [streamlit.io/cloud](https://streamlit.io/cloud)
3. Set `APP_URL=https://your-app.streamlit.app` in Secrets

---

## 🚀 Usage

1. Open the app in your browser (`http://localhost:8501`)
2. Upload an accident video (MP4 or AVI) from the sidebar
3. Click **▶ Start Detection**
4. When an accident is detected:
   - 🚨 Red border appears on the video feed
   - 📱 SMS + voice call sent to emergency responder
   - 📧 Emails sent to all hospitals with an **Accept Case** button
   - 👮 Police notified by email
5. A hospital clicks **Accept** → other hospitals are notified the case is handled

---

## 📦 Requirements

```
streamlit
opencv-python-headless
ultralytics
twilio
python-dotenv
gtts
```

Install all with:
```bash
pip install -r requirements.txt
```

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Streamlit |
| Object Detection | YOLOv8 (Ultralytics) |
| Video Processing | OpenCV |
| SMS & Voice Call | Twilio |
| Email Alerts | Gmail SMTP |
| Audio Alerts | gTTS |
| Environment Config | python-dotenv |

---




## 👨‍💻 Built With ❤️ for Hackathon

*GoldenResQ — Because every second counts.*
