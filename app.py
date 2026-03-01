import streamlit as st
import cv2
import tempfile
import time
import os
import base64
from datetime import datetime
from detector import detect_accident, save_snapshot
from alert import trigger_all_alerts
from crime_detector import detect_crimes, save_crime_snapshot
from crime_alert import send_crime_alert_email

# ── Page Config ──
st.set_page_config(
    page_title="SafeAI — Unified Response System",
    page_icon="🛡️",
    layout="wide"
)

# ── CSS ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Barlow+Condensed:wght@600;700;800&display=swap');

html, body, [class*="css"] { background-color: #070b12; color: #c9d1d9; }

.main-header {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 2.8rem; font-weight: 800;
    letter-spacing: 4px; text-transform: uppercase; text-align: center;
    background: linear-gradient(90deg, #ff4444, #ff8800, #00cfff);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 2px;
}
.sub-header {
    font-family: 'Share Tech Mono', monospace; font-size: 0.78rem;
    color: #3d5166; text-align: center; letter-spacing: 3px; margin-bottom: 18px;
}
.stTabs [data-baseweb="tab-list"] {
    background: #0d1117; border-radius: 8px; padding: 4px; gap: 4px; border: 1px solid #1a2a3a;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Barlow Condensed', sans-serif; font-size: 1rem;
    font-weight: 700; letter-spacing: 2px; color: #546e7a; border-radius: 6px; padding: 8px 24px;
}
.stTabs [aria-selected="true"] {
    background: #0d1f2d !important; color: #00cfff !important; border-bottom: 2px solid #00cfff !important;
}
.event-card {
    border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;
    font-family: 'Share Tech Mono', monospace; font-size: 0.78rem; border-left: 3px solid;
}
.card-accident  { background:#1a0505; border-color:#ff1744; color:#ff8a80; }
.card-CRITICAL  { background:#1a0000; border-color:#ff1744; color:#ff6b6b; }
.card-HIGH      { background:#1a0900; border-color:#ff6d00; color:#ffb74d; }
.card-MEDIUM    { background:#141200; border-color:#ffd600; color:#fff176; }
.card-ok        { background:#001a08; border-color:#00e676; color:#69f0ae; }
.stat-box {
    background: #0d1117; border: 1px solid #1e2d3d;
    border-radius: 8px; padding: 12px 8px; text-align: center;
    font-family: 'Barlow Condensed', sans-serif;
}
.stat-num   { font-size: 1.9rem; font-weight: 700; }
.stat-lbl   { font-size: 0.68rem; color: #3d5166; letter-spacing: 1px; text-transform: uppercase; }
.status-ok  { background:#001a08; border:1px solid #1a3a20; border-radius:6px; padding:6px 12px;
              font-family:'Share Tech Mono',monospace; font-size:0.75rem; color:#4caf50; }
.status-err { background:#1a0000; border:1px solid #3a1010; border-radius:6px; padding:6px 12px;
              font-family:'Share Tech Mono',monospace; font-size:0.75rem; color:#ff5252;
              animation: blink 0.8s step-start infinite; }
@keyframes blink { 50% { opacity: 0.4; } }
div[data-testid="stSidebar"] { background: #050810; border-right: 1px solid #0d1f2d; }
.divider { border: none; border-top: 1px solid #1a2a3a; margin: 12px 0; }
</style>
""", unsafe_allow_html=True)

# ── Header ──
st.markdown('<div class="main-header">🛡️ SafeAI — Unified Response Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">ACCIDENT DETECTION · CRIME SURVEILLANCE · AUTOMATED ALERTS</div>', unsafe_allow_html=True)
st.markdown("<hr style='border-color:#1a2a3a; margin-bottom:16px;'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# AUDIO ALERT SYSTEM
# ── How it works ──
#   1. Run generate_alerts.py ONCE to create MP3 files in the audio/ folder
#   2. At app startup, each MP3 is read and stored as base64 in session state
#   3. When a detection fires, play_alert() injects a hidden <audio autoplay> tag
#      with the base64 data URI — this works reliably inside Streamlit iframes
#      unlike window.speechSynthesis or st.audio()
# ══════════════════════════════════════════════

AUDIO_FILES = {
    "accident":        "audio/accident_alert.mp3",
    "FIGHT_DETECTED":  "audio/fight_alert.mp3",
    "WEAPON_DETECTED": "audio/weapon_alert.mp3",
    "THEFT_PATTERN":   "audio/theft_alert.mp3",
}

AUDIO_MESSAGES = {
    "accident":        "Warning! Road accident detected. Dispatching ambulance immediately.",
    "FIGHT_DETECTED":  "Alert! Fight detected. Police have been notified.",
    "WEAPON_DETECTED": "Critical alert! Weapon detected on camera. Police are on the way.",
    "THEFT_PATTERN":   "Warning! Theft pattern detected. Police have been alerted.",
}

# Cache base64 audio in session state at startup
if "audio_b64" not in st.session_state:
    st.session_state.audio_b64 = {}
    for kind, path in AUDIO_FILES.items():
        if os.path.exists(path):
            with open(path, "rb") as f:
                st.session_state.audio_b64[kind] = base64.b64encode(f.read()).decode()

# Single placeholder — swapped on every alert so browser sees a new element
_audio_slot = st.empty()

def play_alert(kind: str):
    """
    Play the voice alert for this event type.
    Embeds MP3 as base64 data URI inside a hidden <audio autoplay> tag.
    This is the only method that reliably fires audio inside a Streamlit iframe.
    Falls back to a visible error banner if audio/ files haven't been generated yet.
    """
    b64 = st.session_state.audio_b64.get(kind)
    if b64:
        uid = int(time.time() * 1000)   # unique id forces browser to treat as new element
        _audio_slot.markdown(
            f'<audio id="sa_{uid}" autoplay style="display:none">'
            f'<source src="data:audio/mp3;base64,{b64}" type="audio/mp3">'
            f'</audio>',
            unsafe_allow_html=True
        )
    else:
        msg = AUDIO_MESSAGES.get(kind, "Alert detected!")
        _audio_slot.error(f"🔊 {msg}  —  *Run generate_alerts.py to enable voice*")


# ── Session State ──
def init_state():
    defaults = {
        "accident_count": 0,
        "crime_counts": {"FIGHT_DETECTED": 0, "WEAPON_DETECTED": 0, "THEFT_PATTERN": 0},
        "event_log": [],
        "alert_results": {},
        "crime_alerts": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
init_state()

# ── Sidebar ──
st.sidebar.markdown("## ⚙️ Control Panel")
confidence = 0.28

st.sidebar.markdown("<hr class='divider'>", unsafe_allow_html=True)
st.sidebar.markdown("### 🔍 Crime Modules")
enable_fight  = st.sidebar.checkbox("👊 Fight Detection",  value=True)
enable_weapon = st.sidebar.checkbox("⚔️ Weapon Detection", value=True)
enable_theft  = st.sidebar.checkbox("🚨 Theft Pattern",    value=True)

st.sidebar.markdown("<hr class='divider'>", unsafe_allow_html=True)
st.sidebar.markdown("### 📞 Emergency Contacts")
st.sidebar.success("🚑 Ambulance: Configured")
st.sidebar.success("🏥 Hospital:  Configured")
st.sidebar.success("👮 Police:    Configured")

st.sidebar.markdown("<hr class='divider'>", unsafe_allow_html=True)
st.sidebar.markdown("### 📡 Live Event Feed")
sidebar_feed = st.sidebar.empty()

def refresh_sidebar_feed():
    log = st.session_state.event_log
    if not log:
        sidebar_feed.markdown(
            "<p style='color:#3d5166;font-size:0.75rem;font-family:monospace'>No events yet...</p>",
            unsafe_allow_html=True)
        return
    html = ""
    for e in reversed(log[-6:]):
        cls = "card-accident" if e.get("category") == "accident" else f"card-{e.get('severity','MEDIUM')}"
        html += (f'<div class="event-card {cls}" style="font-size:0.7rem;padding:6px 10px;">'
                 f'<b>{e["label"]}</b><br><span style="opacity:0.6">{e["time"]}</span></div>')
    sidebar_feed.markdown(html, unsafe_allow_html=True)

refresh_sidebar_feed()

# ── TABS ──
tab_overview, tab_accident, tab_crime, tab_log = st.tabs([
    "🖥️  OVERVIEW",
    "🚨  ACCIDENT",
    "🔍  CRIME",
    "📋  EVENT LOG"
])


# ═══════════════════════════════════════════
# TAB 0 — OVERVIEW
# ═══════════════════════════════════════════
with tab_overview:
    ov_c1, ov_c2, ov_c3, ov_c4, ov_c5 = st.columns(5)
    ov_stat_total    = ov_c1.empty()
    ov_stat_accident = ov_c2.empty()
    ov_stat_fight    = ov_c3.empty()
    ov_stat_weapon   = ov_c4.empty()
    ov_stat_theft    = ov_c5.empty()

    def render_overview_stats():
        log = st.session_state.event_log
        cc  = st.session_state.crime_counts
        for col, num, lbl, color in [
            (ov_stat_total,    len(log),                        "Total Events", "#00cfff"),
            (ov_stat_accident, st.session_state.accident_count, "Accidents",    "#ff4444"),
            (ov_stat_fight,    cc["FIGHT_DETECTED"],            "Fights",       "#ff6b6b"),
            (ov_stat_weapon,   cc["WEAPON_DETECTED"],           "Weapons",      "#ff1744"),
            (ov_stat_theft,    cc["THEFT_PATTERN"],             "Theft",        "#ff8800"),
        ]:
            col.markdown(
                f'<div class="stat-box"><div class="stat-num" style="color:{color}">{num}</div>'
                f'<div class="stat-lbl">{lbl}</div></div>', unsafe_allow_html=True)

    render_overview_stats()
    st.markdown("<br>", unsafe_allow_html=True)

    ov_left, ov_right = st.columns([2, 1])
    with ov_left:
        st.markdown("#### 📹 Live Feed — Both Detectors Active")
        ov_video  = st.empty()
        ov_status = st.empty()
    with ov_right:
        st.markdown("#### 🚨 Accident Status")
        ov_acc_panel = st.empty()
        st.markdown("<hr class='divider'>", unsafe_allow_html=True)
        st.markdown("#### 🔍 Crime Threats")
        ov_crime_panel = st.empty()

    def render_ov_acc_panel(accident, vehicles):
        if accident:
            v_list = ", ".join(v["type"].upper() for v in vehicles) if vehicles else "—"
            html = f'<div class="event-card card-accident"><b>🚨 ACCIDENT DETECTED</b><br>{v_list}</div>'
        else:
            html = "<p style='color:#3d5166;font-size:0.8rem;font-family:monospace'>● No accident detected</p>"
        ov_acc_panel.markdown(html, unsafe_allow_html=True)

    def render_ov_crime_panel(crimes):
        if not crimes:
            ov_crime_panel.markdown(
                "<p style='color:#3d5166;font-size:0.8rem;font-family:monospace'>● No threats detected</p>",
                unsafe_allow_html=True)
            return
        html = ""
        for c in crimes:
            html += (f'<div class="event-card card-{c["severity"]}"><b>{c["label"]}</b><br>'
                     f'<span style="opacity:0.7">{c["detail"][:50]}</span></div>')
        ov_crime_panel.markdown(html, unsafe_allow_html=True)

    render_ov_acc_panel(False, [])
    render_ov_crime_panel([])

    # ── Upload & Start ──
    uploaded = st.sidebar.file_uploader(
        "📂 Upload video (runs both detectors)", type=["mp4","avi","mov"], key="unified_upload")

    if uploaded:
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tfile.write(uploaded.read())
        tfile.close()
        st.sidebar.success("✅ Video loaded!")

        if st.sidebar.button("▶️ Start Unified Detection", key="unified_start"):
            st.session_state.accident_count = 0
            st.session_state.alert_results  = {}
            st.session_state.crime_counts   = {"FIGHT_DETECTED":0,"WEAPON_DETECTED":0,"THEFT_PATTERN":0}
            st.session_state.crime_alerts   = []
            st.session_state.event_log      = []

            acc_alert_sent  = False
            acc_frame_count = 0
            alerted_crimes  = set()
            crime_frame_ctr = {}

            cap = cv2.VideoCapture(tfile.name)
            frame_idx = 0

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frame_idx += 1
                if frame_idx % 3 != 0:
                    continue

                # ── Run both detectors on same frame ──
                accident, vehicles, acc_annotated = detect_accident(frame, confidence)
                crime_found, crimes, cr_annotated  = detect_crimes(frame, confidence)

                crimes = [c for c in crimes if not (
                    (c["type"] == "FIGHT_DETECTED"  and not enable_fight)  or
                    (c["type"] == "WEAPON_DETECTED" and not enable_weapon) or
                    (c["type"] == "THEFT_PATTERN"   and not enable_theft)
                )]
                crime_found = len(crimes) > 0

                merged = cv2.addWeighted(acc_annotated, 0.6, cr_annotated, 0.4, 0) if crime_found else acc_annotated
                rgb = cv2.cvtColor(merged, cv2.COLOR_BGR2RGB)
                ov_video.image(rgb, channels="RGB", use_container_width=True)

                # ── Accident alert ──
                acc_frame_count = acc_frame_count + 1 if accident else max(0, acc_frame_count - 1)

                if acc_frame_count >= 2 and not acc_alert_sent:
                    snap    = save_snapshot(acc_annotated)
                    results = trigger_all_alerts(vehicles, snap)
                    st.session_state.alert_results  = results
                    st.session_state.accident_count += 1
                    acc_alert_sent = True
                    play_alert("accident")      # 🔊 "Warning! Road accident detected..."
                    st.session_state.event_log.append({
                        "category": "accident",
                        "label":    "🚨 Road Accident",
                        "detail":   f"{len(vehicles)} vehicle(s) involved",
                        "severity": "CRITICAL",
                        "time":     datetime.now().strftime("%H:%M:%S")
                    })

                # ── Crime alerts ──
                for c in crimes:
                    ctype = c["type"]
                    crime_frame_ctr[ctype] = crime_frame_ctr.get(ctype, 0) + 1

                    if crime_frame_ctr[ctype] >= 2 and ctype not in alerted_crimes:
                        snap2 = save_crime_snapshot(cr_annotated, ctype)
                        send_crime_alert_email(snap2, [c])
                        alerted_crimes.add(ctype)
                        if ctype in st.session_state.crime_counts:
                            st.session_state.crime_counts[ctype] += 1
                        st.session_state.crime_alerts.append(
                            f"{ctype.replace('_',' ')} @ {datetime.now().strftime('%H:%M:%S')}")
                        play_alert(ctype)       # 🔊 "Alert! Fight/Weapon/Theft detected..."
                        st.session_state.event_log.append({
                            "category": "crime",
                            "label":    c["label"],
                            "detail":   c["detail"],
                            "severity": c["severity"],
                            "time":     datetime.now().strftime("%H:%M:%S")
                        })

                seen = {c["type"] for c in crimes}
                for ctype in list(crime_frame_ctr):
                    if ctype not in seen:
                        crime_frame_ctr[ctype] = max(0, crime_frame_ctr[ctype] - 1)

                # ── Status bar ──
                if accident and crime_found:
                    ov_status.markdown(
                        '<div class="status-err">🔴 ACCIDENT + CRIME DETECTED — ALL UNITS ALERTED</div>',
                        unsafe_allow_html=True)
                elif accident:
                    ov_status.markdown(
                        '<div class="status-err">🔴 ACCIDENT DETECTED — AMBULANCE DISPATCHED</div>',
                        unsafe_allow_html=True)
                elif crime_found:
                    names = " | ".join(c["label"] for c in crimes)
                    ov_status.markdown(f'<div class="status-err">🔴 {names}</div>', unsafe_allow_html=True)
                else:
                    ov_status.markdown(
                        '<div class="status-ok">● ALL CLEAR — Monitoring active</div>',
                        unsafe_allow_html=True)

                render_ov_acc_panel(accident, vehicles)
                render_ov_crime_panel(crimes if crime_found else [])
                render_overview_stats()
                refresh_sidebar_feed()
                time.sleep(0.03)

            cap.release()
            ov_status.markdown('<div class="status-ok">✅ Analysis complete</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════
# TAB 1 — ACCIDENT DETAIL
# ═══════════════════════════════════════════
with tab_accident:
    st.markdown("#### 🚨 Accident Detection — Detail")
    st.info("▶️ Start detection from the Overview tab. Stats update live.")

    a1, a2, a3 = st.columns(3)
    for col, num, lbl, color in [
        (a1, st.session_state.accident_count, "Accidents Detected", "#ff4444"),
        (a2, len([e for e in st.session_state.event_log if e.get("category") == "accident"]), "Events Logged", "#ff8800"),
        (a3, len(st.session_state.alert_results), "Alert Channels", "#00cfff"),
    ]:
        col.markdown(
            f'<div class="stat-box"><div class="stat-num" style="color:{color}">{num}</div>'
            f'<div class="stat-lbl">{lbl}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>")
    st.markdown("#### 📊 Last Alert Response")
    r = st.session_state.alert_results
    if not r:
        st.markdown("<p style='color:#3d5166;font-family:monospace'>No alerts sent yet.</p>", unsafe_allow_html=True)
    else:
        icons = {"sms":"📱 SMS","call":"📞 Voice Call","hospital_email":"🏥 Hospital","police_email":"👮 Police"}
        for k, v in r.items():
            cls = "card-ok" if v else "card-CRITICAL"
            st.markdown(
                f'<div class="event-card {cls}"><b>{icons.get(k,k)}</b> — {"SENT ✅" if v else "FAILED ❌"}</div>',
                unsafe_allow_html=True)

    st.markdown("<br>")
    st.markdown("#### 📍 Monitored Location")
    st.markdown("**NH 66, Ernakulam, Kerala** — 📌 [Open in Google Maps](https://maps.google.com/?q=10.0159,76.3419)")


# ═══════════════════════════════════════════
# TAB 2 — CRIME DETAIL
# ═══════════════════════════════════════════
with tab_crime:
    st.markdown("#### 🔍 Crime Surveillance — Detail")
    st.info("▶️ Start detection from the Overview tab. Stats update live.")

    cc = st.session_state.crime_counts
    c1, c2, c3 = st.columns(3)
    for col, num, lbl, color in [
        (c1, cc["FIGHT_DETECTED"],  "Fights",  "#ff6b6b"),
        (c2, cc["WEAPON_DETECTED"], "Weapons", "#ff1744"),
        (c3, cc["THEFT_PATTERN"],   "Theft",   "#ff8800"),
    ]:
        col.markdown(
            f'<div class="stat-box"><div class="stat-num" style="color:{color}">{num}</div>'
            f'<div class="stat-lbl">{lbl}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>")
    st.markdown("#### 📧 Police Alerts Sent")
    if not st.session_state.crime_alerts:
        st.markdown("<p style='color:#3d5166;font-family:monospace'>No alerts sent yet.</p>", unsafe_allow_html=True)
    else:
        for a in reversed(st.session_state.crime_alerts[-8:]):
            st.markdown(f'<div class="event-card card-ok">✅ Police notified — {a}</div>', unsafe_allow_html=True)

    st.markdown("<br>")
    st.markdown("#### 📍 Surveillance Zone")
    st.markdown("**Pimpri-Chinchwad, Pune, Maharashtra** — 📌 [Open in Google Maps](https://maps.google.com/?q=18.6298,73.7997)")


# ═══════════════════════════════════════════
# TAB 3 — UNIFIED EVENT LOG
# ═══════════════════════════════════════════
with tab_log:
    st.markdown("#### 📋 Unified Event Log — Accidents & Crimes")

    s1, s2, s3, s4, s5 = st.columns(5)
    log   = st.session_state.event_log
    accs  = len([e for e in log if e.get("category") == "accident"])
    crms  = len([e for e in log if e.get("category") == "crime"])
    crit  = len([e for e in log if e.get("severity") == "CRITICAL"])
    alrts = accs + len(st.session_state.crime_alerts)

    for col, num, lbl, color in [
        (s1, len(log), "Total Events", "#00cfff"),
        (s2, accs,     "Accidents",    "#ff4444"),
        (s3, crms,     "Crimes",       "#ff8800"),
        (s4, crit,     "Critical",     "#ff1744"),
        (s5, alrts,    "Alerts Sent",  "#00e676"),
    ]:
        col.markdown(
            f'<div class="stat-box"><div class="stat-num" style="color:{color}">{num}</div>'
            f'<div class="stat-lbl">{lbl}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>")
    if not log:
        st.markdown(
            "<p style='color:#3d5166;font-family:monospace'>No events recorded yet.</p>",
            unsafe_allow_html=True)
    else:
        for entry in reversed(log):
            cat_icon = "🚨" if entry.get("category") == "accident" else "🔍"
            sev      = entry.get("severity", "MEDIUM")
            card_cls = "card-accident" if entry.get("category") == "accident" else f"card-{sev}"
            st.markdown(
                f'<div class="event-card {card_cls}">{cat_icon} <b>{entry["label"]}</b>'
                f'&nbsp;·&nbsp;<span style="opacity:0.7">{entry["detail"]}</span>'
                f'&nbsp;·&nbsp;<span style="opacity:0.45;font-size:0.7rem">{entry["time"]}</span>'
                f'&nbsp;·&nbsp;<span style="opacity:0.45;font-size:0.7rem">[{sev}]</span></div>',
                unsafe_allow_html=True)

    if st.button("🗑️ Clear Log"):
        st.session_state.event_log      = []
        st.session_state.accident_count = 0
        st.session_state.alert_results  = {}
        st.session_state.crime_counts   = {"FIGHT_DETECTED":0,"WEAPON_DETECTED":0,"THEFT_PATTERN":0}
        st.session_state.crime_alerts   = []
        st.rerun()