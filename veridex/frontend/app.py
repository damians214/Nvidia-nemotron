"""Veridex Glass Box — interactive, clearly simulated product preview."""
import ast
import base64
import difflib
import html
import json
import time
import sys
from datetime import datetime
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title='Veridex · Glass Box', page_icon='🛡️', layout='wide', initial_sidebar_state='expanded')
ROOT = Path(__file__).resolve().parents[1]
# Embed the local shield asset so the sidebar and rotating cube can render it.
SHIELD_PATH = ROOT / 'assets' / 'veridex-shield.svg'
shield_uri = 'data:image/svg+xml;base64,' + base64.b64encode(SHIELD_PATH.read_bytes()).decode('ascii')
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
experience = st.sidebar.radio('Application mode', ['Live investigation', 'Design demo'], key='application_mode')
if experience == 'Live investigation':
    from frontend.live import render_live
    render_live()
    st.stop()
from agent.evidence import syntax_result, policy_check, patch_text, passport_json
ORIGINAL = (ROOT / 'tests' / 'vulnerable_sample.py').read_text(encoding='utf-8')
PATCHED = '''# Proposed SQL injection remediation — demonstration only.
import sqlite3

def get_user(conn: sqlite3.Connection, username: str):
    query = "SELECT * FROM users WHERE username = ?"
    return conn.execute(query, (username,)).fetchone()
'''
UNSAFE_PATCH = '''# Alternative demonstration candidate — still vulnerable!
import sqlite3

def get_user(conn: sqlite3.Connection, username: str):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    return conn.execute(query).fetchone()
'''
CANDIDATES = {"Parameterized query (recommended)": PATCHED, "String formatting (unsafe demo)": UNSAFE_PATCH}
REVIEW_BY_CANDIDATE = {
    "Parameterized query (recommended)": {
        "status": "NO OBVIOUS INJECTION PATTERN IN DEMO REVIEW",
        "summary": "Parameterized query separates SQL syntax from the username value.",
        "concerns": ["No live scanner run or behavioral tests have been performed.", "Database adapter compatibility must be reviewed."],
        "review_type": "SCRIPTED DEMONSTRATION — not a Nemotron response",
    },
    "String formatting (unsafe demo)": {
        "status": "REJECT — UNSAFE SQL CONSTRUCTION",
        "summary": "Formatting untrusted input into SQL text preserves the injection risk.",
        "concerns": ["User-controlled input is still interpolated into SQL.", "Passing Python syntax does not make a patch secure."],
        "review_type": "SCRIPTED DEMONSTRATION — not a Nemotron response",
    },
}
PATCH = ''.join(difflib.unified_diff(ORIGINAL.splitlines(keepends=True), PATCHED.splitlines(keepends=True), fromfile='a/tests/vulnerable_sample.py', tofile='b/tests/vulnerable_sample.py'))
try:
    ast.parse(PATCHED)
    SYNTAX_OK = True
except SyntaxError:
    SYNTAX_OK = False

FINDINGS = [
    {'id':'SEC-001','name':'SQL injection in query construction','file':'vulnerable_sample.py','line':'6','severity':'Critical','category':'Injection','status':'Scan cleared*','detail':'User-controlled input is concatenated into a SQL statement. Parameterized queries avoid mixing data with SQL syntax.'},
    {'id':'SEC-002','name':'Hardcoded application credential','file':'config.py','line':'18','severity':'High','category':'Secrets','status':'Pending','detail':'A credential is stored directly in application source. Consider environment-based secret configuration.'},
    {'id':'SEC-003','name':'Weak cryptographic hash','file':'auth.py','line':'31','severity':'Medium','category':'Cryptography','status':'Needs review','detail':'A legacy hash function is used in a security-sensitive path. A security review should select an appropriate replacement.'},
]
EVENTS = [
    ('SCAN','Sample findings loaded','3 illustrative findings shown; OpenGrep was not executed.'),
    ('PLAN','Investigation selected','Demo selects SEC-001 · SQL injection.'),
    ('TOOL','read_file(vulnerable_sample.py)','Illustrative tool invocation; no Nemotron request was made.'),
    ('PATCH','Parameterized SQL proposed','Local example patch is prepared for inspection.'),
    ('CHECK','Python AST parsed', 'Local ast.parse() passed.' if SYNTAX_OK else 'Local ast.parse() failed.'),
    ('RESULT','Demonstration complete','Scanner clearance is simulated, not independently verified.'),
]

def highlighted_code(source: str, comparison: str, side: str) -> str:
    """Safe, line-oriented highlighting based on difflib opcodes."""
    lines = source.splitlines()
    reference = comparison.splitlines()
    matcher = difflib.SequenceMatcher(a=reference if side == 'after' else lines,
                                      b=lines if side == 'after' else reference,
                                      autojunk=False)
    marked = set()
    for tag, a0, a1, b0, b1 in matcher.get_opcodes():
        if tag != 'equal':
            marked.update(range(b0, b1) if side == 'after' else range(a0, a1))
    output = []
    for i, line in enumerate(lines):
        kind = ('added' if side == 'after' else 'removed') if i in marked else ''
        symbol = '+' if kind == 'added' else ('−' if kind == 'removed' else ' ')
        output.append(f'<div class="code-line {kind}"><span class="line-number">{i+1:02d}</span><span class="line-symbol">{symbol}</span><span>{html.escape(line) or "&nbsp;"}</span></div>')
    return '<div class="code-diff">' + ''.join(output) + '</div>'


def transformation_html(before: str, after: str, active: bool = True) -> str:
    """One text-only continuous 360° transformation, no secondary vortex animations."""
    preview = html.escape('\n'.join(before.splitlines()[:7]))
    result = html.escape('\n'.join(after.splitlines()[:7]))
    klass = 'morph-running' if active else 'morph-still'
    return f"""<div class="morph-scene {klass}" role="img" aria-label="Illustrative code text moves from the original panel to the proposed patch panel while completing one smooth 360 degree rotation">
      <div class="morph-card morph-original"><span>01 · ORIGINAL</span><pre>{preview}</pre></div>
      <pre class="morph-text-flight" aria-hidden="true">{preview}</pre>
      <div class="morph-card morph-fixed"><span>02 · PROPOSED PATCH</span><pre>{result}</pre></div>
      <div class="morph-footer">ILLUSTRATIVE TRANSFORMATION · NO LIVE AI OR SCANNER CALL</div>
    </div>"""



