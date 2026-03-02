import streamlit as st
import cv2
import tempfile
import time
import os
import base64
from datetime import datetime

from detector import run_on_video
from alert import trigger_all_alerts, accept_case

# ─────────────────────────────────────
# 🛡️ PAGE CONFIG
# ─────────────────────────────────────
st.set_page_config(
    page_title="SafeAI — Emergency Accident Response",
    page_icon="🚑",
    layout="wide"
)

# ─────────────────────────────────────
# 🏥 ACCEPT HANDLER (FIXED VERSION)
# ─────────────────────────────────────

params = st.query_params

if "case_id" in params and "hospital" in params:

    case_id = params.get("case_id")
    hospital = params.get("hospital")

    # If Streamlit returns list → take first value
    if isinstance(case_id, list):
        case_id = case_id[0]

    if isinstance(hospital, list):
        hospital = hospital[0]

    if "handled_case" not in st.session_state:

        result = accept_case(case_id, hospital)

        if result == "SUCCESS":
            st.success(f"✅ Case {case_id} accepted by {hospital}")
        elif result == "ALREADY_ACCEPTED":
            st.warning("⚠️ Case already accepted by another hospital.")
        else:
            st.error("❌ Invalid case ID.")

        st.session_state.handled_case = case_id

    st.query_params.clear()
# ─────────────────────────────────────
# 🔊 AUDIO SYSTEM (Accident Only)
# ─────────────────────────────────────
if "audio_b64" not in st.session_state:
    st.session_state.audio_b64 = {}
    if os.path.exists("audio/accident_alert.mp3"):
        with open("audio/accident_alert.mp3", "rb") as f:
            st.session_state.audio_b64["accident"] = base64.b64encode(f.read()).decode()

_audio_slot = st.empty()

def play_alert():
    b64 = st.session_state.audio_b64.get("accident")
    if b64:
        _audio_slot.markdown(
            f'<audio autoplay style="display:none">'
            f'<source src="data:audio/mp3;base64,{b64}" type="audio/mp3">'
            f'</audio>',
            unsafe_allow_html=True
        )


# ─────────────────────────────────────
# 📦 SESSION STATE
# ─────────────────────────────────────
if "alert_results" not in st.session_state:
    st.session_state.alert_results = {}

if "event_log" not in st.session_state:
    st.session_state.event_log = []


# ─────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────
st.sidebar.markdown("## ⚙️ Control Panel")
uploaded = st.sidebar.file_uploader("Upload Accident Video", type=["mp4", "avi"])


# ─────────────────────────────────────
# MAIN UI
# ─────────────────────────────────────
st.title("🚨 AI Accident Detection & Multi-Hospital Alert System")

video_slot = st.empty()
status_box = st.empty()
alert_box = st.empty()


def render_alert_status():
    r = st.session_state.alert_results
    if not r:
        alert_box.info("Waiting for detection...")
        return

    html = ""

    for key in ["sms", "call", "police_email"]:
        if key in r:
            status = "SENT ✅" if r[key] else "FAILED ❌"
            label = {
                "sms": "📱 SMS",
                "call": "📞 Voice Call",
                "police_email": "👮 Police"
            }[key]
            html += f"<div><b>{label}</b> — {status}</div>"

    for name, status_val in r["hospitals"].items():
        status = "SENT ✅" if status_val else "FAILED ❌"
        html += f"<div><b>🏥 {name}</b> — {status}</div>"

    alert_box.markdown(html, unsafe_allow_html=True)


def on_accident(frame, vehicles, snapshot_path):

    results = trigger_all_alerts(vehicles, snapshot_path)
    st.session_state.alert_results = results

    play_alert()

    st.session_state.event_log.append({
        "label": "🚨 Road Accident",
        "detail": f"{len(vehicles)} vehicle(s)",
        "time": datetime.now().strftime("%H:%M:%S")
    })


if uploaded:
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded.read())
    tfile.close()

    if st.sidebar.button("▶ Start Detection"):
        for annotated, accident, vehicles in run_on_video(tfile.name, on_accident):

            rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            video_slot.image(rgb, channels="RGB", use_container_width=True)

            if accident:
                status_box.error("🚨 ACCIDENT DETECTED")
            else:
                status_box.success("Monitoring...")

            render_alert_status()
            time.sleep(0.03)


# ─────────────────────────────────────
# EVENT LOG
# ─────────────────────────────────────
st.markdown("## 📋 Event Log")

if not st.session_state.event_log:
    st.info("No events recorded yet.")
else:
    for e in reversed(st.session_state.event_log):
        st.markdown(
            f"**{e['label']}** — {e['detail']} ({e['time']})"
        )

if st.button("🗑 Clear Log"):
    st.session_state.event_log = []
    st.rerun()