#!/usr/bin/env python3
"""
TradingAgents Web UI - Flask Version
Run with: python app.py
"""
import os
import sys
import json
import subprocess
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_file
from io import BytesIO

# Add TradingAgents to path
sys.path.insert(0, str(Path(__file__).parent))

app = Flask(__name__)

# Data storage
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
JOBS_DIR = DATA_DIR / "jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_CONFIG = {
    "api_key": "sk-nano-67fb7b23-5505-491b-ac1f-c08f45ed30e0",
    "base_url": "https://nano-gpt.com/api/v1",
    "model": "zai-org/glm-5.1",
    "provider_name": "Z.AI GLM 5.1"
}

# ============================================
# SETTINGS
# ============================================
def get_settings_file():
    return DATA_DIR / "settings.json"

def load_settings():
    f = get_settings_file()
    if f.exists():
        try:
            return json.loads(f.read_text())
        except:
            pass
    return DEFAULT_CONFIG.copy()

def save_settings(settings):
    get_settings_file().write_text(json.dumps(settings, indent=2))

# ============================================
# ANALYSES
# ============================================
def get_analyses_file():
    return DATA_DIR / "analyses.json"

def load_analyses():
    f = get_analyses_file()
    if f.exists():
        try:
            return json.loads(f.read_text())
        except:
            pass
    return []

def save_analyses(analyses):
    get_analyses_file().write_text(json.dumps(analyses, indent=2, default=str))

# ============================================
# JOBS
# ============================================
def get_running_jobs():
    """Get list of running jobs"""
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
    job_id = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    settings = load_settings()
    
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

def clear_job(job_id: str):
    """Remove a job file"""
    (JOBS_DIR / f"{job_id}.json").unlink(missing_ok=True)

# ============================================
# ROUTES
# ============================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/settings', methods=['GET'])
def get_settings():
    return jsonify(load_settings())

@app.route('/api/settings', methods=['POST'])
def update_settings():
    settings = request.json
    save_settings(settings)
    return jsonify({"status": "ok"})

@app.route('/api/jobs/running')
def api_running_jobs():
    return jsonify(get_running_jobs())

@app.route('/api/jobs/<job_id>')
def api_get_job(job_id):
    job = get_job(job_id)
    if job:
        return jsonify(job)
    return jsonify({"error": "Job not found"}), 404

@app.route('/api/jobs/start', methods=['POST'])
def api_start_job():
    data = request.json
    ticker = data.get('ticker', '').upper()
    date = data.get('date', '')
    analysts = data.get('analysts', ['market', 'news', 'social', 'fundamentals'])
    depth = data.get('depth', 2)
    
    if not ticker:
        return jsonify({"error": "Ticker required"}), 400
    
    job_id = start_background_job(ticker, date, analysts, depth)
    return jsonify({"job_id": job_id, "status": "started"})

@app.route('/api/jobs/<job_id>/stop', methods=['POST'])
def api_stop_job(job_id):
    stop_job(job_id)
    return jsonify({"status": "stopping"})

@app.route('/api/jobs/<job_id>/clear', methods=['POST'])
def api_clear_job(job_id):
    clear_job(job_id)
    return jsonify({"status": "cleared"})

@app.route('/api/analyses')
def api_analyses():
    return jsonify(load_analyses())

@app.route('/api/analyses/<int:index>', methods=['DELETE'])
def api_delete_analysis(index):
    analyses = load_analyses()
    if 0 <= index < len(analyses):
        analyses.pop(index)
        save_analyses(analyses)
        return jsonify({"status": "deleted"})
    return jsonify({"error": "Not found"}), 404

