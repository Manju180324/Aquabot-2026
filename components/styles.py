import streamlit as st


THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
:root { --ink:#e7f7ff; --muted:#89adbf; --cyan:#59e1e8; --blue:#4e91ff; --panel:rgba(7,28,47,.82); }
html, body, [class*="css"], [data-testid="stApp"] { font-family:'Manrope',sans-serif; }
.stApp { color:var(--ink); background:radial-gradient(ellipse at 75% -10%,#134466 0%,transparent 42%),radial-gradient(ellipse at 0% 50%,#092a43 0%,transparent 55%),linear-gradient(140deg,#061522 0%,#071b2b 50%,#03111d 100%); }
[data-testid="stHeader"] { background:rgba(0,0,0,0); }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#071827,#06121e); border-right:1px solid rgba(89,225,232,.15); }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:#b9d1df; }
.block-container { padding-top:1.55rem; padding-bottom:2.5rem; max-width:1600px; }
h1,h2,h3 { letter-spacing:-.04em; }
h1 { font-weight:800; }
[data-testid="stMetric"] { background:linear-gradient(145deg,rgba(13,49,72,.88),rgba(7,30,48,.84)); border:1px solid rgba(107,201,220,.16); border-radius:16px; padding:16px 18px; box-shadow:0 12px 35px rgba(0,0,0,.14); transition:transform .2s ease,border-color .2s ease; }
[data-testid="stMetric"]:hover { transform:translateY(-2px); border-color:rgba(89,225,232,.55); }
[data-testid="stMetricLabel"] { color:#91b3c5!important; }
[data-testid="stMetricValue"] { color:#effbff; }
.stButton>button,.stDownloadButton>button { border:1px solid rgba(89,225,232,.34); border-radius:10px; background:linear-gradient(110deg,#0d5773,#126c82); color:#f1fcff; font-weight:700; transition:all .18s ease; }
.stButton>button:hover,.stDownloadButton>button:hover { border-color:#67f0ed; box-shadow:0 0 18px rgba(64,213,225,.2); transform:translateY(-1px); color:white; }
[data-testid="stDataFrame"], [data-testid="stPlotlyChart"] { border:1px solid rgba(105,185,208,.14); border-radius:15px; overflow:hidden; background:rgba(5,22,36,.5); }
hr { border-color:rgba(124,190,211,.13); }
.eyebrow { color:#59e1e8; text-transform:uppercase; letter-spacing:.18em; font:500 11px 'DM Mono',monospace; }
.hero { border:1px solid rgba(89,225,232,.2); border-radius:20px; padding:22px 24px; background:linear-gradient(115deg,rgba(10,55,77,.86),rgba(8,28,47,.82)); box-shadow:0 18px 48px rgba(0,0,0,.18); position:relative; overflow:hidden; }
.hero:after { content:''; position:absolute; width:240px;height:240px;right:-70px;top:-115px;border-radius:50%;background:radial-gradient(circle,rgba(56,213,229,.18),transparent 68%);pointer-events:none; }
.status-pill { display:inline-flex; align-items:center; gap:8px; border:1px solid rgba(89,225,232,.28); color:#9af7ed; background:rgba(28,154,158,.12); padding:6px 11px; border-radius:99px; font:500 11px 'DM Mono',monospace; letter-spacing:.06em; }
.status-dot { width:7px;height:7px;border-radius:50%;background:#61edd3;box-shadow:0 0 10px #61edd3; }
.panel { border:1px solid rgba(105,185,208,.15); border-radius:16px; padding:16px 18px; background:var(--panel); }
.sensor-card { border:1px solid rgba(105,185,208,.16); border-radius:15px; padding:15px; background:linear-gradient(145deg,rgba(12,43,64,.85),rgba(6,25,41,.85)); min-height:118px; }
.sensor-name { color:#92b7c8; font-size:12px; letter-spacing:.04em; text-transform:uppercase; }
.sensor-value { color:#edfbff; font-size:25px; font-weight:800; margin-top:9px; }
.sensor-unit { color:#71c7d4; font:11px 'DM Mono',monospace; }
.pipeline-stage { border:1px solid rgba(105,185,208,.17); border-radius:13px; padding:14px; background:rgba(7,31,49,.78); min-height:117px; }
.pipeline-stage.active { border-color:rgba(89,225,232,.58); box-shadow:0 0 22px rgba(60,200,215,.12); }
.pipeline-stage.pending { opacity:.62; }
.bubble { position:fixed; bottom:-50px; width:8px;height:8px;border-radius:50%;background:rgba(96,225,238,.18);border:1px solid rgba(117,235,241,.26); animation:rise 13s linear infinite; pointer-events:none; z-index:0; }
.bubble.b2 { left:82%; width:12px;height:12px;animation-delay:4s;animation-duration:17s; }
.bubble.b3 { left:56%; width:5px;height:5px;animation-delay:8s;animation-duration:15s; }
@keyframes rise { from { transform:translateY(0) translateX(0);opacity:0 } 15%{opacity:.55} 80%{opacity:.35} to { transform:translateY(-110vh) translateX(34px);opacity:0 } }
@media (max-width:760px) { .block-container { padding-left:1rem;padding-right:1rem; } .hero { padding:17px; } }
</style>
<div class="bubble" style="left:18%"></div><div class="bubble b2"></div><div class="bubble b3"></div>
"""


def inject_styles() -> None:
    st.markdown(THEME_CSS, unsafe_allow_html=True)