def animation_frame(before: str, after: str) -> str:
    """Self-contained animated iframe; one code-text layer flies a smooth 360° arc."""
    preview = html.escape('\n'.join(before.splitlines()[:7]))
    result = html.escape('\n'.join(after.splitlines()[:7]))
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
    *{{box-sizing:border-box}}body{{margin:0;background:transparent;font-family:system-ui,sans-serif}}
    .stage{{height:290px;position:relative;overflow:hidden;border:1px solid #353b35;border-radius:15px;background:#111512;color:#f2f5f0;display:flex;align-items:center;justify-content:space-between;padding:22px 20px 37px;gap:14px}}
    .pane{{width:40%;height:195px;border:1px solid #3d4740;background:#1b211c;border-radius:11px;padding:12px;overflow:hidden;position:relative;z-index:1}}
    .pane.fixed{{border-color:#76b900}}
    .pane label{{font:700 10px system-ui;color:#b9d49d;letter-spacing:1px}}
    pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:10px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace;margin:10px 0 0;color:#e3e9e1}}
    .source pre{{animation:dimSource 1.15s ease both}}
    .fixed pre{{animation:revealFix 1.15s ease both}}
    .flight{{position:absolute;z-index:3;left:6%;top:50%;width:34%;height:150px;margin:0;transform-origin:center center;color:#b6f78a;text-shadow:0 0 9px #76b90099;pointer-events:none;opacity:0;animation:fly 1.15s linear forwards}}
    @keyframes fly{{0%{{left:6%;transform:translateY(-50%) rotate(0deg);opacity:0}}8%{{opacity:.83}}88%{{opacity:.83}}100%{{left:60%;transform:translateY(-50%) rotate(360deg);opacity:0}}}}
    @keyframes dimSource{{0%,15%{{opacity:1}}40%,85%{{opacity:.22}}100%{{opacity:1}}}}
    @keyframes revealFix{{0%,80%{{opacity:.05}}100%{{opacity:1}}}}
    footer{{position:absolute;bottom:12px;left:0;right:0;text-align:center;font:10px ui-monospace,monospace;color:#bdc7b9}}
    @media(prefers-reduced-motion:reduce){{.flight,.source pre,.fixed pre{{animation:none!important}}.flight{{display:none}}}}
    </style></head><body><div class="stage"><section class="pane source"><label>01 · ORIGINAL</label><pre>{preview}</pre></section><pre class="flight" aria-hidden="true">{preview}</pre><section class="pane fixed"><label>02 · PROPOSED PATCH</label><pre>{result}</pre></section><footer>VISUAL DEMO · NOT A LIVE SECURITY SCAN</footer></div></body></html>"""


def status_card(message: str, kind: str = 'neutral') -> None:
    """Accessible, theme-neutral status panel; no Streamlit notification backgrounds."""
    symbol = {'pass':'✓','warning':'!','info':'i'}.get(kind,'•')
    st.markdown(f'<div class="sentinel-status sentinel-{kind}"><span class="sentinel-symbol">{symbol}</span><span>{html.escape(message)}</span></div>',unsafe_allow_html=True)

# Explicit display mode controls both page and widget surfaces (not just text).
if 'display_mode' not in st.session_state:
    st.session_state.display_mode = 'System'
with st.sidebar:
    st.markdown('### ◐ Appearance')
    st.radio('Theme', ['System', 'Light', 'Dark'], key='display_mode', horizontal=True,
             help='System follows your browser/operating-system color preference.')

st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
html,body,[class*="css"],[data-testid="stAppViewContainer"]{font-family:'DM Sans',sans-serif!important}
[data-testid="stAppViewContainer"]{background:#f5f7f4;color:#1b241c}
[data-testid="stSidebar"]{background:#fff;border-right:1px solid #e2e8df}
[data-testid="stHeader"]{background:rgba(245,247,244,.93)}
.block-container{padding-top:1.8rem;max-width:1480px}
h1,h2,h3{letter-spacing:-.045em!important;color:#192319!important}
[data-testid="stMetric"]{background:white;padding:18px 19px;border:1px solid #e2e9e0;border-radius:15px;box-shadow:0 3px 14px rgba(28,53,29,.025)}
[data-testid="stMetricLabel"]{color:#667367}[data-testid="stMetricValue"]{color:#172218;font-weight:800}
.stButton>button{border-radius:10px;font-weight:700;border-color:#dbe4d7;transition:all .16s ease}
.stButton>button:hover{border-color:#76b900;color:#4f8100}
.stButton>button[kind="primary"]{background:#76b900!important;color:#fff!important;border:1px solid #76b900!important}
.stButton>button[kind="primary"]:hover{background:#639e00!important}
[data-baseweb="tab-list"]{gap:20px;border-bottom:1px solid #dce5d9}
button[data-baseweb="tab"]{font-weight:700}
[data-testid="stDownloadButton"] button{background:#172219;color:#fff;border-color:#172219}
[data-testid="stDownloadButton"] button:hover{background:#293e2a;color:#fff}
.hero{background:linear-gradient(115deg,#101b12 0%,#15271a 60%,#203a20 100%);border-radius:19px;padding:31px 34px;color:#fff;position:relative;overflow:hidden;margin:8px 0 22px;border:1px solid #2c452e}
.hero:after{content:'';position:absolute;right:-110px;top:-155px;width:450px;height:450px;border:1px solid rgba(130,216,40,.24);border-radius:50%;box-shadow:0 0 0 55px rgba(118,185,0,.045),0 0 0 120px rgba(118,185,0,.025);pointer-events:none}
.hero .eyebrow{font:600 11px 'IBM Plex Mono',monospace;color:#a5e75a;letter-spacing:2px}
.hero h1{color:#fff!important;font-size:37px;line-height:1.13;margin:13px 0 9px;letter-spacing:-1.6px}
.hero p{color:#b5c6b5;font-size:14px;max-width:620px;margin:0;line-height:1.7}
.mini{font:600 11px 'IBM Plex Mono',monospace;color:#7a887a;letter-spacing:1.2px;text-transform:uppercase}
.panel{background:#fff;border:1px solid #e2e9df;border-radius:15px;padding:19px 21px;margin:6px 0 12px}
.panel h4{margin:0 0 6px;color:#1a281a;font-size:15px}
.panel p{margin:0;color:#758174;font-size:12px;line-height:1.6}
.darkpanel{background:linear-gradient(140deg,#0c160e,#152519);color:#e6f3e2;border:1px solid #2b462d;border-radius:15px;padding:19px 21px;margin:7px 0 14px}
.darkpanel .heading{font-weight:700;font-size:15px;color:#f0fff0}
.event{padding:10px 0;border-bottom:1px solid #26382a;font:12px/1.55 'IBM Plex Mono',monospace;color:#c2d5c1}
.event:last-child{border-bottom:none}.event b{color:#9fdf58}.event small{display:block;color:#8ca48d;margin-top:3px;font-size:11px}
.codepanel{background:#111a14;border:1px solid #2b3b2d;border-radius:13px;padding:17px;color:#d6ebd4;white-space:pre-wrap;overflow:auto;font:12px/1.75 'IBM Plex Mono',monospace;min-height:230px}
.tag{display:inline-block;border-radius:30px;padding:4px 10px;font-size:11px;font-weight:700;border:1px solid #d9e7d2;background:#f3f9ef;color:#558a00}
.tag-muted{color:#6c776c;background:#f2f4f2;border-color:#e1e5e0}
.brand{font-size:22px;font-weight:800;letter-spacing:-1.1px;color:#18241a}.brand span{color:#76b900}
.smallcopy{color:#738073;font-size:12px;line-height:1.65}
hr{border-color:#e4eae1}

/* restrained 3D core + motion */
.core-shell{position:relative;min-height:210px;border-radius:18px;background:radial-gradient(ellipse at 32% 50%,#1f4222 0%,#111f14 55%,#0b160d 100%);border:1px solid #345237;display:flex;align-items:center;gap:32px;padding:25px 36px;overflow:hidden;margin:8px 0 16px;color:#fff}
.core-shell:before{content:"";position:absolute;width:360px;height:360px;border:1px solid rgba(118,185,0,.13);border-radius:50%;left:-90px;top:-76px;box-shadow:0 0 0 44px rgba(118,185,0,.035),0 0 0 90px rgba(118,185,0,.025)}
.core-stage{width:160px;height:150px;flex-shrink:0;perspective:650px;display:flex;align-items:center;justify-content:center;position:relative}
.core-stage:after{content:"";position:absolute;bottom:10px;width:112px;height:22px;border-radius:50%;background:rgba(118,185,0,.25);filter:blur(17px)}
.core-3d{position:relative;width:78px;height:78px;transform-style:preserve-3d;transform:rotateX(-22deg) rotateY(30deg);animation:coreturn 14s linear infinite}
.core-face{position:absolute;inset:0;background:linear-gradient(145deg,#1b381e,#0d1c11);border:2px solid #8ad325;box-shadow:inset 0 0 22px rgba(118,185,0,.24),0 0 14px rgba(118,185,0,.18);display:flex;align-items:center;justify-content:center;color:#76b900!important;-webkit-text-fill-color:#76b900!important;text-shadow:0 0 14px rgba(118,185,0,.5);font:900 79px/1 Arial,sans-serif;letter-spacing:0;box-sizing:border-box;text-align:center;padding:0;transform-origin:center center}
.core-face::before{content:'◈';display:block;position:absolute;left:50%;top:50%;transform:translate(-50%,-52%);line-height:1;font-family:Arial,sans-serif;font-size:79px;font-weight:700;color:#76b900;-webkit-text-fill-color:#76b900;text-shadow:0 0 12px rgba(118,185,0,.42)}
.core-face.front{transform:translateZ(39px)}.core-face.back{transform:rotateY(180deg) translateZ(39px)}.core-face.right{transform:rotateY(90deg) translateZ(39px)}.core-face.left{transform:rotateY(-90deg) translateZ(39px)}.core-face.top{transform:rotateX(90deg) translateZ(39px)}.core-face.bottom{transform:rotateX(-90deg) translateZ(39px)}
.core-shell.active .core-face{border-color:#a4f44d;box-shadow:inset 0 0 22px rgba(118,185,0,.3),0 0 24px rgba(118,185,0,.35)}
.core-shell.complete .core-3d{animation-duration:24s}
.core-copy{z-index:1}.core-eyebrow{color:#a4df57;font:600 11px 'IBM Plex Mono',monospace;letter-spacing:1.6px}.core-title{font-size:26px;font-weight:800;letter-spacing:-.8px;margin:8px 0;color:#fff}.core-description{color:#b2c7b3;font-size:13px;line-height:1.6;max-width:470px}
.workflow{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 18px}.workflow-step{border:1px solid #dce6d8;background:#fff;border-radius:999px;padding:7px 12px;font-size:12px;font-weight:700;color:#7d8a7b}.workflow-step.done{background:#ecf7e6;color:#4f8500;border-color:#c7e5b6}.workflow-step.current{color:#345f00;border-color:#76b900;box-shadow:0 0 0 3px rgba(118,185,0,.09);animation:softpulse 2.6s ease-in-out infinite}
.event{animation:eventin .32s ease-out both}
@keyframes coreturn{0%{transform:rotateX(-22deg) rotateY(0deg)}100%{transform:rotateX(-22deg) rotateY(360deg)}}
@keyframes softpulse{50%{box-shadow:0 0 0 6px rgba(118,185,0,.04)}}
@keyframes eventin{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
@media(max-width:700px){.core-shell{padding:20px;gap:8px}.core-stage{width:105px}.core-title{font-size:20px}.core-3d{width:58px;height:58px}.core-face.front{transform:translateZ(29px)}.core-face.back{transform:rotateY(180deg) translateZ(29px)}.core-face.right{transform:rotateY(90deg) translateZ(29px)}.core-face.left{transform:rotateY(-90deg) translateZ(29px)}.core-face.top{transform:rotateX(90deg) translateZ(29px)}.core-face.bottom{transform:rotateX(-90deg) translateZ(29px)}}
@media(prefers-reduced-motion:reduce){.core-3d,.workflow-step.current,.event{animation:none!important;transition:none!important}}

/* Single app-controlled appearance setting; hide Streamlit's duplicate Settings/theme menu. */
#MainMenu, [data-testid="stMainMenu"]{visibility:hidden!important}
/* v5: code transformation, line highlights, and accessible progress states */
.code-diff{background:#111a14;border:1px solid #2b3b2d;border-radius:13px;padding:12px 0;color:#d6ebd4;overflow-x:auto;font:12px/1.75 'IBM Plex Mono',monospace;min-height:210px}
.code-line{display:flex;gap:9px;padding:0 12px;white-space:pre;min-width:max-content}
.code-line.added{background:rgba(118,185,0,.2);border-left:3px solid #9ce647;padding-left:9px;color:#e3ffd0}
.code-line.removed{background:rgba(255,111,103,.14);border-left:3px solid #ff8a80;padding-left:9px;color:#ffd8d5}
.line-number{color:#708571;user-select:none;min-width:25px}.line-symbol{font-weight:800;min-width:10px}
/* One animated element only: source text travels across the gap and completes exactly one smooth 360° turn at arrival. */
.morph-scene{position:relative;display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:270px;background:#0c120e;border:1px solid #344138;border-radius:18px;padding:26px 18px 34px;overflow:hidden;color:#f0f4ef;isolation:isolate}
.morph-card{position:relative;z-index:2;width:38%;min-width:0;border:1px solid #344138;background:#151d17;border-radius:12px;padding:12px}
.morph-card span{font:700 10px 'IBM Plex Mono',monospace;letter-spacing:1px;color:#a9e774}
.morph-card pre{font:10px/1.6 'IBM Plex Mono',monospace;white-space:pre-wrap;overflow-wrap:anywhere;max-height:145px;overflow:hidden;color:#e1e9de}
.morph-fixed{border-color:#76b900}
.morph-text-flight{position:absolute;left:7%;top:50%;width:33%;max-height:150px;margin:0;z-index:4;pointer-events:none;overflow:hidden;white-space:pre-wrap;overflow-wrap:anywhere;font:10px/1.6 'IBM Plex Mono',monospace;color:#a8ee77;text-shadow:0 0 9px rgba(118,185,0,.45);opacity:0;transform-origin:50% 50%}
.morph-running .morph-text-flight{animation:singleCodeFlight 1.15s cubic-bezier(.45,0,.55,1) both}
/* Linear angle progression: no intermediate jumps, no additional rotating rings or overlays. */
@keyframes singleCodeFlight{
  0%{left:7%;opacity:0;transform:translateY(-50%) rotate(0deg)}
  8%{opacity:.8}
  92%{opacity:.8}
  100%{left:60%;opacity:0;transform:translateY(-50%) rotate(360deg)}
}
.morph-footer{position:absolute;bottom:10px;left:0;right:0;text-align:center;color:#bdc8b9;font:10px 'IBM Plex Mono',monospace}
@media(max-width:760px){.morph-scene{padding:16px 8px 32px;min-height:235px}.morph-card{width:40%;padding:8px}.morph-card pre,.morph-text-flight{font-size:8px}.morph-footer{font-size:8px}}
@media(prefers-reduced-motion:reduce){.morph-running .morph-text-flight{animation:none!important}}
</style>''', unsafe_allow_html=True)

# Override Streamlit's theme-dependent widget defaults and the custom light cards.
# System mode uses the browser's prefers-color-scheme media query.
LIGHT_CSS = r"""
:root {color-scheme:light}
[data-testid="stAppViewContainer"] button:not([kind="primary"]),[data-testid="stSidebar"] button:not([kind="primary"]){background:#f4f8f1!important;color:#254224!important;border:1px solid #cbdcc5!important;box-shadow:none!important}
[data-testid="stAppViewContainer"] button:not([kind="primary"]):hover,[data-testid="stSidebar"] button:not([kind="primary"]):hover{background:#e8f4e0!important;color:#2e6200!important;border-color:#76b900!important}
[data-testid="stAppViewContainer"] button[kind="primary"],[data-testid="stSidebar"] button[kind="primary"]{background:#76b900!important;color:#101d0a!important;border-color:#76b900!important}
[data-testid="stAppViewContainer"] button[kind="primary"]:hover{background:#8ed51b!important}
[data-testid="stAppViewContainer"], [data-testid="stMain"], .stApp {background:#ffffff!important;color:#172319!important}
[data-testid="stSidebar"], [data-testid="stSidebarContent"]{background:#f7faf6!important;color:#172319!important}
[data-testid="stHeader"], [data-testid="stToolbar"]{background:#ffffff!important}
[data-testid="stAppViewContainer"] p,[data-testid="stAppViewContainer"] label,[data-testid="stAppViewContainer"] h1,[data-testid="stAppViewContainer"] h2,[data-testid="stAppViewContainer"] h3,[data-testid="stAppViewContainer"] h4,[data-testid="stAppViewContainer"] li,[data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"]{color:#172319}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] label,[data-testid="stSidebar"] h3{color:#172319!important}
[data-testid="stMetric"],.panel{background:#fff!important;border-color:#dae6d8!important}
.panel h4{color:#172319!important}.panel p{color:#586959!important}
[data-testid="stMetricValue"]{color:#172319!important}
[data-testid="stMetricLabel"]{color:#526353!important}
[data-testid="stTabs"] button{color:#253b27!important}
[data-testid="stTabs"] button[aria-selected="true"]{color:#4e8500!important}
[data-testid="stDataFrame"], [data-testid="stVegaLiteChart"]{color:#172319}
[data-testid="stSidebar"] .brand{color:#172319!important}
[data-testid="stAppViewContainer"] .hero h1,[data-testid="stAppViewContainer"] .hero p,[data-testid="stAppViewContainer"] .hero .eyebrow,[data-testid="stAppViewContainer"] .core-shell *,[data-testid="stAppViewContainer"] .darkpanel *,[data-testid="stAppViewContainer"] .codepanel *,[data-testid="stAppViewContainer"] .code-diff *,[data-testid="stAppViewContainer"] .morph-scene *{color:inherit}
[data-testid="stAppViewContainer"] .hero h1{color:#fff!important}
"""
DARK_CSS = r"""
:root {color-scheme:dark}
[data-testid="stSidebar"] button:not([kind="primary"]){background:#172019!important;color:#f2f7ef!important;border-color:#364739!important}
[data-testid="stSidebar"] button[kind="primary"]{background:#76b900!important;color:#081106!important}
[data-testid="stAppViewContainer"], [data-testid="stMain"], .stApp{background:#050705!important;color:#f2f7ef!important}
[data-testid="stSidebar"], [data-testid="stSidebarContent"]{background:#0b100c!important;border-color:#273428!important;color:#f2f7ef!important}
[data-testid="stHeader"], [data-testid="stToolbar"]{background:#050705!important}
[data-testid="stAppViewContainer"] p,[data-testid="stAppViewContainer"] label,[data-testid="stAppViewContainer"] h1,[data-testid="stAppViewContainer"] h2,[data-testid="stAppViewContainer"] h3,[data-testid="stAppViewContainer"] h4,[data-testid="stAppViewContainer"] li,[data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"]{color:#f2f7ef!important}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] label,[data-testid="stSidebar"] h3,[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]{color:#f2f7ef!important}
[data-testid="stMetric"],.panel{background:#101712!important;border:1px solid #2c3c2e!important;box-shadow:none!important}
.panel h4{color:#f2f7ef!important}.panel p{color:#bdcdbb!important}
[data-testid="stMetricValue"]{color:#f2f7ef!important}
[data-testid="stMetricLabel"]{color:#bed1ba!important}
[data-testid="stTabs"] button{color:#dce8d9!important}
[data-testid="stTabs"] button[aria-selected="true"]{color:#a4e65d!important}
[data-baseweb="tab-list"]{border-color:#344634!important}
[data-testid="stSidebar"] .brand{color:#f2f7ef!important}
[data-testid="stSidebar"] .mini,[data-testid="stSidebar"] .smallcopy{color:#c3d4bf!important}
[data-testid="stAppViewContainer"] .tag{background:#1d3018!important;border-color:#46643b!important;color:#c9ff9c!important}
[data-testid="stAppViewContainer"] .tag-muted{background:#1a221a!important;color:#c8d4c4!important}
[data-testid="stAppViewContainer"] .workflow-step{background:#111b12!important;color:#d4e1cf!important;border-color:#405240!important}
[data-testid="stAppViewContainer"] .workflow-step.done{background:#20351c!important;color:#c7f9a0!important}
[data-testid="stAppViewContainer"] .workflow-step.current{background:#1a2d15!important;color:#c7ff9a!important}
[data-testid="stAppViewContainer"] .hero h1{color:#fff!important}
[data-testid="stAppViewContainer"] .hero p{color:#c6d7c5!important}
[data-testid="stAppViewContainer"] .core-shell *,[data-testid="stAppViewContainer"] .darkpanel *,[data-testid="stAppViewContainer"] .codepanel *,[data-testid="stAppViewContainer"] .code-diff *,[data-testid="stAppViewContainer"] .morph-scene *{color:inherit}
[data-testid="stAppViewContainer"] .core-title,[data-testid="stAppViewContainer"] .darkpanel .heading{color:#f5fff2!important}
[data-testid="stAppViewContainer"] .core-eyebrow,[data-testid="stAppViewContainer"] .event b{color:#b4ef69!important}
[data-testid="stAppViewContainer"] .code-line.added{color:#e3ffd0!important}
[data-testid="stAppViewContainer"] .code-line.removed{color:#ffd8d5!important}
[data-testid="stAppViewContainer"] [data-testid="stAlert"]{background:#162417!important;color:#e9f7e5!important}
[data-testid="stAppViewContainer"] [data-testid="stAlert"] p{color:#e9f7e5!important}
[data-testid="stAppViewContainer"] [data-testid="stDataFrame"], [data-testid="stAppViewContainer"] [data-testid="stVegaLiteChart"]{background:#101712!important}
[data-testid="stAppViewContainer"] input,[data-testid="stAppViewContainer"] textarea,[data-testid="stAppViewContainer"] [role="combobox"]{background:#151f17!important;color:#f2f7ef!important;border-color:#344836!important}
[data-testid="stAppViewContainer"] button:not([kind="primary"]){background:#172019;color:#f2f7ef;border-color:#364739}
[data-testid="stAppViewContainer"] button:not([kind="primary"]):hover{border-color:#76b900;color:#cfff9a}
[data-testid="stAppViewContainer"] [data-testid="stDownloadButton"] button{background:#243b20!important;color:#eaffdf!important}
/* Prevent white markdown/section surfaces in dark mode, including sidebar workspace and panel headings. */
[data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stAppViewContainer"] [data-testid="stVerticalBlock"],
[data-testid="stSidebar"] [data-testid="stVerticalBlock"],
[data-testid="stAppViewContainer"] [data-testid="stElementContainer"],
[data-testid="stSidebar"] [data-testid="stElementContainer"]{background-color:transparent!important}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] b,
[data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] strong{color:#f2f7ef!important}
[data-testid="stSidebar"] [data-baseweb="select"]>div,
[data-testid="stSidebar"] [data-baseweb="input"]>div,
[data-testid="stSidebar"] [data-baseweb="radio"]{background:#152019!important;color:#f2f7ef!important;border-color:#3d533d!important}
[data-testid="stSidebar"] [data-baseweb="select"] span,
[data-testid="stSidebar"] [data-baseweb="select"] input,
[data-testid="stSidebar"] [data-baseweb="radio"] label{color:#f2f7ef!important}
[data-testid="stAppViewContainer"] [data-testid="stExpander"],
[data-testid="stAppViewContainer"] [data-testid="stExpander"] details,
[data-testid="stAppViewContainer"] [data-testid="stStatusWidget"]{background:#111a13!important;color:#f2f7ef!important;border-color:#334733!important}
[data-testid="stAppViewContainer"] .panel,
[data-testid="stAppViewContainer"] .context-tile{background:#121d13!important;color:#f2f7ef!important}

"""
# Unified neutral surfaces for both themes. Green is an accent, not a card fill.
LIGHT_REFINEMENT = r"""
[data-testid="stSidebar"] [data-baseweb="radio"], [data-testid="stSidebar"] [data-baseweb="select"]>div,
[data-testid="stSidebar"] [data-baseweb="input"]>div {background:#ffffff!important;color:#172319!important;border-color:#dce6dc!important}
[data-testid="stSidebar"] [data-baseweb="radio"] label,[data-testid="stSidebar"] [data-baseweb="radio"] span,
[data-testid="stSidebar"] [data-baseweb="select"] span{color:#253429!important}
[data-testid="stAppViewContainer"] .context-tile{background:#ffffff!important;color:#172319!important;border:1px solid #dce6dc!important}
[data-testid="stAppViewContainer"] .context-tile *,[data-testid="stAppViewContainer"] .panel *{color:#263a2a!important}
[data-testid="stAppViewContainer"] .workflow-step{background:#ffffff!important;color:#3f5042!important;border-color:#dce6dc!important}
[data-testid="stAppViewContainer"] .workflow-step.done{background:#f0f6ed!important;color:#3b681a!important}
[data-testid="stAppViewContainer"] .workflow-step.current{background:#f4f8f1!important;color:#315e0b!important;border-color:#76b900!important}
[data-testid="stAppViewContainer"] .tag{background:#f1f6ed!important;color:#426b22!important;border-color:#d7e6d0!important}
[data-testid="stAppViewContainer"] .tag-muted{background:#f5f7f5!important;color:#536354!important}
[data-testid="stSidebar"] [data-baseweb="radio"] [aria-checked="true"]{background:#edf5e9!important;color:#294a1b!important}
"""
DARK_REFINEMENT = r"""
[data-testid="stSidebar"] [data-baseweb="radio"], [data-testid="stSidebar"] [data-baseweb="select"]>div,
[data-testid="stSidebar"] [data-baseweb="input"]>div{background:#141a15!important;color:#edf3eb!important;border-color:#303d32!important}
[data-testid="stSidebar"] [data-baseweb="radio"] label,[data-testid="stSidebar"] [data-baseweb="radio"] span,
[data-testid="stSidebar"] [data-baseweb="select"] span{color:#edf3eb!important}
[data-testid="stSidebar"] [data-baseweb="radio"] [aria-checked="true"]{background:#222d22!important;color:#f2f7ef!important}
[data-testid="stAppViewContainer"] .context-tile,[data-testid="stAppViewContainer"] .panel{background:#111713!important;color:#f2f7ef!important;border:1px solid #303d32!important}
[data-testid="stAppViewContainer"] .context-tile *,[data-testid="stAppViewContainer"] .panel *{color:#e6efe3!important}
[data-testid="stAppViewContainer"] .workflow-step{background:#141a15!important;color:#d5e0d2!important;border-color:#344236!important}
[data-testid="stAppViewContainer"] .workflow-step.done{background:#1b261b!important;color:#d4eac8!important}
[data-testid="stAppViewContainer"] .workflow-step.current{background:#202b20!important;color:#e3f5d9!important;border-color:#76b900!important}
[data-testid="stAppViewContainer"] .tag{background:#1d281c!important;color:#d5edc7!important;border-color:#3b5035!important}
[data-testid="stAppViewContainer"] .tag-muted{background:#1a211b!important;color:#d0d9cd!important}
"""
if st.session_state.display_mode == 'Dark':
    mode_css = DARK_CSS + DARK_REFINEMENT
elif st.session_state.display_mode == 'Light':
    mode_css = LIGHT_CSS + LIGHT_REFINEMENT
else:
    mode_css = LIGHT_CSS + LIGHT_REFINEMENT + '@media (prefers-color-scheme: dark) {' + DARK_CSS + DARK_REFINEMENT + '}'
st.markdown('<style>' + mode_css + '</style>', unsafe_allow_html=True)
st.markdown("""<style>
.block-container{max-width:1660px!important;padding-left:2rem!important;padding-right:2rem!important}
.hero{margin-bottom:12px!important}
.hero-brand{position:absolute;right:25px;top:19px;color:#d4ffb0;font:700 11px 'IBM Plex Mono',monospace;letter-spacing:.7px;background:#243e24;border:1px solid #4b7741;padding:8px 11px;border-radius:8px}
.hero-brand span{color:#b8cbb1;font-weight:400}
.powered-chip{border:1px solid #57843b;background:#182919;color:#dfffc6;border-radius:10px;padding:12px 13px;margin:12px 0 16px;font-size:12px;line-height:1.4}
.powered-chip strong{color:#a5e65b}.powered-chip small{display:block;color:#bed4b8;font-size:10px;margin-top:4px}
.context-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:12px 0 18px}
.context-tile{border:1px solid #d5e4d1;background:#edf5e9;border-radius:12px;padding:13px 16px;display:flex;flex-direction:column;gap:4px;min-height:92px}
.context-tile b{color:#5b8c26;font:700 10px 'IBM Plex Mono',monospace;letter-spacing:.7px}
.context-tile strong{color:#20351c;font-size:15px}.context-tile span{color:#526850;font-size:11px}
@media(max-width:1000px){.context-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.hero-brand{position:relative;display:inline-block;right:auto;top:auto;margin-bottom:12px}}
@media(max-width:580px){.context-grid{grid-template-columns:1fr}.block-container{padding-left:1rem!important;padding-right:1rem!important}}
</style>""",unsafe_allow_html=True)
if st.session_state.display_mode == 'Dark':
    st.markdown('<style>.context-tile{background:#121d13;border-color:#344b31}.context-tile strong{color:#f0ffe8}.context-tile span{color:#c3d7bd}.context-tile b{color:#b0e778}</style>',unsafe_allow_html=True)
elif st.session_state.display_mode == 'System':
    st.markdown('<style>@media(prefers-color-scheme:dark){.context-tile{background:#121d13;border-color:#344b31}.context-tile strong{color:#f0ffe8}.context-tile span{color:#c3d7bd}.context-tile b{color:#b0e778}}</style>',unsafe_allow_html=True)



# Consistent neutral UI surfaces; NVIDIA green is reserved for accents, not alert fills.
NEUTRAL_LIGHT = r"""
[data-testid="stAppViewContainer"] [data-testid="stAlert"],
[data-testid="stAppViewContainer"] [data-testid="stNotification"],
[data-testid="stAppViewContainer"] [data-testid="stExpander"] details,
[data-testid="stAppViewContainer"] [data-testid="stStatusWidget"]{background:#f7f8f7!important;color:#172319!important;border:1px solid #dce3dc!important;border-radius:10px!important}
[data-testid="stAppViewContainer"] [data-testid="stAlert"] p,
[data-testid="stAppViewContainer"] [data-testid="stAlert"] span,
[data-testid="stAppViewContainer"] [data-testid="stAlert"] div{color:#172319!important}
[data-testid="stAppViewContainer"] [data-testid="stAlert"] svg{color:#578a00!important;fill:none!important}
[data-testid="stSidebar"] [data-baseweb="radio"] [aria-checked="true"]{background:#f0f2f0!important;color:#172319!important}
[data-testid="stAppViewContainer"] .workflow-step.done,[data-testid="stAppViewContainer"] .workflow-step.current{background:#f2f4f2!important;color:#243b24!important}
[data-testid="stAppViewContainer"] .tag{background:#f2f4f2!important;color:#294529!important}
"""
NEUTRAL_DARK = r"""
[data-testid="stAppViewContainer"] [data-testid="stAlert"],
[data-testid="stAppViewContainer"] [data-testid="stNotification"],
[data-testid="stAppViewContainer"] [data-testid="stExpander"] details,
[data-testid="stAppViewContainer"] [data-testid="stStatusWidget"]{background:#161a17!important;color:#f1f4f0!important;border:1px solid #333b34!important;border-radius:10px!important}
[data-testid="stAppViewContainer"] [data-testid="stAlert"] p,
[data-testid="stAppViewContainer"] [data-testid="stAlert"] span,
[data-testid="stAppViewContainer"] [data-testid="stAlert"] div{color:#f1f4f0!important}
[data-testid="stAppViewContainer"] [data-testid="stAlert"] svg{color:#9bd64a!important;fill:none!important}
[data-testid="stSidebar"] [data-baseweb="radio"] [aria-checked="true"]{background:#232923!important;color:#f1f4f0!important}
[data-testid="stAppViewContainer"] .workflow-step.done,[data-testid="stAppViewContainer"] .workflow-step.current{background:#202621!important;color:#f1f4f0!important}
[data-testid="stAppViewContainer"] .tag{background:#202621!important;color:#f1f4f0!important}
"""
if st.session_state.display_mode == 'Dark':
    st.markdown('<style>'+NEUTRAL_DARK+'</style>',unsafe_allow_html=True)
elif st.session_state.display_mode == 'Light':
    st.markdown('<style>'+NEUTRAL_LIGHT+'</style>',unsafe_allow_html=True)
else:
    st.markdown('<style>'+NEUTRAL_LIGHT+'@media(prefers-color-scheme:dark){'+NEUTRAL_DARK+'}</style>',unsafe_allow_html=True)


st.markdown('<style>'+'\n/* v11 unified neutral palette: all alert and policy cards share the same surfaces. */\n.sentinel-status{display:flex;align-items:center;gap:12px;background:#f5f6f5!important;color:#1b241d!important;border:1px solid #d9ded9!important;border-left:3px solid #76b900!important;border-radius:11px;padding:16px 18px;margin:9px 0 13px;line-height:1.5;font-size:14px;font-weight:600}\n.sentinel-status span{color:inherit!important}.sentinel-status .sentinel-symbol{display:inline-flex;align-items:center;justify-content:center;flex:0 0 22px;height:22px;color:#427300!important;font-weight:800}\n.sentinel-warning{border-left-color:#c28a2d!important}.sentinel-warning .sentinel-symbol{color:#9d6b14!important}\n[data-testid="stAppViewContainer"] [data-testid="stDownloadButton"] button{background:#f1f3f1!important;color:#172319!important;border:1px solid #d6dfd6!important}\n[data-testid="stAppViewContainer"] [data-testid="stDownloadButton"] button:hover{background:#e8eee8!important;color:#172319!important;border-color:#76b900!important}\n'+'</style>',unsafe_allow_html=True)
if st.session_state.display_mode == 'Dark':
    st.markdown('<style>'+'\n.sentinel-status{background:#171b18!important;color:#f1f4f1!important;border-color:#363d37!important;border-left-color:#76b900!important}\n.sentinel-status .sentinel-symbol{color:#a6e461!important}\n.sentinel-warning{border-left-color:#d4a453!important}.sentinel-warning .sentinel-symbol{color:#e4bd75!important}\n[data-testid="stAppViewContainer"] [data-testid="stDownloadButton"] button{background:#232a24!important;color:#f1f4f1!important;border:1px solid #424c43!important}\n[data-testid="stAppViewContainer"] [data-testid="stDownloadButton"] button:hover{background:#2d362e!important;color:#ffffff!important;border-color:#76b900!important}\n'+'</style>',unsafe_allow_html=True)
elif st.session_state.display_mode == 'System':
    st.markdown('<style>@media(prefers-color-scheme:dark){'+'\n.sentinel-status{background:#171b18!important;color:#f1f4f1!important;border-color:#363d37!important;border-left-color:#76b900!important}\n.sentinel-status .sentinel-symbol{color:#a6e461!important}\n.sentinel-warning{border-left-color:#d4a453!important}.sentinel-warning .sentinel-symbol{color:#e4bd75!important}\n[data-testid="stAppViewContainer"] [data-testid="stDownloadButton"] button{background:#232a24!important;color:#f1f4f1!important;border:1px solid #424c43!important}\n[data-testid="stAppViewContainer"] [data-testid="stDownloadButton"] button:hover{background:#2d362e!important;color:#ffffff!important;border-color:#76b900!important}\n'+'}</style>',unsafe_allow_html=True)

st.markdown("""<style>
.veridex-brand-icon{height:29px;width:27px;vertical-align:middle;margin-right:8px;object-fit:contain}
.core-face::before{content:none!important;display:none!important}
.core-face .veridex-shield-face{display:block;position:absolute;left:50%;top:50%;width:70px;height:70px;transform:translate(-50%,-50%);object-fit:contain;filter:drop-shadow(0 0 7px rgba(118,185,0,.4))}
@media(max-width:700px){.core-face .veridex-shield-face{width:52px;height:52px}}
[data-testid="stVegaLiteChart"], [data-testid="stVegaLiteChart"] > div{background:transparent!important}
</style>""",unsafe_allow_html=True)

DEFAULT={'run_step':0,'selected_id':'SEC-001','view':'Developer','steering':[],'patch_scope':2,'filter_severity':'All','filter_status':'All','activity_only':False,'candidate':'Parameterized query (recommended)','policy_minimal':True,'policy_no_imports':True,'show_highlights':True,'show_morph':True,'demo_animation':False,'show_only_changes':False}
for key,val in DEFAULT.items():
    if key not in st.session_state: st.session_state[key]=val

with st.sidebar:
    st.markdown('<div class="brand"><img src="'+shield_uri+'" alt="" class="veridex-brand-icon"> VERIDEX</div>',unsafe_allow_html=True)
    st.markdown('<div class="mini">GLASS BOX / DESIGN PREVIEW</div>',unsafe_allow_html=True)
    st.markdown('<div class="powered-chip">◈ Designed for <strong>NVIDIA Nemotron</strong><small>Integration planned · independent student project</small></div>',unsafe_allow_html=True)
    st.write('')
    status_card('Interactive demo — no live Nemotron or OpenGrep calls.', 'info')
    st.markdown('**Workspace**')
    st.selectbox('Sample repository',['Python security demo'],label_visibility='collapsed')
    st.markdown('**Experience**')
    st.toggle('Show patch highlights',key='show_highlights')
    st.toggle('Show transformation visual',key='show_morph')
    st.toggle('Animate demo run (~1 second)',key='demo_animation',help='Optional visualization of a scripted demo. No real processing is occurring.')
    st.markdown('**Patch preference**')
    st.session_state.patch_scope=st.slider('Remediation scope',1,5,st.session_state.patch_scope,help='Visual preference only in this demo; does not change the proposed patch.')
    st.caption('Minimal fix  ·  Broader refactor')
    st.divider()
    st.markdown('**Integrations**')
    st.markdown('<div class="smallcopy">● Nemotron — <b>not connected</b><br>● OpenGrep — <b>not connected</b><br>● Python AST — <b>local check available</b></div>',unsafe_allow_html=True)
    st.divider()
    if st.button('↺ Reset demo',use_container_width=True):
        st.session_state.run_step=0
        st.session_state.steering=[]
        st.rerun()
    st.caption('HackUTD 2026 · NVIDIA Nemotron challenge concept. Independent student project.')

st.markdown('''<div class="hero"><div class="hero-brand">DESIGNED FOR NVIDIA NEMOTRON <span>· INTEGRATION PLANNED</span></div><div class="eyebrow">SECURITY INTELLIGENCE / NEMOTRON CHALLENGE CONCEPT</div><h1>Don't just fix it.<br><span style="color:#a4df57">Verify it.</span></h1><p>From security findings to reviewable fixes. Explore the autonomous workflow through a transparent, interactive product demonstration.</p></div>''',unsafe_allow_html=True)

st.markdown("""<div class="context-grid">
<div class="context-tile"><b>01 / DETECT</b><strong>OpenGrep</strong><span>Scanner integration planned</span></div>
<div class="context-tile"><b>02 / INVESTIGATE</b><strong>NVIDIA Nemotron</strong><span>Agent reasoning integration planned</span></div>
<div class="context-tile"><b>03 / VERIFY</b><strong>Local AST</strong><span>Syntax validation available</span></div>
<div class="context-tile"><b>04 / REVIEW</b><strong>Evidence Passport</strong><span>Exportable demonstration report</span></div>
</div>""",unsafe_allow_html=True)

tab_dev,tab_exec,tab_about=st.tabs(['◈  Developer workspace','▦  Executive overview','◎  Product & architecture'])

with tab_dev:
    a,b,c,d=st.columns(4)
    a.metric('Findings','03',help='Illustrative sample findings')
    b.metric('Critical','01')
    c.metric('Scan cleared*','01' if st.session_state.run_step==len(EVENTS) else '00')
    d.metric('Agent steps',f'{st.session_state.run_step:02d} / {len(EVENTS):02d}')
    st.write('')
    left,right=st.columns([1.3,1],gap='large')
    with left:
        state = 'idle' if st.session_state.run_step == 0 else ('complete' if st.session_state.run_step == len(EVENTS) else 'active')
        state_label = {'idle':'Ready to investigate','active':'Investigation in progress','complete':'Demo investigation complete'}[state]
        state_detail = {'idle':'Run the demo to explore the workflow.','active':'The current stage follows the scripted demonstration.','complete':'Review the example patch and verification limitations below.'}[state]
        core_faces = ''.join(f'<div class="core-face {face}" aria-hidden="true"><img class="veridex-shield-face" src="'+shield_uri+'" alt=""></div>' for face in ('front','back','right','left','top','bottom'))
        st.markdown(f'<div class="core-shell {state}"><div class="core-stage"><div class="core-3d">{core_faces}</div></div><div class="core-copy"><div class="core-eyebrow">VERIDEX CORE · NEMOTRON CONCEPT</div><div class="core-title">{state_label}</div><div class="core-description">{state_detail} 3D animation is decorative; no model is connected.</div></div></div>',unsafe_allow_html=True)
        stages=[('Scan',1),('Investigate',3),('Patch',4),('Validate',5),('Review',6)]
        steps=''.join(f'<span class="workflow-step {"done" if st.session_state.run_step>=threshold else "current" if st.session_state.run_step==threshold-1 else ""}">{label}</span>' for label,threshold in stages)
        st.markdown('<div class="workflow">'+steps+'</div>',unsafe_allow_html=True)
        st.markdown('#### Investigation control')
        st.caption('Advance through the demonstration one event at a time, or run the full scripted sequence.')
        x,y,z=st.columns([1,1,1])
        if x.button('▶ Run demo',type='primary',use_container_width=True):
            if st.session_state.demo_animation:
                # The animation lives in a standalone iframe. Allow the full CSS flight
                # to finish before rerunning Streamlit; otherwise it vanishes immediately.
                st.caption('Playing 1.15-second code transformation · illustrative demo')
                components.html(animation_frame(ORIGINAL, CANDIDATES[st.session_state.candidate]),height=302,scrolling=False)
                progress_bar=st.progress(0,text='Visualizing proposed patch')
                for index in range(23):
                    time.sleep(0.05)
                    progress_bar.progress((index+1)/23,text='Visualizing proposed patch' if index<22 else 'Demonstration complete')
            st.session_state.run_step=len(EVENTS)
            st.rerun()
        if y.button('→ Next action',use_container_width=True,disabled=st.session_state.run_step>=len(EVENTS)):
            st.session_state.run_step+=1
            st.rerun()
        if z.button('↺ Restart',use_container_width=True):
            st.session_state.run_step=0
            st.rerun()
        st.progress(st.session_state.run_step/len(EVENTS),text=f'Demo progress · {st.session_state.run_step} of {len(EVENTS)} actions')
        st.markdown('#### Vulnerability explorer')
        q1,q2=st.columns(2)
        with q1: severity=st.selectbox('Severity',['All','Critical','High','Medium'])
        with q2: status=st.selectbox('Status',['All','Pending','Needs review','Scan cleared*'])
        shown=[f for f in FINDINGS if (severity=='All' or f['severity']==severity) and (status=='All' or f['status']==status)]
        if not shown: status_card('No findings match these filters.', 'info')
        for f in shown:
            with st.container(border=True):
                t1,t2=st.columns([4,1])
                with t1:
                    st.markdown(f"**{f['id']} · {f['name']}**")
                    st.caption(f"{f['file']} : {f['line']}  ·  {f['category']}  ·  {f['status']}")
                with t2:
                    if st.button('Inspect',key='inspect_'+f['id'],use_container_width=True):st.session_state.selected_id=f['id']
                st.markdown(f"<span class='tag {'tag-muted' if f['severity']=='Medium' else ''}'>{f['severity']}</span>",unsafe_allow_html=True)
    with right:
        st.markdown('#### Agent telemetry')
        rendered=EVENTS[:st.session_state.run_step]
        lines=''.join(f'<div class="event"><b>{html.escape(kind)}</b> · {html.escape(title)}<small>{html.escape(detail)}</small></div>' for kind,title,detail in rendered)
        if not lines: lines='<div class="event">Waiting for demo to begin.<small>Press Run demo or Next action to populate this feed.</small></div>'
        st.markdown('<div class="darkpanel"><div class="heading">◉ Activity stream <span style="float:right;color:#9fdf58;font-size:11px">SIMULATED</span></div>'+lines+'</div>',unsafe_allow_html=True)
        if st.session_state.run_step==len(EVENTS):status_card('Demo sequence complete · review the proposed patch below.', 'pass')
        else:st.caption('Activity entries are scripted; they do not represent real model tool calls. Animation reflects the current demo step only.')
    st.divider()
    selected=next(f for f in FINDINGS if f['id']==st.session_state.selected_id)
    st.markdown(f"#### Finding details · {selected['id']}")
    st.markdown(f"**{selected['name']}**")
    st.caption(selected['detail'])
    if selected['id']=='SEC-001':
        st.markdown('#### Patch Arena · compare two approaches')
        st.caption('Two prewritten candidates illustrate how a review gate could reject a plausible-looking but unsafe patch. Neither was generated by Nemotron.')
        candidate_name=st.radio('Select patch candidate', list(CANDIDATES), key='candidate', horizontal=True)
        candidate_code=CANDIDATES[candidate_name]
        review=REVIEW_BY_CANDIDATE[candidate_name]
        st.markdown('#### Proposed code change')
        if st.session_state.show_morph:
            with st.expander('◈ Code transformation visual',expanded=False):
                st.caption('Select **Animate demo run** and click **Run demo** to watch the original code rotate into the proposed patch. The comparison below shows the actual changed lines.')
                st.caption('Illustrative original → proposed patch transition. Open the animated run in the investigation controls above to see the spiral in motion.')
        st.caption('Green + = added/changed lines · Red − = removed/changed lines · Line numbers reference the respective file')
        before,after=st.columns(2,gap='medium')
        with before:
            st.caption('ORIGINAL · READ ONLY')
            st.markdown(highlighted_code(ORIGINAL,candidate_code,'before') if st.session_state.show_highlights else '<div class="codepanel">'+html.escape(ORIGINAL)+'</div>',unsafe_allow_html=True)
        with after:
            st.caption('PROPOSED · DEMONSTRATION PATCH')
            st.markdown(highlighted_code(candidate_code,ORIGINAL,'after') if st.session_state.show_highlights else '<div class="codepanel">'+html.escape(candidate_code)+'</div>',unsafe_allow_html=True)
        v1,v2,v3=st.columns(3)
        v1.metric('Python syntax','Passed' if syntax_result(candidate_code)['passed'] else 'Failed')
        v2.metric('OpenGrep rescan','Not run')
        v3.metric('Original files','Unchanged')
        st.caption('* “Scan cleared” is an illustrative scenario status, not a measured scanner result. No real security verification has occurred.')
        selected_patch=patch_text(ORIGINAL,candidate_code,'tests/vulnerable_sample.py')
        if st.button('✓ Choose recommended candidate',help='Switches to the parameterized-query sample, without modifying any files'):
            st.session_state.candidate='Parameterized query (recommended)'
            st.rerun()
        st.download_button('↓ Export selected demo .patch',data=selected_patch,file_name='veridex-sample.patch',mime='text/x-patch',use_container_width=False)
        with st.expander('View raw unified diff (exact changed lines)'):
            st.code(selected_patch,language='diff')
        st.markdown('#### Adversarial Review · second opinion')
        st.caption('Scripted reviewer scenario. A real implementation will use a separate Nemotron call and ground its conclusions in tool evidence.')
        if review['status'].startswith('REJECT'):
            st.error('Review gate: ' + review['status'])
        else:
            status_card('Review gate: ' + review['status'], 'warning' if 'REJECT' in review['status'] else 'pass')
        st.write(review['summary'])
        for concern in review['concerns']:
            st.markdown('- ' + concern)
        st.markdown('#### Remediation policies')
        st.caption('These two constraints are evaluated by local Python code, not by an AI model.')
        cpol1,cpol2=st.columns(2)
        with cpol1: st.checkbox('Prefer small diff',key='policy_minimal')
        with cpol2: st.checkbox('No new imports',key='policy_no_imports')
        checks=policy_check(ORIGINAL,candidate_code,st.session_state.policy_minimal,st.session_state.policy_no_imports)
        for check in checks:
            status_card(('PASS' if check['passed'] else 'CHECK')+' · '+check['name']+' — '+check['detail'], 'pass' if check['passed'] else 'warning')
        st.markdown('#### Evidence Passport')
        st.caption('Download an auditable JSON record of what was shown, which checks really ran, and what remains unverified.')
        event_records=[{'type':kind,'title':title,'detail':detail,'mode':'SIMULATED'} for kind,title,detail in EVENTS[:st.session_state.run_step]]
        passport=passport_json(ORIGINAL,candidate_code,checks,review,event_records,selected)
        st.download_button('↓ Download Evidence Passport (.json)',data=passport,file_name='veridex-evidence-passport.json',mime='application/json')
        with st.expander('Inspect Evidence Passport'):
            st.json(json.loads(passport))
        st.markdown('#### Human steering · UI preview')
        st.caption('Try leaving feedback on the proposal. In this prototype it is recorded locally but is not sent to an AI model.')
        with st.form('steer_form',clear_on_submit=True):
            steering=st.text_input('Revision request',placeholder='e.g. Keep the change minimal and add a comment')
            submit=st.form_submit_button('Save feedback')
            if submit and steering.strip():st.session_state.steering.append(steering.strip())
        for i,request in enumerate(st.session_state.steering,1):status_card(f'Feedback {i}: {request} · awaiting live agent integration', 'info')
    else:
        status_card('This finding is included for UI exploration. Only SEC-001 has a sample patch in demo mode.', 'info')

with tab_exec:
    st.markdown('### Security posture')
    st.caption('An executive-friendly view of the same illustrative dataset. No real repository scan has run.')
    a,b,c=st.columns(3)
    a.metric('Open findings','02')
    b.metric('Critical exposure','01')
    c.metric('Proposed remediations','01')
    st.write('')
    col1,col2=st.columns([1.1,1],gap='large')
    with col1:
        st.markdown('#### Findings by severity')
        import altair as alt
        chart_dark = st.session_state.display_mode == 'Dark'
        chart_ink = '#F0F4F0' if chart_dark else '#172319'
        chart_grid = '#303830' if chart_dark else '#E0E5E0'
        chart_data = [{'Severity':'Critical','Findings':1},{'Severity':'High','Findings':1},{'Severity':'Medium','Findings':1}]
        severity_chart = (alt.Chart(alt.Data(values=chart_data))
            .mark_bar(color='#76B900', cornerRadiusEnd=6, size=35)
            .encode(y=alt.Y('Severity:N',sort=['Critical','High','Medium'],axis=alt.Axis(title=None,labelColor=chart_ink,labelFontSize=14,labelPadding=12,ticks=False,domain=False)),
                    x=alt.X('Findings:Q',scale=alt.Scale(domain=[0,1.25]),axis=alt.Axis(title='Number of findings',titleColor=chart_ink,labelColor=chart_ink,gridColor=chart_grid,domain=False,tickColor=chart_grid,values=[0,1])),
                    tooltip=['Severity:N','Findings:Q'])
            .properties(height=350,background='transparent',padding={'left':5,'top':12,'right':16,'bottom':8})
            .configure_view(stroke=None))
        st.altair_chart(severity_chart,use_container_width=True,theme=None)
    with col2:
        st.markdown('#### Remediation snapshot')
        st.markdown('''<div class="panel"><h4>1 proposed remediation</h4><p>SQL injection · sample project<br>Syntax parsed locally. Scanner rescan not executed.<br><br>2 additional findings are pending or require review.</p></div>''',unsafe_allow_html=True)
        st.markdown('''<div class="panel"><h4>Human oversight is essential</h4><p>All exported patches are proposals. Scanner results alone cannot establish security or functional correctness.</p></div>''',unsafe_allow_html=True)
    st.markdown('#### Decision readiness')
    x,y,z=st.columns(3)
    with x: st.markdown('<div class="panel"><h4>Detection</h4><p>Three sample findings illustrate severity-based prioritization. No repository was scanned.</p></div>',unsafe_allow_html=True)
    with y: st.markdown('<div class="panel"><h4>Remediation</h4><p>Compare a recommended SQL patch against a deliberately unsafe candidate in Patch Arena.</p></div>',unsafe_allow_html=True)
    with z: st.markdown('<div class="panel"><h4>Assurance</h4><p>Syntax and policy checks are local. AI review and scanner clearance remain unverified.</p></div>',unsafe_allow_html=True)
    st.markdown('#### Findings inventory')
    st.dataframe([{k:f[k] for k in ('id','name','severity','status','file')} for f in FINDINGS],use_container_width=True,hide_index=True)

with tab_about:
    st.markdown('### How the full product will work')
    st.markdown('<div class="panel"><h4>Designed for NVIDIA Nemotron</h4><p>Nemotron is the planned reasoning engine for source inspection, tool selection, patch proposals and adversarial review. This prototype does not make NVIDIA API calls and is not an official NVIDIA product.</p></div>',unsafe_allow_html=True)
    st.markdown('''<div class="panel"><h4>Scan → Investigate → Patch → Validate → Review</h4><p>The planned production workflow uses NVIDIA Nemotron to choose approved investigation tools, OpenGrep to detect potential vulnerabilities, Python AST parsing to validate syntax, and a read-only original repository with patch export.</p></div>''',unsafe_allow_html=True)
    a,b=st.columns(2)
    with a:
        st.markdown('#### Implemented in this preview')
        st.markdown('- Interactive filters and finding selection\n- Step-through demonstration and telemetry\n- Before-and-after code inspection\n- Real local AST parsing of sample patch\n- Unified diff export\n- Feedback capture in session\n- Executive summary\n- Patch Arena with two scripted candidates\n- Scripted adversarial review and real local policy checks\n- Downloadable Evidence Passport (JSON)\n- Animated optional demo loading with spiral code visualization\n- Color-highlighted changed lines and candidate quick-select\n- Sidebar accessibility and visualization toggles')
    with b:
        st.markdown('#### Planned integrations')
        st.markdown('- NVIDIA Nemotron inference and tool calling\n- OpenGrep execution and JSON parsing\n- Isolated working-copy patch application\n- Automated scan comparison and bounded retries\n- Agent-driven human steering\n- Custom policy uploads (stretch goal)\n- Evidence-grounded Nemotron reviewer (currently scripted)')
    st.caption('Independent HackUTD concept using NVIDIA-inspired colors. Not an official NVIDIA product or endorsement.')
