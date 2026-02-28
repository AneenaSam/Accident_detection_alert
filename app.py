import streamlit as st
import cv2
import tempfile
import time
import os
from datetime import datetime
from detector import run_on_video, detect_accident, save_snapshot
from alert import trigger_all_alerts
from crime_detector import run_crime_detection_on_video, detect_crimes, save_crime_snapshot
from crime_alert import send_crime_alert_email

# ── Page Config ──
st.set_page_config(
    page_title="SafeAI — Accident & Crime Response",
    page_icon="🛡️",
    layout="wide"
)

# ── CSS ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Barlow+Condensed:wght@600;700;800&display=swap');

html, body, [class*="css"] {
    background-color: #070b12;
    color: #c9d1d9;
}

/* Header */
.main-header {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 2.8rem;
    font-weight: 800;
    letter-spacing: 4px;
    text-transform: uppercase;
    text-align: center;
    background: linear-gradient(90deg, #ff4444, #ff8800, #00cfff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: none;
    margin-bottom: 2px;
}
.sub-header {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.78rem;
    color: #3d5166;
    text-align: center;
    letter-spacing: 3px;
    margin-bottom: 18px;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    background: #0d1117;
    border-radius: 8px;
    padding: 4px;
    gap: 4px;
    border: 1px solid #1a2a3a;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: 2px;
    color: #546e7a;
    border-radius: 6px;
    padding: 8px 24px;
}
.stTabs [aria-selected="true"] {
    background: #0d1f2d !important;
    color: #00cfff !important;
    border-bottom: 2px solid #00cfff !important;
}

/* Cards */
.event-card {
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 8px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.78rem;
    border-left: 3px solid;
}
.card-accident  { background:#1a0505; border-color:#ff1744; color:#ff8a80; }
.card-CRITICAL  { background:#1a0000; border-color:#ff1744; color:#ff6b6b; }
.card-HIGH      { background:#1a0900; border-color:#ff6d00; color:#ffb74d; }
.card-MEDIUM    { background:#141200; border-color:#ffd600; color:#fff176; }
.card-ok        { background:#001a08; border-color:#00e676; color:#69f0ae; }

/* Stat boxes */
.stat-box {
    background: #0d1117;
    border: 1px solid #1e2d3d;
    border-radius: 8px;
    padding: 12px 8px;
    text-align: center;
    font-family: 'Barlow Condensed', sans-serif;
}
.stat-num   { font-size: 1.9rem; font-weight: 700; }
.stat-lbl   { font-size: 0.68rem; color: #3d5166; letter-spacing: 1px; text-transform: uppercase; }

/* Status bar */
.status-ok  { background:#001a08; border:1px solid #1a3a20; border-radius:6px; padding:6px 12px;
              font-family:'Share Tech Mono',monospace; font-size:0.75rem; color:#4caf50; }
.status-err { background:#1a0000; border:1px solid #3a1010; border-radius:6px; padding:6px 12px;
              font-family:'Share Tech Mono',monospace; font-size:0.75rem; color:#ff5252;
              animation: blink 0.8s step-start infinite; }
@keyframes blink { 50% { opacity: 0.4; } }

/* Sidebar */
div[data-testid="stSidebar"] {
    background: #050810;
    border-right: 1px solid #0d1f2d;
}

/* Divider */
.divider { border: none; border-top: 1px solid #1a2a3a; margin: 12px 0; }
</style>
""", unsafe_allow_html=True)

# ── Header ──
st.markdown('<div class="main-header">🛡️ SafeAI — Emergency Response System</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">ACCIDENT DETECTION · CRIME SURVEILLANCE · AUTOMATED ALERTS</div>', unsafe_allow_html=True)
st.markdown("<hr style='border-color:#1a2a3a; margin-bottom:16px;'>", unsafe_allow_html=True)

# ── Sidebar ──
st.sidebar.markdown("## ⚙️ Control Panel")
source = st.sidebar.radio("Video Source", ["Upload Video", "Webcam"])
confidence = st.sidebar.slider("Detection Confidence", 0.15, 0.85, 0.28)

st.sidebar.markdown("<hr class='divider'>", unsafe_allow_html=True)
st.sidebar.markdown("### 🔍 Crime Modules")
enable_fight  = st.sidebar.checkbox("👊 Fight Detection",     value=True)
enable_weapon = st.sidebar.checkbox("⚔️ Weapon Detection",    value=True)
enable_theft  = st.sidebar.checkbox("🚨 Theft Pattern",        value=True)

st.sidebar.markdown("<hr class='divider'>", unsafe_allow_html=True)
st.sidebar.markdown("### 📞 Emergency Contacts")
st.sidebar.success("🚑 Ambulance: Configured")
st.sidebar.success("🏥 Hospital: Configured")
st.sidebar.success("👮 Police: Configured")

# ── Session State ──
def init_state():
    defaults = {
        "accident_count": 0,
        "crime_counts": {"FIGHT_DETECTED": 0, "WEAPON_DETECTED": 0, "THEFT_PATTERN": 0},
        "event_log": [],       # unified log for both tabs
        "alert_results": {},
        "crime_alerts": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ── TABS ──
tab_accident, tab_crime, tab_log = st.tabs([
    "🚨  ACCIDENT DETECTION",
    "🔍  CRIME SURVEILLANCE",
    "📋  EVENT LOG"
])


# ═══════════════════════════════════════════
# TAB 1 — ACCIDENT DETECTION
# ═══════════════════════════════════════════
with tab_accident:
    col_feed, col_right = st.columns([2, 1])

    with col_feed:
        st.markdown("#### 📹 Live Feed")
        acc_video    = st.empty()
        acc_status   = st.empty()

    with col_right:
        st.markdown("#### 📊 Response Status")
        acc_alerts   = st.empty()

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)
        st.markdown("#### 🚗 Vehicles Detected")
        acc_vehicles = st.empty()

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)
        st.markdown("#### 📍 Location")
        st.markdown("""
            **Pimpri-Chinchwad, Pune, Maharashtra**
            📌 [Open in Google Maps](https://maps.google.com/?q=18.6298,73.7997)
        """)

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)
        st.markdown("#### 🔢 Session Stats")
        sc1, sc2 = st.columns(2)
        acc_stat_count  = sc1.empty()
        acc_stat_alerts = sc2.empty()

    def render_acc_stats():
        acc_stat_count.markdown(f"""<div class="stat-box">
            <div class="stat-num" style="color:#ff4444">{st.session_state.accident_count}</div>
            <div class="stat-lbl">Accidents</div></div>""", unsafe_allow_html=True)
        sent = len([e for e in st.session_state.event_log if e.get("category") == "accident"])
        acc_stat_alerts.markdown(f"""<div class="stat-box">
            <div class="stat-num" style="color:#ff8800">{sent}</div>
            <div class="stat-lbl">Alerts Sent</div></div>""", unsafe_allow_html=True)

    def render_acc_alert_status():
        r = st.session_state.alert_results
        if not r:
            acc_alerts.markdown("<p style='color:#3d5166;font-size:0.8rem;font-family:monospace'>Waiting for detection...</p>",
                               unsafe_allow_html=True)
            return
        icons = {"sms": "📱 SMS", "call": "📞 Voice Call",
                 "hospital_email": "🏥 Hospital", "police_email": "👮 Police"}
        html = ""
        for k, v in r.items():
            cls = "card-ok" if v else "card-CRITICAL"
            label = icons.get(k, k)
            status = "SENT ✅" if v else "FAILED ❌"
            html += f'<div class="event-card {cls}"><b>{label}</b> — {status}</div>'
        acc_alerts.markdown(html, unsafe_allow_html=True)

    render_acc_stats()
    render_acc_alert_status()

    if source == "Upload Video":
        uploaded_acc = st.sidebar.file_uploader("📂 Upload accident video", type=["mp4","avi","mov"], key="acc_upload")
        if uploaded_acc:
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tfile.write(uploaded_acc.read())
            tfile.close()
            st.sidebar.success("✅ Video loaded!")

            if st.sidebar.button("▶️ Start Accident Detection", key="acc_start"):
                st.session_state.accident_count = 0
                st.session_state.alert_results  = {}

                def on_accident(frame, vehicles, snapshot_path):
                    st.session_state.accident_count += 1
                    results = trigger_all_alerts(vehicles, snapshot_path)
                    st.session_state.alert_results = results
                    st.session_state.event_log.append({
                        "category": "accident",
                        "label": "🚨 Road Accident",
                        "detail": f"{len(vehicles)} vehicle(s) involved",
                        "severity": "CRITICAL",
                        "time": datetime.now().strftime("%H:%M:%S")
                    })

                for annotated, accident, vehicles in run_on_video(tfile.name, on_accident):
                    rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                    acc_video.image(rgb, channels="RGB", use_column_width=True)

                    if accident:
                        acc_status.markdown('<div class="status-err">🔴 ACCIDENT DETECTED — ALL UNITS ALERTED</div>',
                                           unsafe_allow_html=True)
                    else:
                        acc_status.markdown('<div class="status-ok">● MONITORING — No accident detected</div>',
                                           unsafe_allow_html=True)

                    if vehicles:
                        acc_vehicles.markdown(
                            "\n".join([f"**{v['type'].upper()}** — conf: `{v['confidence']}`" for v in vehicles])
                        )

                    render_acc_stats()
                    render_acc_alert_status()
                    time.sleep(0.03)

    elif source == "Webcam":
        if st.sidebar.button("▶️ Start Webcam", key="acc_webcam"):
            cap = cv2.VideoCapture(0)
            alert_sent = False
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret: break
                accident, vehicles, annotated = detect_accident(frame, confidence)
                rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                acc_video.image(rgb, channels="RGB", use_column_width=True)
                if accident and not alert_sent:
                    snap = save_snapshot(annotated)
                    results = trigger_all_alerts(vehicles, snap)
                    st.session_state.alert_results = results
                    st.session_state.accident_count += 1
                    alert_sent = True
                render_acc_stats()
                render_acc_alert_status()
                time.sleep(0.03)
            cap.release()


# ═══════════════════════════════════════════
# TAB 2 — CRIME SURVEILLANCE
# ═══════════════════════════════════════════
with tab_crime:
    cr_col_feed, cr_col_right = st.columns([2, 1])

    with cr_col_feed:
        st.markdown("#### 📹 Surveillance Feed")
        cr_video  = st.empty()
        cr_status = st.empty()

    with cr_col_right:
        st.markdown("#### 🚨 Active Threats")
        cr_threats = st.empty()

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)
        st.markdown("#### 📊 Crime Stats")
        cc1, cc2, cc3 = st.columns(3)
        cr_fights   = cc1.empty()
        cr_weapons  = cc2.empty()
        cr_theft    = cc3.empty()

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)
        st.markdown("#### 📧 Police Alerts Sent")
        cr_alert_log = st.empty()

    def render_crime_stats():
        c = st.session_state.crime_counts
        cr_fights.markdown(f"""<div class="stat-box">
            <div class="stat-num" style="color:#ff6b6b">{c['FIGHT_DETECTED']}</div>
            <div class="stat-lbl">Fights</div></div>""", unsafe_allow_html=True)
        cr_weapons.markdown(f"""<div class="stat-box">
            <div class="stat-num" style="color:#ff1744">{c['WEAPON_DETECTED']}</div>
            <div class="stat-lbl">Weapons</div></div>""", unsafe_allow_html=True)
        cr_theft.markdown(f"""<div class="stat-box">
            <div class="stat-num" style="color:#ff8800">{c['THEFT_PATTERN']}</div>
            <div class="stat-lbl">Theft</div></div>""", unsafe_allow_html=True)

    def render_crime_alerts():
        if not st.session_state.crime_alerts:
            cr_alert_log.markdown("<p style='color:#3d5166;font-size:0.8rem;font-family:monospace'>No alerts sent yet</p>",
                                 unsafe_allow_html=True)
            return
        html = ""
        for a in reversed(st.session_state.crime_alerts[-4:]):
            html += f'<div class="event-card card-ok">✅ Police notified — {a}</div>'
        cr_alert_log.markdown(html, unsafe_allow_html=True)

    def render_threats(crimes):
        if not crimes:
            cr_threats.markdown("<p style='color:#3d5166;font-size:0.8rem;font-family:monospace'>No threats detected...</p>",
                               unsafe_allow_html=True)
            return
        html = ""
        for c in crimes:
            html += f"""<div class="event-card card-{c['severity']}">
                <b>{c['label']}</b><br>
                <span style='opacity:0.75'>{c['detail'][:55]}</span>
            </div>"""
        cr_threats.markdown(html, unsafe_allow_html=True)

    render_crime_stats()
    render_crime_alerts()
    render_threats([])

    def on_crime_detected(frame, crimes, snapshot_path):
        filtered = []
        for c in crimes:
            if c["type"] == "FIGHT_DETECTED"  and not enable_fight:  continue
            if c["type"] == "WEAPON_DETECTED" and not enable_weapon: continue
            if c["type"] == "THEFT_PATTERN"   and not enable_theft:  continue
            filtered.append(c)
        if not filtered:
            return
        for c in filtered:
            if c["type"] in st.session_state.crime_counts:
                st.session_state.crime_counts[c["type"]] += 1
            st.session_state.event_log.append({
                "category": "crime",
                "label":    c["label"],
                "detail":   c["detail"],
                "severity": c["severity"],
                "time":     datetime.now().strftime("%H:%M:%S")
            })
        ok = send_crime_alert_email(snapshot_path, filtered)
        if ok:
            names = ", ".join(c["type"].replace("_"," ") for c in filtered)
            st.session_state.crime_alerts.append(f"{names} @ {datetime.now().strftime('%H:%M:%S')}")

    if source == "Upload Video":
        uploaded_cr = st.sidebar.file_uploader("📂 Upload surveillance video", type=["mp4","avi","mov"], key="cr_upload")
        if uploaded_cr:
            tfile2 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tfile2.write(uploaded_cr.read())
            tfile2.close()
            st.sidebar.success("✅ Video loaded!")

            if st.sidebar.button("▶️ Start Crime Detection", key="cr_start"):
                st.session_state.crime_counts = {"FIGHT_DETECTED":0,"WEAPON_DETECTED":0,"THEFT_PATTERN":0}
                st.session_state.crime_alerts = []

                last_crimes = []
                for annotated, crime_found, crimes in run_crime_detection_on_video(tfile2.name, on_crime_detected):
                    rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                    cr_video.image(rgb, channels="RGB", use_column_width=True)

                    if crime_found:
                        names = " | ".join(c["label"] for c in crimes)
                        cr_status.markdown(f'<div class="status-err">🔴 {names}</div>', unsafe_allow_html=True)
                        last_crimes = crimes
                    else:
                        cr_status.markdown('<div class="status-ok">● MONITORING — No threats detected</div>',
                                          unsafe_allow_html=True)

                    render_threats(last_crimes if crime_found else [])
                    render_crime_stats()
                    render_crime_alerts()
                    time.sleep(0.03)

    elif source == "Webcam":
        if st.sidebar.button("▶️ Start Crime Webcam", key="cr_webcam"):
            cap2 = cv2.VideoCapture(0)
            alerted = set()
            while cap2.isOpened():
                ret, frame = cap2.read()
                if not ret: break
                crime_found, crimes, annotated = detect_crimes(frame, confidence)
                rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                cr_video.image(rgb, channels="RGB", use_column_width=True)
                for crime in crimes:
                    if crime["type"] not in alerted:
                        snap = save_crime_snapshot(annotated, crime["type"])
                        on_crime_detected(annotated, [crime], snap)
                        alerted.add(crime["type"])
                render_threats(crimes)
                render_crime_stats()
                render_crime_alerts()
                time.sleep(0.03)
            cap2.release()


# ═══════════════════════════════════════════
# TAB 3 — UNIFIED EVENT LOG
# ═══════════════════════════════════════════
with tab_log:
    st.markdown("#### 📋 All Events — Accident & Crime Log")

    # Summary stats row
    s1, s2, s3, s4, s5 = st.columns(5)
    total = len(st.session_state.event_log)
    accidents = len([e for e in st.session_state.event_log if e.get("category") == "accident"])
    crimes    = len([e for e in st.session_state.event_log if e.get("category") == "crime"])
    critical  = len([e for e in st.session_state.event_log if e.get("severity") == "CRITICAL"])
    alerts    = accidents + len(st.session_state.crime_alerts)

    for col, num, lbl, color in [
        (s1, total,     "Total Events",  "#00cfff"),
        (s2, accidents, "Accidents",     "#ff4444"),
        (s3, crimes,    "Crimes",        "#ff8800"),
        (s4, critical,  "Critical",      "#ff1744"),
        (s5, alerts,    "Alerts Sent",   "#00e676"),
    ]:
        col.markdown(f"""<div class="stat-box">
            <div class="stat-num" style="color:{color}">{num}</div>
            <div class="stat-lbl">{lbl}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if not st.session_state.event_log:
        st.markdown("<p style='color:#3d5166;font-family:monospace'>No events recorded yet. Start detection in the tabs above.</p>",
                   unsafe_allow_html=True)
    else:
        for entry in reversed(st.session_state.event_log):
            cat_icon = "🚨" if entry.get("category") == "accident" else "🔍"
            sev = entry.get("severity", "MEDIUM")
            card_cls = "card-accident" if entry.get("category") == "accident" else f"card-{sev}"
            st.markdown(f"""<div class="event-card {card_cls}">
                {cat_icon} <b>{entry['label']}</b>
                &nbsp;·&nbsp; <span style='opacity:0.7'>{entry['detail']}</span>
                &nbsp;·&nbsp; <span style='opacity:0.45;font-size:0.7rem'>{entry['time']}</span>
                &nbsp;·&nbsp; <span style='opacity:0.45;font-size:0.7rem'>[{sev}]</span>
            </div>""", unsafe_allow_html=True)

    if st.button("🗑️ Clear Log"):
        st.session_state.event_log = []
        st.rerun()