@app.route('/api/analyses/<int:index>/pdf')
def api_download_pdf(index):
    """Generate and download PDF report for an analysis"""
    analyses = load_analyses()
    if not (0 <= index < len(analyses)):
        return jsonify({"error": "Not found"}), 404
    
    analysis = analyses[index]
    
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    except ImportError:
        return jsonify({"error": "reportlab not installed"}), 500
    
    # Create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, 
                           leftMargin=0.75*inch, rightMargin=0.75*inch,
                           topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=HexColor('#1a1a2e')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=16,
        spaceAfter=8,
        textColor=HexColor('#667eea'),
        borderWidth=1,
        borderColor=HexColor('#667eea'),
        borderPadding=5
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubheading',
        parent=styles['Heading3'],
        fontSize=12,
        spaceBefore=12,
        spaceAfter=6,
        textColor=HexColor('#333333')
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=8,
        alignment=TA_JUSTIFY
    )
    
    meta_style = ParagraphStyle(
        'Meta',
        parent=styles['Normal'],
        fontSize=10,
        textColor=HexColor('#666666'),
        alignment=TA_CENTER
    )
    
    # Build content
    story = []
    
    # Header
    story.append(Paragraph("📊 AI Market Analyst Report", title_style))
    story.append(Spacer(1, 10))
    
    # Metadata
    ticker = analysis.get('ticker', 'N/A')
    date = analysis.get('date', 'N/A')
    timestamp = analysis.get('timestamp', '')
    if timestamp:
        timestamp = timestamp[:19].replace('T', ' ')
    
    story.append(Paragraph(f"<b>Symbol:</b> {ticker} | <b>Analysis Date:</b> {date} | <b>Generated:</b> {timestamp}", meta_style))
    story.append(Spacer(1, 20))
    
    # Decision Box
    decision = analysis.get('decision', 'HOLD')
    decision_color = '#4CAF50' if 'BUY' in decision else ('#f44336' if 'SELL' in decision else '#FF9800')
    
    decision_style = ParagraphStyle(
        'Decision',
        parent=styles['Heading1'],
        fontSize=20,
        alignment=TA_CENTER,
        textColor=HexColor(decision_color),
        spaceBefore=10,
        spaceAfter=20
    )
    story.append(Paragraph(f"RECOMMENDATION: {decision}", decision_style))
    story.append(Spacer(1, 20))
    
    # Analysis Configuration
    depth = analysis.get('depth', 2)
    depth_labels = ['', 'Quick', 'Standard', 'Thorough', 'Deep', 'Comprehensive']
    analysts = analysis.get('analysts', [])
    
    config_data = [
        ['Research Depth', f"Level {depth} - {depth_labels[depth] if depth < len(depth_labels) else 'Standard'}"],
        ['Analysts Used', ', '.join(a.title() for a in analysts) if analysts else 'All'],
    ]
    
    config_table = Table(config_data, colWidths=[2*inch, 4.5*inch])
    config_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), HexColor('#f5f5f5')),
        ('TEXTCOLOR', (0, 0), (0, -1), HexColor('#666666')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
    ]))
    
    story.append(Paragraph("Analysis Configuration", heading_style))
    story.append(config_table)
    story.append(Spacer(1, 20))
    
    # Analysis Reports
    data = analysis.get('full_data', {})
    
    # Section mapping
    sections = [
        ("Market Analysis", [
            ("Market Report", "market_report"),
        ]),
        ("Sentiment & News Analysis", [
            ("Sentiment Report", "sentiment_report"),
            ("News Report", "news_report"),
        ]),
        ("Fundamental Analysis", [
            ("Fundamentals Report", "fundamentals_report"),
        ]),
        ("Trading Strategy", [
            ("Trading Plan", "trader_investment_plan"),
        ]),
        ("Final Decision", [
            ("Decision Details", "final_trade_decision"),
        ]),
    ]
    
    for section_title, items in sections:
        section_content = []
        for item_title, key in items:
            content = data.get(key, '')
            if content and content.strip():
                section_content.append((item_title, content))
        
        if section_content:
            story.append(Paragraph(section_title, heading_style))
            for item_title, content in section_content:
                story.append(Paragraph(item_title, subheading_style))
                # Clean up content for PDF
                content = str(content).replace('<', '&lt;').replace('>', '&gt;')
                # Split into paragraphs
                for para in content.split('\n\n'):
                    if para.strip():
                        story.append(Paragraph(para.strip(), body_style))
            story.append(Spacer(1, 10))
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph("_" * 80, meta_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Powered by TradingAgents | AI-Powered Financial Analysis", meta_style))
    story.append(Paragraph("<i>Disclaimer: This report is for informational purposes only and does not constitute financial advice.</i>", meta_style))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    # Generate filename
    filename = f"{ticker}_{date}_analysis_report.pdf"
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )

if __name__ == '__main__':
    print("Starting TradingAgents UI on http://0.0.0.0:8502")
    app.run(host='0.0.0.0', port=8502, debug=False)
