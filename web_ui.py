#!/usr/bin/env python3
"""
TradingAgents Web UI - Clean Modern Interface
Run with: streamlit run web_ui.py
"""
import os
import sys
import streamlit as st
from datetime import datetime, timedelta
import json
from pathlib import Path
from io import BytesIO

# Add TradingAgents to path
sys.path.insert(0, "/root/.openclaw/workspace/TradingAgents")

# Page config - must be first Streamlit command
st.set_page_config(
    page_title="TradingAgents",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Default configuration
DEFAULT_CONFIG = {
    "api_key": "sk-nano-67fb7b23-5505-491b-ac1f-c08f45ed30e0",
    "base_url": "https://nano-gpt.com/api/v1",
    "model": "zai-org/glm-5.1",
    "provider_name": "Z.AI GLM 5.1"
}

# Data storage
DATA_DIR = Path("/root/.openclaw/workspace/TradingAgents/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ============================================
# SESSION STATE - Initialize ALL at startup
# ============================================
def init_session_state():
    """Initialize all session state variables"""
    import threading
    defaults = {
        "page": "analyze",
        "view_analysis": None,
        "stop_analysis": False,
        "stop_event": None,  # Will be created as threading.Event when needed
        "analysis_running": False,
        "current_logs": [],
        "step_status": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Call immediately
init_session_state()

def get_analyses_file():
    return DATA_DIR / "analyses.json"

def load_analyses():
    f = get_analyses_file()
    if f.exists():
        with open(f, 'r') as file:
            return json.load(file)
    return []

def save_analyses(analyses):
    with open(get_analyses_file(), 'w') as f:
        json.dump(analyses, f, indent=2)

def get_settings_file():
    return DATA_DIR / "settings.json"

def load_settings():
    f = get_settings_file()
    if f.exists():
        with open(f, 'r') as file:
            return json.load(file)
    return DEFAULT_CONFIG.copy()

def save_settings(settings):
    with open(get_settings_file(), 'w') as f:
        json.dump(settings, f, indent=2)

# ============================================
# BACKGROUND JOB MANAGEMENT
# ============================================
JOBS_DIR = DATA_DIR / "jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)

def get_running_jobs():
    """Get list of running/pending jobs"""
    jobs = []
    for job_file in JOBS_DIR.glob("*.json"):
        try:
            job = json.loads(job_file.read_text())
            if job.get("status") in ("running", "pending"):
                jobs.append(job)
        except:
            pass
    return sorted(jobs, key=lambda x: x.get("started_at", ""), reverse=True)

def get_job(job_id: str):
    """Get a specific job by ID"""
    job_file = JOBS_DIR / f"{job_id}.json"
    if job_file.exists():
        return json.loads(job_file.read_text())
    return None

def start_background_job(ticker, analysis_date, selected_analysts, depth):
    """Start a background analysis job"""
    import subprocess
    import uuid
    
    job_id = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    settings = load_settings()
    
    # Start the background worker
    cmd = [
        sys.executable,
        str(Path(__file__).parent / "background_worker.py"),
        "--job-id", job_id,
        "--ticker", ticker,
        "--date", str(analysis_date),
        "--analysts", ",".join(selected_analysts),
        "--depth", str(depth),
        "--api-key", settings.get("api_key", DEFAULT_CONFIG["api_key"]),
        "--base-url", settings.get("base_url", DEFAULT_CONFIG["base_url"]),
        "--model", settings.get("model", DEFAULT_CONFIG["model"]),
    ]
    
    # Start as detached process
    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    
    return job_id

def stop_job(job_id: str):
    """Request a job to stop"""
    job_file = JOBS_DIR / f"{job_id}.json"
    if job_file.exists():
        job = json.loads(job_file.read_text())
        job["stop_requested"] = True
        job_file.write_text(json.dumps(job, indent=2))

def render_job_status(job):
    """Render the status of a running/completed job"""
    job_id = job.get("job_id", "unknown")
    ticker = job.get("ticker", "?")
    status = job.get("status", "unknown")
    progress = job.get("progress", {})
    logs = job.get("logs", [])
    result = job.get("result")
    error = job.get("error")
    started_at = job.get("started_at", "")
    
    # Status badge
    status_colors = {
        "running": "#4CAF50",
        "completed": "#2196F3",
        "failed": "#f44336",
        "stopped": "#FF9800"
    }
    status_color = status_colors.get(status, "#888")
    
    st.markdown(f"""
    <div style="background: #1a1a2e; border-radius: 12px; padding: 20px; margin: 10px 0;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <span style="font-size: 1.5em; font-weight: bold;">{ticker}</span>
                <span style="color: #888; margin-left: 10px;">{started_at[:19].replace('T', ' ') if started_at else ''}</span>
            </div>
            <span style="background: {status_color}; padding: 4px 12px; border-radius: 20px; font-size: 0.9em;">{status.upper()}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if status == "running":
        # Progress steps
        steps = [
            ("init", "Initializing"),
            ("market", "Market data"),
            ("analysts", "Analysts"),
            ("research", "Research"),
            ("trading", "Trading plan"),
            ("risk", "Risk assessment"),
            ("final", "Final decision"),
        ]
        
        step_html = ""
        for key, name in steps:
            p_status = progress.get(key, "pending")
            icon = "✓" if p_status == "done" else ("●" if p_status == "active" else "○")
            color = "#4CAF50" if p_status == "done" else ("#667eea" if p_status == "active" else "#555")
            step_html += f'<span style="color: {color}; margin-right: 15px;">{icon} {name}</span>'
        
        st.markdown(f'<div style="padding: 10px 0;">{step_html}</div>', unsafe_allow_html=True)
        
        # Recent logs
        if logs:
            with st.expander("📋 Recent Logs", expanded=False):
                log_html = ""
                for log in logs[-20:]:
                    log_type = log.get("type", "info")
                    color = {"success": "#4CAF50", "error": "#f44336", "agent": "#667eea"}.get(log_type, "#888")
                    log_html += f'<div style="font-family: monospace; font-size: 0.85em;"><span style="color: #666;">{log.get("time", "")}</span> <span style="color: {color};">{log.get("msg", "")}</span></div>'
                st.markdown(log_html, unsafe_allow_html=True)
        
        # Stop button
        if st.button("⏹️ Stop Analysis", key=f"stop_{job_id}"):
            stop_job(job_id)
            st.success("Stop requested - analysis will halt shortly")
            st.rerun()
        
        # Auto-refresh indicator
        st.caption("🔄 Auto-refreshing... Navigate away and come back to see progress.")
        
    elif status == "completed":
        st.success(f"Decision: **{result or 'N/A'}**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 View in History", key=f"view_{job_id}"):
                st.session_state.page = "history"
                st.rerun()
        with col2:
            if st.button("🗑️ Clear", key=f"clear_{job_id}"):
                (JOBS_DIR / f"{job_id}.json").unlink(missing_ok=True)
                st.rerun()
                
    elif status in ("failed", "stopped"):
        if error:
            st.error(f"Error: {error}")
        if st.button("🗑️ Clear", key=f"clear_{job_id}"):
            (JOBS_DIR / f"{job_id}.json").unlink(missing_ok=True)
            st.rerun()

# ============================================
# CSS STYLES
# ============================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .stApp { background: #0f0f17; }
    
    /* Navbar */
    .navbar {
        background: #1a1a2e;
        padding: 0 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        height: 60px;
        border-bottom: 1px solid #2a2a4a;
        margin: -60px -1rem 24px -1rem;
        position: sticky;
        top: 0;
        z-index: 100;
    }
    
    .navbar-brand {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 20px;
        font-weight: 700;
        color: #fff;
    }
    
    .navbar-brand span { font-size: 24px; }
    
    .navbar-nav {
        display: flex;
        gap: 4px;
    }
    
    .nav-link {
        padding: 8px 16px;
        border-radius: 8px;
        color: #888;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .nav-link:hover { background: #2a2a4a; color: #fff; }
    .nav-link.active { background: #667eea; color: #fff; }
    
    /* Cards */
    .card {
        background: #1a1a2e;
        border: 1px solid #2a2a4a;
        border-radius: 12px;
        padding: 20px;
        margin: 16px 0;
    }
    
    .card-header {
        font-size: 14px;
        font-weight: 600;
        color: #888;
        margin-bottom: 12px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Decision badges */
    .decision-buy {
        background: linear-gradient(135deg, #059669, #10b981);
        color: white;
        padding: 16px 32px;
        border-radius: 12px;
        font-size: 24px;
        font-weight: 700;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: 0 4px 20px rgba(16, 185, 129, 0.3);
    }
    
    .decision-sell {
        background: linear-gradient(135deg, #dc2626, #ef4444);
        color: white;
        padding: 16px 32px;
        border-radius: 12px;
        font-size: 24px;
        font-weight: 700;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: 0 4px 20px rgba(239, 68, 68, 0.3);
    }
    
    .decision-hold {
        background: linear-gradient(135deg, #d97706, #f59e0b);
        color: white;
        padding: 16px 32px;
        border-radius: 12px;
        font-size: 24px;
        font-weight: 700;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: 0 4px 20px rgba(245, 158, 11, 0.3);
    }
    
    /* Progress */
    .progress-container {
        background: #12121f;
        border: 1px solid #2a2a4a;
        border-radius: 12px;
        padding: 20px;
    }
    
    .progress-step {
        display: flex;
        align-items: center;
        padding: 8px 0;
        color: #666;
    }
    
    .progress-step.active { color: #667eea; }
    .progress-step.done { color: #10b981; }
    
    .step-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #333;
        margin-right: 12px;
    }
    
    .progress-step.active .step-dot {
        background: #667eea;
        box-shadow: 0 0 8px #667eea;
    }
    
    .progress-step.done .step-dot { background: #10b981; }
    
    /* Log viewer */
    .log-viewer {
        background: #0a0a14;
        border: 1px solid #1a1a2e;
        border-radius: 8px;
        padding: 12px;
        font-family: 'Monaco', 'Menlo', monospace;
        font-size: 11px;
        max-height: 200px;
        overflow-y: auto;
        color: #00ff88;
    }
    
    .log-line { padding: 2px 0; }
    .log-time { color: #555; margin-right: 8px; }
    .log-agent { color: #8b5cf6; }
    .log-tool { color: #3b82f6; }
    .log-success { color: #10b981; }
    
    /* Sections */
    .section {
        background: #16162a;
        border-left: 3px solid;
        padding: 16px 20px;
        margin: 12px 0;
        border-radius: 0 8px 8px 0;
    }
    
    .section-analysts { border-color: #667eea; }
    .section-research { border-color: #f59e0b; }
    .section-trading { border-color: #10b981; }
    .section-risk { border-color: #ef4444; }
    .section-final { border-color: #8b5cf6; }
    
    .section-title {
        font-size: 13px;
        font-weight: 600;
        color: #888;
        margin-bottom: 8px;
        text-transform: uppercase;
    }
    
    /* History items */
    .history-item {
        background: #1a1a2e;
        border: 1px solid #2a2a4a;
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .history-item:hover {
        border-color: #667eea;
        background: #1e1e36;
    }
    
    .history-ticker {
        font-size: 18px;
        font-weight: 700;
        color: #fff;
    }
    
    .history-meta {
        font-size: 12px;
        color: #666;
    }
    
    .history-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    
    .badge-buy { background: rgba(16,185,129,0.2); color: #10b981; }
    .badge-sell { background: rgba(239,68,68,0.2); color: #ef4444; }
    .badge-hold { background: rgba(245,158,11,0.2); color: #f59e0b; }
    
    /* Input styling */
    .stTextInput > div > div > input {
        background: #1a1a2e !important;
        border: 1px solid #2a2a4a !important;
        border-radius: 8px !important;
        color: #fff !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea !important;
    }
    
    /* Buttons */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea, #764ba2) !important;
        border: none !important;
    }
    
    /* Select slider */
    .stSelectSlider {
        background: transparent;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: #1a1a2e !important;
        border-radius: 8px !important;
    }
    
    /* Labels */
    label {
        color: #888 !important;
        font-size: 13px !important;
    }
    
    /* Analysis controls bar */
    .control-bar {
        display: flex;
        align-items: flex-end;
        gap: 16px;
        background: #1a1a2e;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #2a2a4a;
        margin-bottom: 24px;
    }
    
    .control-item {
        flex: 1;
    }
    
    .control-item-ticker { flex: 0 0 150px; }
    .control-item-date { flex: 0 0 150px; }
    .control-item-depth { flex: 0 0 200px; }
    .control-item-button { flex: 0 0 120px; }
    
    /* Stop button */
    .stop-btn button {
        background: #ef4444 !important;
        border: none !important;
    }
    
    /* Analyst pills */
    .analyst-pills {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
    }
    
    .analyst-pill {
        background: #1a1a2e;
        border: 1px solid #2a2a4a;
        border-radius: 20px;
        padding: 6px 16px;
        font-size: 13px;
        color: #888;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .analyst-pill:hover { border-color: #667eea; }
    .analyst-pill.selected { 
        background: #667eea; 
        border-color: #667eea; 
        color: #fff; 
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# PDF GENERATION
# ============================================
def generate_pdf(data, ticker, date, decision, full=False):
    """Generate PDF report"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=72)
        
        styles = getSampleStyleSheet()
        
        story = []
        
        # Title
        story.append(Paragraph(f"Trading Analysis Report",
                              ParagraphStyle('Title', fontSize=24, alignment=TA_CENTER,
                                           textColor=colors.HexColor('#667eea'), spaceAfter=20)))
        story.append(Paragraph(f"{ticker} | {date}",
                              ParagraphStyle('Subtitle', fontSize=14, alignment=TA_CENTER,
                                           textColor=colors.gray, spaceAfter=30)))
        
        # Decision
        dec_colors = {'BUY': '#10b981', 'SELL': '#ef4444', 'HOLD': '#f59e0b'}
        story.append(Paragraph(f"<b>Recommendation: {decision}</b>",
                              ParagraphStyle('Decision', fontSize=18, alignment=TA_CENTER,
                                           textColor=colors.HexColor(dec_colors.get(decision, '#888')))))
        story.append(Spacer(1, 30))
        
        # Final decision
        if data.get("final_trade_decision"):
            story.append(Paragraph("Final Decision", styles['Heading2']))
            text = str(data["final_trade_decision"])[:2000].replace('\n', '<br/>')
            story.append(Paragraph(text, styles['Normal']))
        
        if full:
            # Add all sections
            sections = [
                ("Market Analysis", "market_report"),
                ("Sentiment Analysis", "sentiment_report"),
                ("News Analysis", "news_report"),
                ("Fundamentals", "fundamentals_report"),
                ("Trading Plan", "trader_investment_plan"),
            ]
            for name, key in sections:
                if data.get(key):
                    story.append(Spacer(1, 20))
                    story.append(Paragraph(name, styles['Heading2']))
                    text = str(data[key])[:1500].replace('\n', '<br/>')
                    story.append(Paragraph(text, styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    except:
        return None

# ============================================
# NAVBAR
# ============================================
def render_navbar():
    st.markdown("""
    <div class="navbar">
        <div class="navbar-brand">
            <span>📈</span>
            TradingAgents
        </div>
        <div class="navbar-nav">
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 4])
    
    with col1:
        if st.button("📊 Analyze", key="nav_analyze", use_container_width=True):
            st.session_state.page = "analyze"
            st.session_state.view_analysis = None
            st.rerun()
    
    with col2:
        if st.button("📜 History", key="nav_history", use_container_width=True):
            st.session_state.page = "history"
            st.rerun()
    
    with col3:
        if st.button("⚙️ Settings", key="nav_settings", use_container_width=True):
            st.session_state.page = "settings"
            st.rerun()
    
    st.markdown("</div></div>", unsafe_allow_html=True)

# ============================================
# ANALYZE PAGE
# ============================================
def render_analyze_page():
    st.markdown("## New Analysis")
    
    # Check if viewing saved analysis
    if st.session_state.view_analysis:
        render_saved_analysis()
        return
    
    # Show running jobs at the top
    running_jobs = get_running_jobs()
    if running_jobs:
        st.markdown("### 🔄 Running Analyses")
        for job in running_jobs:
            render_job_status(job)
        st.markdown("---")
        # Auto-refresh while jobs are running
        import time
        time.sleep(2)
        st.rerun()
    
    # Control bar - all inputs in one row
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 0.8])
    
    with col1:
        ticker = st.text_input("Ticker", value="AAPL", placeholder="AAPL").upper()
    
    with col2:
        default_date = datetime.now() - timedelta(days=1)
        analysis_date = st.date_input("Date", value=default_date, max_value=datetime.now().date())
    
    with col3:
        depth = st.select_slider("Depth", options=[1, 2, 3, 4, 5], value=2)
        st.caption(f"{'Quick' if depth <= 2 else 'Thorough' if depth <= 3 else 'Deep'} • ~{depth * 2}-{depth * 3} min")
    
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("🚀 Analyze", type="primary", use_container_width=True)
    
    with col5:
        st.markdown("<br>", unsafe_allow_html=True)
        settings = load_settings()
        st.caption(f"Model: {settings.get('model', 'GLM 5.1').split('/')[-1]}")
    
    # Analyst selection
    st.markdown("#### Select Analysts")
    analyst_cols = st.columns(4)
    analysts = [
        ("Market", "market", "📊 Technical analysis"),
        ("News", "news", "📰 News & events"),
        ("Social", "social", "💬 Sentiment"),
        ("Fundamentals", "fundamentals", "💰 Financials"),
    ]
    
    selected_analysts = []
    for i, (name, key, desc) in enumerate(analysts):
        with analyst_cols[i]:
            if st.checkbox(f"{name}", value=True, key=f"analyst_{key}"):
                selected_analysts.append(key)
            st.caption(desc)
    
    # Run analysis
    if analyze_btn:
        if not ticker:
            st.error("Enter a ticker symbol")
        elif not selected_analysts:
            st.error("Select at least one analyst")
        else:
            run_analysis(ticker, analysis_date, selected_analysts, depth)

def render_saved_analysis():
    """Display a saved analysis"""
    analysis = st.session_state.view_analysis
    
    st.markdown(f"## {analysis['ticker']} Analysis")
    st.markdown(f"**Date:** {analysis['date']} • **Saved:** {analysis['timestamp'][:19].replace('T', ' ')}")
    
    if st.button("← Back to New Analysis"):
        st.session_state.view_analysis = None
        st.rerun()
    
    # Display decision
    decision = analysis.get('decision', 'HOLD')
    badge_class = {'BUY': 'decision-buy', 'SELL': 'decision-sell', 'HOLD': 'decision-hold'}.get(decision, 'decision-hold')
    st.markdown(f"""
    <div class="{badge_class}">{decision}</div>
    """, unsafe_allow_html=True)
    
    # Display sections
    data = analysis.get('full_data', {})
    
    sections = [
        ("Analysts", "section-analysts", [
            ("Market", "market_report"),
            ("Sentiment", "sentiment_report"),
            ("News", "news_report"),
            ("Fundamentals", "fundamentals_report"),
        ]),
        ("Research", "section-research", [
            ("Trading Plan", "trader_investment_plan"),
        ]),
        ("Final", "section-final", [
            ("Decision", "final_trade_decision"),
        ]),
    ]
    
    for section_name, section_class, items in sections:
        st.markdown(f"<div class='section {section_class}'><div class='section-title'>{section_name}</div>", unsafe_allow_html=True)
        for name, key in items:
            if data.get(key):
                with st.expander(name, expanded=(key == "final_trade_decision")):
                    st.markdown(str(data[key]))
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Export
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        pdf = generate_pdf(data, analysis['ticker'], analysis['date'], decision, full=False)
        if pdf:
            st.download_button("📄 Summary PDF", pdf, f"{analysis['ticker']}_summary.pdf", use_container_width=True)
    
    with col2:
        pdf_full = generate_pdf(data, analysis['ticker'], analysis['date'], decision, full=True)
        if pdf_full:
            st.download_button("📄 Full PDF", pdf_full, f"{analysis['ticker']}_full.pdf", use_container_width=True)
    
    with col3:
        st.download_button("📥 JSON", json.dumps(data, indent=2), f"{analysis['ticker']}_analysis.json", use_container_width=True)

def run_analysis(ticker, analysis_date, selected_analysts, depth):
    """Start a background analysis job"""
    job_id = start_background_job(ticker, analysis_date, selected_analysts, depth)
    st.success(f"✅ Analysis started in background!")
    st.info(f"📋 Job ID: `{job_id}`\n\nNavigate away and come back anytime - your analysis will continue running.")
    st.rerun()

def display_results(final_state, decision, ticker, analysis_date):
    """Display analysis results"""
    # Determine decision
    dec_text = (decision or "").lower()
    if "buy" in dec_text or "long" in dec_text:
        dec_class, dec_label = "decision-buy", "BUY"
    elif "sell" in dec_text or "short" in dec_text:
        dec_class, dec_label = "decision-sell", "SELL"
    else:
        dec_class, dec_label = "decision-hold", "HOLD"
    
    # Decision badge
    st.markdown(f"""
    <div style="text-align: center; margin: 20px 0;">
        <div class="{dec_class}">{dec_label}</div>
        <div style="color: #888; margin-top: 8px;">{ticker} • {analysis_date}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Analysis sections
    sections = [
        ("Analysts", "section-analysts", [
            ("📊 Market", "market_report"),
            ("💬 Sentiment", "sentiment_report"),
            ("📰 News", "news_report"),
            ("💰 Fundamentals", "fundamentals_report"),
        ]),
        ("Research", "section-research", [
            ("📈 Trading Plan", "trader_investment_plan"),
        ]),
        ("Final", "section-final", [
            ("🎯 Decision", "final_trade_decision"),
        ]),
    ]
    
    for section_name, section_class, items in sections:
        st.markdown(f"<div class='section {section_class}'><div class='section-title'>{section_name}</div>", unsafe_allow_html=True)
        for name, key in items:
            if final_state.get(key):
                with st.expander(name, expanded=(key == "final_trade_decision")):
                    st.markdown(str(final_state[key]))
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Export & Save
    st.markdown("---")
    st.markdown("### Export & Save")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        pdf = generate_pdf(final_state, ticker, analysis_date, dec_label, full=False)
        if pdf:
            st.download_button("📄 Summary PDF", pdf, f"{ticker}_{analysis_date}_summary.pdf", use_container_width=True)
    
    with col2:
        pdf_full = generate_pdf(final_state, ticker, analysis_date, dec_label, full=True)
        if pdf_full:
            st.download_button("📄 Full PDF", pdf_full, f"{ticker}_{analysis_date}_full.pdf", use_container_width=True)
    
    with col3:
        st.download_button("📥 JSON", json.dumps(final_state, indent=2, default=str), 
                          f"{ticker}_{analysis_date}.json", use_container_width=True)
    
    with col4:
        if st.button("💾 Save to History", use_container_width=True):
            analyses = load_analyses()
            analyses.insert(0, {
                "ticker": ticker,
                "date": str(analysis_date),
                "decision": dec_label,
                "timestamp": datetime.now().isoformat(),
                "final_decision": str(final_state.get("final_trade_decision", ""))[:500],
                "full_data": {k: str(v) if not isinstance(v, (dict, list)) else v for k, v in final_state.items()}
            })
            save_analyses(analyses[:100])  # Keep last 100
            st.success("Saved!")

# ============================================
# HISTORY PAGE
# ============================================
def render_history_page():
    st.markdown("## Analysis History")
    
    analyses = load_analyses()
    
    if not analyses:
        st.info("No saved analyses. Run an analysis and save it to see it here.")
        return
    
    # Search
    search = st.text_input("🔍 Search ticker", placeholder="Type to filter...")
    
    if search:
        analyses = [a for a in analyses if search.upper() in a.get("ticker", "")]
    
    # Display
    for i, a in enumerate(analyses):
        col1, col2, col3 = st.columns([2, 3, 1])
        
        with col1:
            st.markdown(f"<div class='history-ticker'>{a.get('ticker', 'N/A')}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='history-meta'>{a.get('date', '')}</div>", unsafe_allow_html=True)
        
        with col2:
            dec = a.get('decision', 'HOLD')
            badge = {'BUY': 'badge-buy', 'SELL': 'badge-sell', 'HOLD': 'badge-hold'}.get(dec, 'badge-hold')
            st.markdown(f"<span class='history-badge {badge}'>{dec}</span>", unsafe_allow_html=True)
            st.caption(a.get('timestamp', '')[:19].replace('T', ' '))
        
        with col3:
            if st.button("View", key=f"view_{i}", use_container_width=True):
                st.session_state.view_analysis = a
                st.session_state.page = "analyze"
                st.rerun()
        
        st.markdown("---")

# ============================================
# SETTINGS PAGE
# ============================================
def render_settings_page():
    st.markdown("## Settings")
    
    settings = load_settings()
    
    # Provider selection
    providers = {
        "Z.AI (Nano-GPT)": {
            "url": "https://nano-gpt.com/api/v1",
            "models": [
                ("GLM 5.1 (Recommended)", "zai-org/glm-5.1"),
                ("GLM 5", "zai-org/glm-5"),
                ("GLM 4.5 Air (Free)", "z-ai/glm-4.5-air:free"),
            ]
        },
        "OpenAI": {
            "url": "https://api.openai.com/v1",
            "models": [
                ("GPT-5.4", "gpt-5.4"),
                ("GPT-5.2", "gpt-5.2"),
                ("GPT-5 Mini", "gpt-5-mini"),
            ]
        },
        "Anthropic": {
            "url": "https://api.anthropic.com/v1",
            "models": [
                ("Claude Opus 4.6", "claude-opus-4-6"),
                ("Claude Sonnet 4.6", "claude-sonnet-4-6"),
            ]
        },
        "Google": {
            "url": "https://generativelanguage.googleapis.com/v1",
            "models": [
                ("Gemini 3.1 Pro", "gemini-3.1-pro-preview"),
                ("Gemini 3 Flash", "gemini-3-flash-preview"),
            ]
        },
        "xAI": {
            "url": "https://api.x.ai/v1",
            "models": [
                ("Grok 4", "grok-4-0709"),
                ("Grok 4 Fast", "grok-4-fast-reasoning"),
            ]
        },
        "Custom": {
            "url": "",
            "models": [("Custom Model", "custom")]
        }
    }
    
    col1, col2 = st.columns(2)
    
    with col1:
        provider = st.selectbox("Provider", list(providers.keys()), 
                               index=0 if "Z.AI" in settings.get("provider_name", "") else 0)
        
        model_opts = providers[provider]["models"]
        model_names = [m[0] for m in model_opts]
        model = st.selectbox("Model", model_names)
        model_id = next((m[1] for m in model_opts if m[0] == model), model_opts[0][1])
    
    with col2:
        base_url = st.text_input("API URL", value=providers[provider]["url"] or settings.get("base_url", ""))
        
        # Show masked key
        current_key = settings.get("api_key", "")
        masked = current_key[:8] + "..." + current_key[-4:] if len(current_key) > 12 else current_key
        
        api_key = st.text_input("API Key", value=masked, type="password")
        
        # Keep original if not changed
        if api_key == masked:
            api_key = current_key
    
    if st.button("💾 Save Settings", type="primary"):
        new_settings = {
            "api_key": api_key,
            "base_url": base_url,
            "model": model_id,
            "provider_name": f"{provider} - {model}"
        }
        save_settings(new_settings)
        st.success("Settings saved!")
        st.rerun()
    
    # Current settings
    st.markdown("---")
    st.markdown("### Current Configuration")
    st.json({
        "Provider": settings.get("provider_name", "Not set"),
        "Model": settings.get("model", "Not set"),
        "URL": settings.get("base_url", "Not set"),
    })

# ============================================
# MAIN
# ============================================
def main():
    render_navbar()
    
    if st.session_state.page == "analyze":
        render_analyze_page()
    elif st.session_state.page == "history":
        render_history_page()
    elif st.session_state.page == "settings":
        render_settings_page()

if __name__ == "__main__":
    main()
