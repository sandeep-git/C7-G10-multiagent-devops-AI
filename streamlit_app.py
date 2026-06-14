"""
Streamlit UI — DevOps Incident Analysis Suite
Design: Purple-indigo gradient bg · white floating cards · clean enterprise look
"""
from __future__ import annotations
import os, time
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── Page config ────────────────────────────────────────────────────
st.set_page_config(
    page_title="DevOps Incident Analysis Suite",
    page_icon="🚨",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ─────────────────────────────────────────────────────
st.markdown("""
<style>
/* ---- gradient background ---- */
.stApp {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
}
/* hide default streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding-top: 4rem !important;
    padding-bottom: 4rem !important;
    max-width: 820px !important;
}

/* ---- white card ---- */
.card {
    background: #ffffff;
    border-radius: 20px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.25);
    padding: 40px 44px;
    margin-bottom: 24px;
}
.card-title {
    font-size: 26px;
    font-weight: 700;
    color: #1a1a2e;
    margin: 0 0 6px 0;
}
.card-sub {
    font-size: 14px;
    color: #6b7280;
    margin: 0 0 28px 0;
}

/* ---- primary purple button ---- */
.stButton > button {
    background: #6c63ff !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 12px 28px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    width: 100% !important;
    cursor: pointer !important;
    transition: background .2s, transform .1s !important;
    box-shadow: 0 4px 15px rgba(108,99,255,.35) !important;
}
.stButton > button:hover {
    background: #574fd6 !important;
    transform: translateY(-1px) !important;
}
.stButton > button:disabled {
    background: #a5a0f5 !important;
    cursor: not-allowed !important;
}

/* ---- secondary / danger buttons ---- */
button[kind="secondary"] {
    background: #f1f0ff !important;
    color: #6c63ff !important;
    box-shadow: none !important;
}
.reject-btn > button {
    background: #fff0f0 !important;
    color: #e53935 !important;
    box-shadow: 0 4px 15px rgba(229,57,53,.15) !important;
}
.reject-btn > button:hover {
    background: #ffe0e0 !important;
}

/* ---- upload zone ---- */
[data-testid="stFileUploaderDropzone"] {
    background: #f9f8ff !important;
    border: 2px dashed #c4c0f7 !important;
    border-radius: 14px !important;
    padding: 28px !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: #6c63ff !important;
    background: #f3f1ff !important;
}

/* ---- text area ---- */
.stTextArea textarea {
    background: #f9f8ff !important;
    border: 1.5px solid #e0deff !important;
    border-radius: 10px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important;
    color: #374151 !important;
}
.stTextArea textarea:focus {
    border-color: #6c63ff !important;
    box-shadow: 0 0 0 3px rgba(108,99,255,.15) !important;
}

/* ---- pipeline node pills ---- */
.node-done {
    background: #f0fdf4; border: 1.5px solid #86efac;
    border-radius: 12px; padding: 10px 16px; margin: 4px 0;
    display: flex; align-items: center; gap: 10px;
}
.node-active {
    background: #f5f3ff; border: 2px solid #6c63ff;
    border-radius: 12px; padding: 10px 16px; margin: 4px 0;
    display: flex; align-items: center; gap: 10px;
    box-shadow: 0 0 0 4px rgba(108,99,255,.12);
}
.node-pending {
    background: #f9fafb; border: 1.5px solid #e5e7eb;
    border-radius: 12px; padding: 10px 16px; margin: 4px 0;
    display: flex; align-items: center; gap: 10px; opacity: .55;
}
.node-label { font-weight: 600; font-size: 14px; color: #1a1a2e; }
.node-badge-done   { margin-left:auto; color:#16a34a; font-size:13px; font-weight:700; }
.node-badge-active { margin-left:auto; color:#6c63ff; font-size:13px; font-weight:700; }
.node-badge-pend   { margin-left:auto; color:#9ca3af; font-size:13px; }

/* ---- log viewer ---- */
.log-wrap {
    background: #1a1a2e; border-radius: 12px;
    padding: 12px 4px; max-height: 380px; overflow-y: auto;
    border: 1px solid #2d2b55;
}
.log-err  { padding: 2px 12px; font-family: monospace; font-size: 12px;
             color: #fca5a5; border-left: 3px solid #dc2626; background: #450a0a22; }
.log-warn { padding: 2px 12px; font-family: monospace; font-size: 12px;
             color: #fde68a; border-left: 3px solid #f59e0b; background: #78350f22; }
.log-info { padding: 2px 12px; font-family: monospace; font-size: 12px;
             color: #94a3b8; border-left: 3px solid transparent; }

/* ---- severity badge ---- */
.sev-banner {
    border-radius: 12px; padding: 12px 16px; margin-bottom: 12px;
    font-size: 13px; line-height: 1.6;
}
.sev-5 { background:#450a0a; border-left:4px solid #dc2626; color:#fca5a5; }
.sev-4 { background:#431407; border-left:4px solid #ea580c; color:#fdba74; }
.sev-3 { background:#422006; border-left:4px solid #d97706; color:#fde68a; }
.sev-2 { background:#052e16; border-left:4px solid #16a34a; color:#86efac; }
.sev-1 { background:#0c1a2e; border-left:4px solid #2563eb; color:#93c5fd; }

/* ---- action hub cards ---- */
.hub-card {
    background: #f5f3ff; border: 1.5px solid #c4c0f7;
    border-radius: 14px; padding: 18px 20px;
}
.hub-card a { color: #6c63ff; font-weight: 600; font-size: 13px; text-decoration: none; }
.hub-card a:hover { text-decoration: underline; }

/* ---- audit log ---- */
.audit-box {
    background: #f9f8ff; border: 1px solid #e0deff;
    border-radius: 10px; padding: 10px 14px;
    font-size: 12px; line-height: 1.7; color: #4b5563;
    max-height: 180px; overflow-y: auto;
}
/* ---- divider ---- */
hr { border-color: #e5e7eb !important; }
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────
for k, v in {"run_id": None, "raw_logs": "", "pipeline_state": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── API helpers ────────────────────────────────────────────────────
def api_analyze(logs: str) -> dict:
    r = requests.post(f"{BACKEND}/api/analyze", json={"logs": logs}, timeout=10)
    r.raise_for_status(); return r.json()

def api_analyze_file(content: bytes, name: str) -> dict:
    r = requests.post(f"{BACKEND}/api/analyze/upload",
                      files={"file": (name, content, "text/plain")}, timeout=10)
    r.raise_for_status(); return r.json()

def api_get_run(run_id: str) -> dict:
    r = requests.get(f"{BACKEND}/api/runs/{run_id}", timeout=10)
    r.raise_for_status(); return r.json()

def api_approve(run_id: str, decision: str) -> dict:
    r = requests.post(f"{BACKEND}/api/runs/{run_id}/approve",
                      json={"run_id": run_id, "decision": decision}, timeout=10)
    r.raise_for_status(); return r.json()

# ── Constants ──────────────────────────────────────────────────────
NODES = [
    ("log_classifier",       "🔍", "Log Classifier"),
    ("remediation_agent",    "🧠", "Remediation Agent"),
    ("cookbook_synthesizer", "📝", "Cookbook Synthesizer"),
    ("hitl_approval",        "👤", "HITL Approval"),
    ("jira_agent",           "🎫", "Jira Agent"),
    ("notification_agent",   "💬", "Slack Agent"),
    ("end",                  "✅", "Complete"),
]
NODE_IDS = [n[0] for n in NODES]
SEV = {1:("🔵","INFO","sev-1"), 2:("🟢","LOW","sev-2"),
       3:("🟡","MEDIUM","sev-3"), 4:("🟠","HIGH","sev-4"), 5:("🔴","CRITICAL","sev-5")}

# ─────────────────────────────────────────────────────────────────
# ── INGESTION VIEW ────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────
if not st.session_state.run_id:
    st.markdown("""
    <div class="card">
        <p class="card-title">🚨 DevOps Incident Analysis Suite</p>
        <p class="card-sub">Upload your log file and get AI-powered insights</p>
        <p style="margin:0;font-size:13px">
            🌐 Live App:&nbsp;
            <a href="https://sandeepg06-devops-incident-suite.hf.space" target="_blank"
               style="color:#6c63ff;font-weight:600;text-decoration:none">
               sandeepg06-devops-incident-suite.hf.space
            </a>
            &nbsp;·&nbsp;
            📦 GitHub:&nbsp;
            <a href="https://github.com/sandeep-git/C7-G10-multiagent-devops-AI" target="_blank"
               style="color:#6c63ff;font-weight:600;text-decoration:none">
               C7-G10-multiagent-devops-AI
            </a>
        </p>
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Choose Log File",
        type=["log", "txt", "json"],
        label_visibility="collapsed",
    )
    if uploaded:
        st.caption(f"📄 **{uploaded.name}** selected")

    st.markdown("**— or paste logs directly —**")
    pasted = st.text_area(
        "Paste logs",
        height=140,
        placeholder="2024-06-13 ERROR payment-service Connection pool exhausted...",
        label_visibility="collapsed",
    )

    clicked = st.button("Analyze Logs", use_container_width=True)

    if clicked:
        if not uploaded and not pasted.strip():
            st.warning("Please upload a file or paste some logs.")
            st.stop()
        with st.spinner("Starting analysis pipeline..."):
            try:
                if uploaded:
                    content = uploaded.read()
                    st.session_state.raw_logs = content.decode("utf-8", errors="replace")
                    result = api_analyze_file(content, uploaded.name)
                else:
                    st.session_state.raw_logs = pasted
                    result = api_analyze(pasted)
                st.session_state.run_id = result["run_id"]
                st.session_state.pipeline_state = result
                st.rerun()
            except Exception as e:
                st.error(f"Failed to start: {e}")
    st.stop()

# ─────────────────────────────────────────────────────────────────
# ── LIVE PIPELINE VIEW ────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────

# Poll fresh state
try:
    st.session_state.pipeline_state = api_get_run(st.session_state.run_id)
except Exception:
    pass

state        = st.session_state.pipeline_state or {}
current_node = state.get("current_node", "start")
approval     = state.get("approval_status", "pending")
messages     = state.get("messages", [])
log_analysis = state.get("log_analysis")
runbook      = state.get("runbook")
jira_result  = state.get("jira_result")
slack_result = state.get("slack_result")
ext_links    = state.get("external_links", {})
error        = state.get("error")

# ── Top bar ────────────────────────────────────────────────────────
top_l, top_r = st.columns([6, 2])
with top_l:
    st.markdown("""
    <div style="background:white;border-radius:16px;padding:18px 24px;box-shadow:0 8px 30px rgba(0,0,0,.15);margin-bottom:20px">
        <span style="font-size:22px;font-weight:700;color:#1a1a2e">🚨 DevOps Incident Analysis Suite</span><br>
        <span style="font-size:13px;color:#6b7280">Multi-Agent Pipeline · OpenRouter · ChromaDB RAG</span>
        &nbsp;&nbsp;
        <a href="https://sandeepg06-devops-incident-suite.hf.space" target="_blank"
           style="font-size:12px;color:#6c63ff;font-weight:600;text-decoration:none">
           🌐 Live on HF Spaces
        </a>
        &nbsp;·&nbsp;
        <a href="https://github.com/sandeep-git/C7-G10-multiagent-devops-AI" target="_blank"
           style="font-size:12px;color:#6c63ff;font-weight:600;text-decoration:none">
           📦 GitHub
        </a>
    </div>
    """, unsafe_allow_html=True)
with top_r:
    st.markdown("<div style='padding-top:10px'>", unsafe_allow_html=True)
    if st.button("← New Analysis"):
        st.session_state.run_id = None
        st.session_state.raw_logs = ""
        st.session_state.pipeline_state = None
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ── HITL Approval Banner — always visible, above everything ────────
if current_node == "hitl_approval" and approval == "pending":
    st.markdown("""
    <style>
    div[data-testid="stForm"] {
        background: #ffffff !important;
        border: 2.5px solid #6c63ff !important;
        border-radius: 16px !important;
        padding: 24px 28px 20px 28px !important;
        box-shadow: 0 4px 24px rgba(108,99,255,.18) !important;
        margin-bottom: 20px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    with st.form("hitl_form", clear_on_submit=False):
        st.markdown("""
        <div style="font-size:17px;font-weight:700;color:#6c63ff;margin-bottom:6px">
            👤 Human Approval Required
        </div>
        <div style="color:#4b5563;font-size:13px;margin-bottom:18px">
            Agents 1–3 have completed. Review the runbook in the tab below,
            then approve or reject deployment to Jira &amp; Slack.
        </div>
        """, unsafe_allow_html=True)
        hitl_a, hitl_r = st.columns(2)
        with hitl_a:
            approve_clicked = st.form_submit_button(
                "✅  Approve & Deploy",
                use_container_width=True,
                type="primary",
            )
        with hitl_r:
            reject_clicked = st.form_submit_button(
                "❌  Reject",
                use_container_width=True,
            )

    if approve_clicked:
        try:
            r = api_approve(st.session_state.run_id, "approved")
            st.session_state.pipeline_state = r
            st.success("Approved! Running Jira + Slack agents...")
            time.sleep(1); st.rerun()
        except Exception as e:
            st.error(str(e))
    if reject_clicked:
        try:
            r = api_approve(st.session_state.run_id, "rejected")
            st.session_state.pipeline_state = r
            st.rerun()
        except Exception as e:
            st.error(str(e))

elif approval == "approved":
    st.markdown("""
    <div style="background:#f0fdf4;border:1.5px solid #86efac;border-radius:14px;
                padding:14px 20px;margin-bottom:16px;color:#15803d;font-weight:600">
        ✅ Approved — Jira &amp; Slack agents running...
    </div>
    """, unsafe_allow_html=True)
elif approval == "rejected":
    st.markdown("""
    <div style="background:#fef2f2;border:1.5px solid #fca5a5;border-radius:14px;
                padding:14px 20px;margin-bottom:16px;color:#dc2626;font-weight:600">
        ✗ Pipeline rejected by human operator.
    </div>
    """, unsafe_allow_html=True)

# ── Main two-column layout ─────────────────────────────────────────
col_left, col_right = st.columns([1, 2])

# ── LEFT: Pipeline nodes + audit log ──────────────────────────────
with col_left:
    st.markdown('<div class="card" style="padding:24px 20px">', unsafe_allow_html=True)
    st.markdown('<p style="font-weight:700;color:#1a1a2e;font-size:15px;margin:0 0 12px 0">Pipeline</p>', unsafe_allow_html=True)

    ci = NODE_IDS.index(current_node) if current_node in NODE_IDS else -1
    for node_id, icon, label in NODES:
        ni = NODE_IDS.index(node_id)
        if ni < ci:
            st.markdown(f'<div class="node-done"><span>{icon}</span><span class="node-label">{label}</span><span class="node-badge-done">✓</span></div>', unsafe_allow_html=True)
        elif ni == ci:
            st.markdown(f'<div class="node-active"><span>{icon}</span><span class="node-label">{label}</span><span class="node-badge-active">●</span></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="node-pending"><span>{icon}</span><span class="node-label" style="color:#9ca3af">{label}</span><span class="node-badge-pend">○</span></div>', unsafe_allow_html=True)

    if messages:
        st.markdown('<p style="font-weight:700;color:#1a1a2e;font-size:14px;margin:16px 0 8px 0">Audit Log</p>', unsafe_allow_html=True)
        log_lines = "".join(f'<div>{i+1}. {m}</div>' for i, m in enumerate(messages))
        st.markdown(f'<div class="audit-box">{log_lines}</div>', unsafe_allow_html=True)

    if error:
        st.markdown(f'<div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:10px;padding:10px 14px;margin-top:12px;color:#dc2626;font-size:13px">⚠️ {error}</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ── RIGHT: Log view + Runbook ──────────────────────────────────────
with col_right:
    # Severity banner
    if log_analysis:
        sev = log_analysis.get("overall_severity", 1)
        emoji, label, cls = SEV.get(sev, ("⚪","UNKNOWN","sev-1"))
        services = ", ".join(log_analysis.get("affected_services", []))
        hypo = log_analysis.get("root_cause_hypothesis", "")[:200]
        st.markdown(
            f'<div class="sev-banner {cls}">'
            f'<b>{emoji} Severity: {label} ({sev}/5)</b> &nbsp;·&nbsp; {services}<br>'
            f'<span style="opacity:.85;font-size:12px">{hypo}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Tabs: Logs | Runbook ───────────────────────────────────────
    tab_log, tab_rb = st.tabs(["📋 Log File", "📝 Runbook"])

    with tab_log:
        raw = st.session_state.raw_logs
        if raw:
            rows = []
            for i, line in enumerate(raw.split("\n")):
                ln = line.lower()
                if any(k in ln for k in ["error","fatal","exception","oom","killed","exhausted","refused"]):
                    css = "log-err"
                elif any(k in ln for k in ["warn","timeout","retry","failed","spike","pressure"]):
                    css = "log-warn"
                else:
                    css = "log-info"
                safe = line.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                rows.append(f'<div class="{css}"><span style="color:#475569;margin-right:8px;user-select:none">{i+1}</span>{safe}</div>')
            st.markdown(f'<div class="log-wrap">{"".join(rows)}</div>', unsafe_allow_html=True)
        else:
            st.info("No log content loaded.")

    with tab_rb:
        if not runbook:
            st.markdown("""
            <div style="text-align:center;padding:40px 20px;color:#9ca3af">
                <div style="font-size:40px;margin-bottom:8px">📝</div>
                Runbook will appear here once the<br>Cookbook Synthesizer completes...
            </div>
            """, unsafe_allow_html=True)
        else:
            title = runbook.get("title","Runbook")
            eta   = runbook.get("estimated_time_minutes","?")
            steps = runbook.get("steps",[])
            destructive = any(s.get("is_destructive") for s in steps)

            st.markdown(f"""
            <div style="background:#ffffff;border:1.5px solid #e5e7eb;border-radius:12px;padding:14px 18px;margin-bottom:12px;box-shadow:0 2px 8px rgba(0,0,0,.06)">
                <span style="font-size:17px;font-weight:700;color:#1a1a2e">{title}</span><br>
                <span style="color:#6b7280;font-size:13px">⏱ ~{eta} min &nbsp;·&nbsp; {len(steps)} steps</span>
            </div>
            """, unsafe_allow_html=True)

            if destructive:
                st.warning("⚠️ Contains destructive operations — review carefully before approving.")

            # Render markdown runbook
            md = runbook.get("markdown","")
            if md:
                st.markdown(
                    f'<div style="background:#ffffff;border:1.5px solid #e5e7eb;border-radius:14px;'
                    f'padding:24px 28px;margin-top:8px;color:#1a1a2e;line-height:1.8">{md}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown('<div style="background:#ffffff;border:1.5px solid #e5e7eb;border-radius:14px;padding:24px 28px;margin-top:8px">', unsafe_allow_html=True)
                for s in steps:
                    warn = f"\n> ⚠️ {s['warning']}" if s.get("warning") else ""
                    st.markdown(f"**{s['order']}.** {s['description']}{warn}")
                    if s.get("command"):
                        st.code(s["command"], language="bash")
                st.markdown('</div>', unsafe_allow_html=True)

# ── Action Hub ─────────────────────────────────────────────────────
if ext_links.get("jira") or ext_links.get("slack"):
    st.markdown("---")
    st.markdown("""
    <div style="background:white;border-radius:16px;box-shadow:0 8px 30px rgba(0,0,0,.1);padding:24px 28px;margin-bottom:8px">
        <p style="font-size:17px;font-weight:700;color:#1a1a2e;margin:0 0 16px 0">🎯 Action Hub</p>
    """, unsafe_allow_html=True)

    hub_l, hub_r = st.columns(2)
    with hub_l:
        if ext_links.get("jira"):
            priority = jira_result.get("priority","—") if jira_result else "—"
            st.markdown(f"""
            <div class="hub-card">
                <div style="font-size:22px;margin-bottom:6px">🎫</div>
                <b style="color:#1a1a2e">Jira Ticket Created</b><br>
                <a href="{ext_links['jira']}" target="_blank">{ext_links['jira']}</a><br>
                <span style="color:#9ca3af;font-size:12px">Priority: {priority}</span>
            </div>
            """, unsafe_allow_html=True)
    with hub_r:
        if ext_links.get("slack"):
            channel = slack_result.get("channel","#incidents") if slack_result else "#incidents"
            st.markdown(f"""
            <div class="hub-card">
                <div style="font-size:22px;margin-bottom:6px">💬</div>
                <b style="color:#1a1a2e">Slack Notification Sent</b><br>
                <a href="{ext_links['slack']}" target="_blank">{ext_links['slack']}</a><br>
                <span style="color:#9ca3af;font-size:12px">Channel: {channel}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ── Auto-refresh while pipeline is in flight ───────────────────────
if current_node not in ("end", "hitl_approval") and not error:
    time.sleep(3)
    st.rerun()
