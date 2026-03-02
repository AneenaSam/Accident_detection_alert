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
# PAGE CONFIG
# ─────────────────────────────────────
st.set_page_config(
    page_title="GoldenResQ — Golden Hour Response",
    page_icon="🛡",
    layout="wide"
)

# ─────────────────────────────────────
# GOLDEN THEME CSS
# ─────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700;900&family=Rajdhani:wght@400;500;600;700&family=Share+Tech+Mono&family=Outfit:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }

/* ── BACKGROUND ── */
.stApp {
    background: #0a0005;
    background-image:
        radial-gradient(ellipse 130% 50% at 50% 0%, rgba(107,0,51,0.6) 0%, transparent 65%),
        radial-gradient(ellipse 60% 40% at 0% 60%, rgba(61,0,32,0.4) 0%, transparent 55%),
        radial-gradient(ellipse 50% 35% at 100% 85%, rgba(193,141,82,0.1) 0%, transparent 50%),
        repeating-linear-gradient(0deg, transparent, transparent 59px, rgba(212,168,67,0.03) 60px),
        repeating-linear-gradient(90deg, transparent, transparent 59px, rgba(212,168,67,0.02) 60px);
}
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 2rem 3rem; max-width: 100%; }

/* ── NAVBAR ── */
.g-navbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 40px; height: 72px; margin: 0 -2rem 2rem;
    background: linear-gradient(90deg, #080004 0%, #160010 20%, #280016 45%, #160010 75%, #080004 100%);
    border-bottom: 1px solid rgba(193,141,82,0.3);
    box-shadow: 0 4px 60px rgba(107,0,51,0.5), 0 1px 0 rgba(212,168,67,0.1);
    position: relative; overflow: hidden;
}
.g-navbar::before {
    content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, #C18D52 20%, #FFD700 50%, #C18D52 80%, transparent);
    opacity: 0.7;
}
.g-navbar::after {
    content: ''; position: absolute; inset: 0;
    background: radial-gradient(ellipse 40% 200% at 50% 50%, rgba(255,215,0,0.03) 0%, transparent 70%);
    pointer-events: none;
}

