import streamlit as st
import cv2
import tempfile
import time
import os
from datetime import datetime
from detector import run_on_video, detect_accident, save_snapshot
from alert import trigger_all_alerts

# Page config
st.set_page_config(
    page_title="AccidentAI — Emergency Response System",
    page_icon="🚨",
    layout="wide"
)

# Header
st.markdown("""
    <h1 style='text-align:center; color:red;'>🚨 AccidentAI — Smart Emergency Response</h1>
    <p style='text-align:center; color:gray;'>Real-time accident detection powered by YOLOv8</p>
    <hr>
""", unsafe_allow_html=True)

# Layout
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📹 Live Video Feed")
    video_placeholder = st.empty()
    status_placeholder = st.empty()

with col2:
    st.subheader("📊 Response Status")
    alert_box = st.empty()
    st.markdown("---")
    st.subheader("🚗 Vehicle Info")
    vehicle_box = st.empty()
    st.markdown("---")
    st.subheader("📍 Location")
    st.markdown("""
        **NH 66, Ernakulam, Kerala**  
        📌 [Open in Google Maps](https://maps.google.com/?q=10.0159,76.3419)
    """)

# Sidebar
st.sidebar.title("⚙️ Control Panel")
source = st.sidebar.radio("Video Source", ["Upload Video", "Webcam"])
confidence = st.sidebar.slider("Detection Confidence", 0.1, 0.9, 0.25)
st.sidebar.markdown("---")
st.sidebar.markdown("### 📞 Emergency Contacts")
st.sidebar.success("🚑 Ambulance: Configured")
st.sidebar.success("🏥 Hospital: Configured")
st.sidebar.success("👮 Police: Configured")

# Alert state
if "alert_sent" not in st.session_state:
    st.session_state.alert_sent = False
if "alert_results" not in st.session_state:
    st.session_state.alert_results = {}

def show_alert_status(results):
    icons = {"sms": "📱 SMS", "call": "📞 Voice Call",
             "hospital_email": "🏥 Hospital", "police_email": "👮 Police"}
    html = ""
    for k, v in results.items():
        color = "green" if v else "red"
        icon = icons.get(k, k)
        status = "SENT ✅" if v else "FAILED ❌"
        html += f"<p style='color:{color};'><b>{icon}:</b> {status}</p>"
    return html

# Main logic
if source == "Upload Video":
    uploaded = st.sidebar.file_uploader("Upload accident video", type=["mp4", "avi", "mov"])

    if uploaded:
        # Save to temp file
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tfile.write(uploaded.read())
        tfile.close()

        st.sidebar.success("✅ Video loaded!")
        start = st.sidebar.button("▶️ START DETECTION")

        if start:
            st.session_state.alert_sent = False
            accident_callback_data = {}

            def on_accident(frame, vehicles, snapshot_path):
                if not st.session_state.alert_sent:
                    st.session_state.alert_sent = True
                    results = trigger_all_alerts(vehicles, snapshot_path)
                    st.session_state.alert_results = results
                    accident_callback_data["vehicles"] = vehicles

            for annotated_frame, accident, vehicles in run_on_video(tfile.name, on_accident):
                # Convert BGR to RGB
                rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                video_placeholder.image(rgb, channels="RGB", use_column_width=True)

                if accident:
                    status_placeholder.error("🚨 ACCIDENT DETECTED — ALERTS SENT!")
                else:
                    status_placeholder.success("✅ Monitoring... No accident detected")

                if st.session_state.alert_results:
                    alert_box.markdown(
                        show_alert_status(st.session_state.alert_results),
                        unsafe_allow_html=True
                    )

                if vehicles:
                    vehicle_box.markdown(
                        "\n".join([f"**{v['type'].upper()}** — {v['confidence']}" 
                                   for v in vehicles])
                    )

                time.sleep(0.03)

elif source == "Webcam":
    start_cam = st.sidebar.button("▶️ Start Webcam")
    stop_cam = st.sidebar.button("⏹️ Stop")

    if start_cam:
        cap = cv2.VideoCapture(0)
        alert_sent = False

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret or stop_cam:
                break

            accident, vehicles, annotated = detect_accident(frame, confidence)
            rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            video_placeholder.image(rgb, channels="RGB", use_column_width=True)

            if accident and not alert_sent:
                snapshot = save_snapshot(annotated)
                results = trigger_all_alerts(vehicles, snapshot)
                st.session_state.alert_results = results
                alert_sent = True
                status_placeholder.error("🚨 ACCIDENT DETECTED!")

            if st.session_state.alert_results:
                alert_box.markdown(
                    show_alert_status(st.session_state.alert_results),
                    unsafe_allow_html=True
                )

            time.sleep(0.03)

        cap.release()