/* Logo */
.g-logo-wrap { display: flex; flex-direction: column; position: relative; z-index: 1; }
.g-logo-row { display: flex; align-items: center; gap: 12px; }
.g-shield {
    font-size: 28px;
    filter: drop-shadow(0 0 14px rgba(255,215,0,0.7));
    animation: shieldpulse 3s ease-in-out infinite;
}
@keyframes shieldpulse {
    0%,100% { filter: drop-shadow(0 0 8px rgba(255,215,0,0.4)); }
    50%     { filter: drop-shadow(0 0 22px rgba(255,215,0,0.9)); }
}
.g-logo {
    font-family: 'Cinzel', serif; font-size: 34px; font-weight: 900; letter-spacing: 6px;
    background: linear-gradient(135deg, #8B5E1A 0%, #C18D52 18%, #D4A843 33%, #FFF0AA 50%, #FFD700 63%, #C18D52 82%, #8B5E1A 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    line-height: 1;
}
.g-tagline {
    font-family: 'Share Tech Mono', monospace; font-size: 8px;
    color: rgba(193,141,82,0.5); letter-spacing: 4px; text-transform: uppercase;
    margin-top: 4px; margin-left: 40px;
}

/* Nav right */
.g-nav-right { display: flex; align-items: center; gap: 16px; position: relative; z-index: 1; }
.g-live-dot {
    width: 9px; height: 9px; border-radius: 50%;
    background: #FFD700; box-shadow: 0 0 14px #FFD700cc;
    animation: livepulse 1.8s infinite;
}
@keyframes livepulse {
    0%,100% { transform: scale(1); box-shadow: 0 0 14px #FFD700cc; }
    50%      { transform: scale(0.5); box-shadow: 0 0 4px #FFD70055; }
}
.g-live-txt {
    font-family: 'Share Tech Mono', monospace; font-size: 11px;
    color: #FFD700; letter-spacing: 2px; text-shadow: 0 0 10px rgba(255,215,0,0.5);
}
.g-clock {
    font-family: 'Share Tech Mono', monospace; font-size: 13px; color: #D4A843;
    background: rgba(212,168,67,0.08); border: 1px solid rgba(212,168,67,0.2);
    padding: 6px 16px; border-radius: 4px; letter-spacing: 1.5px;
}
.g-golden-badge {
    font-family: 'Rajdhani', sans-serif; font-size: 11px; font-weight: 800;
    letter-spacing: 2px; color: #0a0005; text-transform: uppercase;
    background: linear-gradient(135deg, #C18D52, #FFD700, #D4A843);
    padding: 6px 16px; border-radius: 4px;
    box-shadow: 0 2px 14px rgba(255,215,0,0.4);
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #080004 0%, #100008 60%, #080004 100%) !important;
    border-right: 1px solid rgba(193,141,82,0.15) !important;
}
[data-testid="stSidebar"] * { color: #C18D52 !important; }
[data-testid="stSidebar"] .stFileUploader section {
    background: rgba(107,0,51,0.08) !important;
    border: 1px dashed rgba(193,141,82,0.2) !important;
    border-radius: 8px !important;
}

.sb-section {
    font-family: 'Share Tech Mono', monospace; font-size: 9px;
    color: rgba(193,141,82,0.4) !important; letter-spacing: 3px;
    text-transform: uppercase; margin: 20px 0 10px;
    border-bottom: 1px solid rgba(193,141,82,0.1); padding-bottom: 6px;
}
.sb-channel {
    display: flex; align-items: center; gap: 10px;
    background: linear-gradient(135deg, #0e0008, #180010);
    border: 1px solid rgba(193,141,82,0.12); border-left: 3px solid #C18D52;
    border-radius: 6px; padding: 10px 14px; margin-bottom: 7px;
}
.sb-ch-label { font-family: 'Outfit', sans-serif; font-size: 12px; font-weight: 500; color: #C18D52 !important; flex: 1; }
.sb-ch-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: #FFD700; box-shadow: 0 0 8px #FFD700aa;
}
.sb-stat {
    background: linear-gradient(135deg, rgba(107,0,51,0.15), rgba(61,0,32,0.25));
    border: 1px solid rgba(193,141,82,0.2); border-radius: 8px;
    padding: 16px; text-align: center; margin-top: 8px;
}
.sb-stat-num {
    font-family: 'Share Tech Mono', monospace; font-size: 40px;
    background: linear-gradient(135deg, #C18D52, #FFD700, #FFF0AA);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    filter: drop-shadow(0 0 12px rgba(255,215,0,0.4));
    line-height: 1;
}
.sb-stat-label {
    font-family: 'Outfit', sans-serif; font-size: 10px;
    color: rgba(193,141,82,0.45) !important; letter-spacing: 2px; text-transform: uppercase; margin-top: 4px;
}
.sb-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(193,141,82,0.2), transparent);
    margin: 14px 0;
}

/* ── TABS ── */
[data-testid="stTabs"] button {
    font-family: 'Rajdhani', sans-serif !important; font-size: 13px !important;
    font-weight: 700 !important; letter-spacing: 2.5px !important;
    text-transform: uppercase !important; color: rgba(193,141,82,0.35) !important;
    border: none !important; padding: 14px 30px !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #FFD700 !important; border-bottom: 2px solid #C18D52 !important;
    background: transparent !important; text-shadow: 0 0 12px rgba(255,215,0,0.4) !important;
}
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: #080004 !important; border-bottom: 1px solid rgba(193,141,82,0.12) !important;
    gap: 4px !important;
}

/* ── SECTION HEADERS ── */
.g-sec-hdr {
    font-family: 'Rajdhani', sans-serif; font-size: 11px; font-weight: 700;
    letter-spacing: 3px; text-transform: uppercase; color: rgba(193,141,82,0.55);
    padding-bottom: 10px; border-bottom: 1px solid rgba(193,141,82,0.1); margin-bottom: 16px;
    display: flex; align-items: center; gap: 8px;
}

/* ── FEED IDLE STATE ── */
.g-feed-idle {
    background: linear-gradient(135deg, #080004, #110009, #080004);
    border: 1px dashed rgba(193,141,82,0.18); border-radius: 12px; height: 340px;
    display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 14px;
}
.g-feed-icon { font-size: 42px; opacity: 0.15; }
.g-feed-txt {
    font-family: 'Share Tech Mono', monospace; font-size: 10px;
    color: rgba(193,141,82,0.28); letter-spacing: 4px; text-transform: uppercase;
}

/* ── STATUS PILL ── */
.g-status {
    display: flex; align-items: center; justify-content: center; gap: 10px;
    padding: 12px; border-radius: 8px; margin-top: 12px; width: 100%;
    font-family: 'Rajdhani', sans-serif; font-size: 14px; font-weight: 700;
    letter-spacing: 2px; text-transform: uppercase;
}
.g-status.ready {
    background: rgba(61,0,32,0.25); border: 1px solid rgba(107,0,51,0.45); color: #9e4060;
}
.g-status.danger {
    background: rgba(193,141,82,0.1); border: 1px solid rgba(255,215,0,0.5); color: #FFD700;
    animation: dangerpulse 0.7s infinite alternate;
}
@keyframes dangerpulse {
    from { background: rgba(193,141,82,0.06); box-shadow: none; }
    to   { background: rgba(193,141,82,0.2); box-shadow: 0 0 32px rgba(255,215,0,0.2); }
}

/* ── ALERT PANEL ── */
.g-alert-panel {
    background: linear-gradient(135deg, #080004, #110009);
    border: 1px solid rgba(193,141,82,0.18); border-radius: 10px;
    padding: 18px; min-height: 220px;
}
.g-case-id {
    font-family: 'Share Tech Mono', monospace; font-size: 10px;
    color: rgba(193,141,82,0.35); letter-spacing: 2px; text-transform: uppercase; margin-bottom: 14px;
}
.g-alert-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 11px 14px; margin-bottom: 8px; border-radius: 7px;
    background: rgba(107,0,51,0.1); border: 1px solid rgba(193,141,82,0.07);
}
.g-alert-row.ok   { border-left: 3px solid #C18D52; }
.g-alert-row.fail { border-left: 3px solid rgba(107,0,51,0.5); }
.g-alert-label {
    font-family: 'Outfit', sans-serif; font-size: 13px; font-weight: 500;
    color: #C18D52; display: flex; align-items: center; gap: 8px;
}
.g-alert-badge {
    font-family: 'Share Tech Mono', monospace; font-size: 9px;
    letter-spacing: 1.5px; padding: 3px 10px; border-radius: 20px;
}
.g-alert-badge.ok   { background: rgba(255,215,0,0.1); border: 1px solid rgba(255,215,0,0.3); color: #FFD700; }
.g-alert-badge.fail { background: rgba(107,0,51,0.2); border: 1px solid rgba(155,25,66,0.3); color: #c06080; }
.g-alert-idle {
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; padding: 60px 20px; gap: 12px;
}
.g-alert-idle-icon { font-size: 32px; opacity: 0.13; }
.g-alert-idle-txt {
    font-family: 'Share Tech Mono', monospace; font-size: 10px;
    color: rgba(193,141,82,0.28); letter-spacing: 2.5px; text-transform: uppercase;
}

/* ── EVENT LOG CARDS ── */
.g-event-card {
    background: linear-gradient(135deg, #080004, #120008, #180010, #100008, #080004);
    border: 1px solid rgba(193,141,82,0.2); border-left: 5px solid #C18D52;
    border-radius: 0 12px 12px 0; padding: 20px 24px 18px;
    margin-bottom: 14px; position: relative; overflow: hidden;
    box-shadow: 0 6px 32px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.02);
    animation: cardslide 0.4s cubic-bezier(.2,.8,.4,1);
}
@keyframes cardslide {
    from { opacity: 0; transform: translateX(-12px); }
    to   { opacity: 1; transform: translateX(0); }
}
.g-event-card::before {
    content: ''; position: absolute; top: 0; left: 5px; right: 0; height: 1px;
    background: linear-gradient(90deg, #FFD70055, rgba(193,141,82,0.1), transparent);
}
.g-event-card::after {
    content: ''; position: absolute; top: 0; right: 0; width: 180px; height: 100%;
    background: radial-gradient(ellipse at right, rgba(107,0,51,0.1) 0%, transparent 70%);
    pointer-events: none;
}
.g-ev-num {
    position: absolute; top: 14px; right: 18px;
    font-family: 'Share Tech Mono', monospace; font-size: 11px;
    color: rgba(193,141,82,0.18); letter-spacing: 1px;
}
.g-ev-head { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 10px; }
.g-ev-emoji { font-size: 28px; margin-top: 2px; filter: drop-shadow(0 0 8px rgba(255,215,0,0.35)); }
.g-ev-title {
    font-family: 'Cinzel', serif; font-size: 17px; font-weight: 700; letter-spacing: 2px;
    background: linear-gradient(135deg, #8B5E1A, #C18D52, #D4A843, #FFF0AA, #FFD700, #D4A843);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    text-transform: uppercase; margin-bottom: 5px;
}
.g-ev-sev {
    display: inline-block; font-family: 'Outfit', sans-serif; font-size: 9px; font-weight: 700;
    letter-spacing: 2px; padding: 2px 12px; border-radius: 20px;
    background: rgba(107,0,51,0.3); border: 1px solid rgba(155,25,66,0.4);
    color: #c06080; -webkit-text-fill-color: #c06080;
}
.g-ev-rule {
    height: 1px;
    background: linear-gradient(90deg, rgba(193,141,82,0.45), rgba(107,0,51,0.15), transparent);
    margin: 10px 0;
}
.g-ev-detail {
    display: inline-flex; align-items: center; gap: 6px;
    font-family: 'Share Tech Mono', monospace; font-size: 11px; color: rgba(193,141,82,0.5);
    background: rgba(193,141,82,0.06); border: 1px solid rgba(193,141,82,0.15);
    border-radius: 4px; padding: 5px 13px; margin-bottom: 14px;
}
.g-ev-meta { display: flex; gap: 10px; flex-wrap: wrap; }
.g-ev-pill {
    display: flex; align-items: center; gap: 8px;
    background: rgba(61,0,32,0.3); border: 1px solid rgba(107,0,51,0.3);
    border-radius: 20px; padding: 6px 14px;
    font-family: 'Outfit', sans-serif; font-size: 12px; color: rgba(193,141,82,0.55);
}
.g-ev-pill b { color: #C18D52; font-weight: 600; }

/* ── LOG HEADER ── */
.g-log-hdr {
    background: linear-gradient(135deg, #080004, #130008, #1e0012, #130008, #080004);
    border: 1px solid rgba(193,141,82,0.25); border-radius: 12px;
    padding: 22px 30px; display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 20px; position: relative; overflow: hidden;
    box-shadow: 0 0 50px rgba(107,0,51,0.18), inset 0 1px 0 rgba(255,255,255,0.03);
}
.g-log-hdr::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, #C18D52, #FFD700, #FFF0AA, #FFD700, #C18D52, transparent);
}
.g-log-title {
    font-family: 'Cinzel', serif; font-size: 20px; font-weight: 900; letter-spacing: 4px;
    background: linear-gradient(135deg, #8B5E1A, #C18D52, #D4A843, #FFF0AA, #FFD700, #D4A843);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    text-transform: uppercase;
}
.g-log-count-box {
    background: rgba(193,141,82,0.08); border: 1px solid rgba(193,141,82,0.3);
    border-radius: 10px; padding: 10px 28px; text-align: center;
}
.g-log-count-num {
    font-family: 'Share Tech Mono', monospace; font-size: 44px; line-height: 1;
    background: linear-gradient(135deg, #C18D52, #FFD700, #FFF0AA);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    filter: drop-shadow(0 0 14px rgba(255,215,0,0.4));
}
.g-log-count-lbl {
    font-family: 'Outfit', sans-serif; font-size: 9px;
    color: rgba(193,141,82,0.45); letter-spacing: 3px; text-transform: uppercase; margin-top: 3px;
}

/* ── EMPTY LOG ── */
.g-log-empty {
    text-align: center; padding: 80px 20px;
    border: 1px dashed rgba(193,141,82,0.15); border-radius: 12px;
    background: linear-gradient(135deg, #080004, #110009);
}
.g-log-empty-icon { font-size: 52px; opacity: 0.12; margin-bottom: 18px; }
.g-log-empty-txt {
    font-family: 'Share Tech Mono', monospace; font-size: 11px;
    color: rgba(193,141,82,0.3); letter-spacing: 3px; text-transform: uppercase; line-height: 2.4;
}

/* ── BUTTONS ── */
[data-testid="stButton"] button {
    background: linear-gradient(135deg, #110009, #1c0010) !important;
    border: 1px solid rgba(193,141,82,0.3) !important; color: #D4A843 !important;
    font-family: 'Rajdhani', sans-serif !important; font-size: 13px !important;
    font-weight: 700 !important; letter-spacing: 2px !important;
    text-transform: uppercase !important; border-radius: 6px !important;
    transition: all 0.2s !important;
}
[data-testid="stButton"] button:hover {
    background: linear-gradient(135deg, #1c0010, #2c0018) !important;
    border-color: #FFD700 !important; color: #FFD700 !important;
    box-shadow: 0 0 20px rgba(255,215,0,0.2) !important;
}

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #080004; }
::-webkit-scrollbar-thumb { background: #3D0020; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #C18D52; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────
# ACCEPTANCE HANDLER
# ─────────────────────────────────────
params = st.query_params

if "case_id" in params and "hospital" in params:
    case_id = params.get("case_id")
    hospital = params.get("hospital")
    if isinstance(case_id, list): case_id = case_id[0]
    if isinstance(hospital, list): hospital = hospital[0]

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
# AUDIO
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
            f'<source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>',
            unsafe_allow_html=True
        )

# ─────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────
for _k, _v in {"alert_results": {}, "event_log": []}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─────────────────────────────────────
# NAVBAR
# ─────────────────────────────────────
now_str = datetime.now().strftime("%d %b %Y  %H:%M")
st.markdown(f"""
<div class="g-navbar">
    <div class="g-logo-wrap">
        <div class="g-logo-row">
            <span class="g-shield">🛡</span>
            <span class="g-logo">GoldenResQ</span>
        </div>
        <div class="g-tagline">Real-Time Accident Detection · Emergency Dispatch · Golden Hour Response</div>
    </div>
    <div class="g-nav-right">
        <div style="display:flex;align-items:center;gap:8px;">
            <div class="g-live-dot"></div>
            <span class="g-live-txt">SYSTEM LIVE</span>
        </div>
        <div class="g-clock">{now_str}</div>
        <div class="g-golden-badge">⏱ GOLDEN HOUR</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────
total = len(st.session_state.event_log)

st.sidebar.markdown('<div class="sb-section">📁 Video Source</div>', unsafe_allow_html=True)
uploaded = st.sidebar.file_uploader("Upload accident video", type=["mp4", "avi"], label_visibility="collapsed")

st.sidebar.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="sb-section">📞 Emergency Channels</div>', unsafe_allow_html=True)
st.sidebar.markdown("""
<div class="sb-channel">
    <span>🚑</span>
    <span class="sb-ch-label">Ambulance Dispatch</span>
    <div class="sb-ch-dot"></div>
</div>
<div class="sb-channel">
    <span>🏥</span>
    <span class="sb-ch-label">Multi-Hospital Network</span>
    <div class="sb-ch-dot"></div>
</div>
<div class="sb-channel">
    <span>👮</span>
    <span class="sb-ch-label">Police Control Room</span>
    <div class="sb-ch-dot"></div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="sb-section">📊 Session Stats</div>', unsafe_allow_html=True)
st.sidebar.markdown(f"""
<div class="sb-stat">
    <div class="sb-stat-num">{total}</div>
    <div class="sb-stat-label">Total Incidents</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────
# TABS
# ─────────────────────────────────────
tab_detect, tab_log = st.tabs(["🚨  Accident Detection", "📋  Event Log"])

# ═══════════════════════════════════════
# TAB 1 — DETECTION
# ═══════════════════════════════════════
with tab_detect:
    col_feed, col_status = st.columns([3, 2], gap="medium")

    with col_feed:
        st.markdown('<div class="g-sec-hdr">📹 Live Detection Feed</div>', unsafe_allow_html=True)
        video_slot = st.empty()
        status_slot = st.empty()

        video_slot.markdown("""
        <div class="g-feed-idle">
            <div class="g-feed-icon">🎥</div>
            <div class="g-feed-txt">Awaiting video input...</div>
        </div>
        """, unsafe_allow_html=True)

        status_slot.markdown(
            '<div class="g-status ready">📡 System Monitoring — Ready</div>',
            unsafe_allow_html=True
        )

    with col_status:
        st.markdown('<div class="g-sec-hdr">📡 Alert Dispatch Status</div>', unsafe_allow_html=True)
        alert_slot = st.empty()

        def render_alerts():
            r = st.session_state.alert_results
            if not r:
                alert_slot.markdown("""
                <div class="g-alert-panel">
                    <div class="g-alert-idle">
                        <div class="g-alert-idle-icon">📡</div>
                        <div class="g-alert-idle-txt">Waiting for incident...</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                return

            channels = [
                ("📱", "SMS Alert",    r.get("sms")),
                ("📞", "Voice Call",   r.get("call")),
                ("👮", "Police Email", r.get("police_email")),
            ]
            rows = ""
            for icon, label, ok in channels:
                cls = "ok" if ok else "fail"
                badge = "DISPATCHED" if ok else "FAILED"
                rows += f"""
                <div class="g-alert-row {cls}">
                    <span class="g-alert-label">{icon}&nbsp; {label}</span>
                    <span class="g-alert-badge {cls}">{badge}</span>
                </div>"""

            for name, ok in r.get("hospitals", {}).items():
                cls = "ok" if ok else "fail"
                badge = "DISPATCHED" if ok else "FAILED"
                rows += f"""
                <div class="g-alert-row {cls}">
                    <span class="g-alert-label">🏥&nbsp; {name}</span>
                    <span class="g-alert-badge {cls}">{badge}</span>
                </div>"""

            components.html(f"""
            <style>
            *{{margin:0;padding:0;box-sizing:border-box;font-family:'Outfit',sans-serif;}}
            body{{background:transparent;}}
            .g-alert-panel{{background:linear-gradient(135deg,#080004,#110009);border:1px solid rgba(193,141,82,0.18);border-radius:10px;padding:18px;}}
            .g-case-id{{font-family:monospace;font-size:10px;color:rgba(193,141,82,0.35);letter-spacing:2px;text-transform:uppercase;margin-bottom:14px;}}
            .g-alert-row{{display:flex;align-items:center;justify-content:space-between;padding:11px 14px;margin-bottom:8px;border-radius:7px;background:rgba(107,0,51,0.1);border:1px solid rgba(193,141,82,0.07);}}
            .g-alert-row.ok{{border-left:3px solid #C18D52;}}
            .g-alert-row.fail{{border-left:3px solid rgba(107,0,51,0.5);}}
            .g-alert-label{{font-size:13px;font-weight:500;color:#C18D52;}}
            .g-alert-badge{{font-size:9px;letter-spacing:1.5px;padding:3px 10px;border-radius:20px;}}
            .g-alert-badge.ok{{background:rgba(255,215,0,0.1);border:1px solid rgba(255,215,0,0.3);color:#FFD700;}}
            .g-alert-badge.fail{{background:rgba(107,0,51,0.2);border:1px solid rgba(155,25,66,0.3);color:#c06080;}}
            </style>
            <div class="g-alert-panel">
                <div class="g-case-id">CASE ID &nbsp;/&nbsp; {r.get("case_id", "—")}</div>
                {rows}
            </div>
            """, height=320, scrolling=False)

        render_alerts()

    def on_accident(frame, vehicles, snapshot_path):
        results = trigger_all_alerts(vehicles, snapshot_path)
        st.session_state.alert_results = results
        play_alert()
        st.session_state.event_log.append({
            "label": "Road Accident",
            "detail": f"{len(vehicles)} vehicle(s) involved",
            "severity": "CRITICAL",
            "time": datetime.now().strftime("%H:%M:%S"),
            "date": datetime.now().strftime("%d %b %Y"),
            "location": "NH 66, Ernakulam, Kerala",
        })

    if uploaded:
        tfile = tempfile.NamedTemporaryFile(delete=False)
        tfile.write(uploaded.read())
        tfile.close()

        if st.sidebar.button("⚡  START DETECTION"):
            for annotated, accident, vehicles in run_on_video(tfile.name, on_accident):
                rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                video_slot.image(rgb, channels="RGB", use_container_width=True)

                if accident:
                    status_slot.markdown(
                        '<div class="g-status danger">🚨 INCIDENT DETECTED — DISPATCHING</div>',
                        unsafe_allow_html=True
                    )
                else:
                    status_slot.markdown(
                        '<div class="g-status ready">📡 Monitoring Feed...</div>',
                        unsafe_allow_html=True
                    )

                render_alerts()
                time.sleep(0.03)

# ═══════════════════════════════════════
# TAB 2 — EVENT LOG
# ═══════════════════════════════════════
with tab_log:

    log = st.session_state.event_log
    total = len(log)

    st.markdown(f"""
    <div class="g-log-hdr">
        <div>
            <div class="g-log-title">📋 Incident Log</div>
            <div style="font-family:'Share Tech Mono',monospace;font-size:9px;color:rgba(193,141,82,0.4);letter-spacing:2px;margin-top:6px;">
                REAL-TIME EVENT HISTORY
            </div>
        </div>
        <div class="g-log-count-box">
            <div class="g-log-count-num">{total}</div>
            <div class="g-log-count-lbl">Events</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_btn, _ = st.columns([1, 6])
    with col_btn:
        if st.button("🗑  Clear Log"):
            st.session_state.event_log = []
            st.rerun()

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

    if not log:
        st.markdown("""
        <div class="g-log-empty">
            <div class="g-log-empty-icon">📋</div>
            <div class="g-log-empty-txt">No events recorded yet.<br>Upload a video and start detection.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for i, e in enumerate(reversed(log), 1):
            num = total - i + 1
            st.markdown(f"""
            <div class="g-event-card">
                <div class="g-ev-num">#{num:03d}</div>
                <div class="g-ev-head">
                    <span class="g-ev-emoji">🚨</span>
                    <div>
                        <div class="g-ev-title">{e['label']}</div>
                        <span class="g-ev-sev">{e['severity']}</span>
                    </div>
                </div>
                <div class="g-ev-rule"></div>
                <div class="g-ev-detail">⚠ &nbsp;{e['detail']}</div>
                <div class="g-ev-meta">
                    <div class="g-ev-pill">🕐 &nbsp;<b>{e['time']}</b>&nbsp; {e.get('date','')}</div>
                    <div class="g-ev-pill">📍 &nbsp;{e.get('location','—')}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
