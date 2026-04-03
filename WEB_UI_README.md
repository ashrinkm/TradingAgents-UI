# TradingAgents Web UI - Detailed Documentation

Comprehensive guide for the TradingAgents Flask Web UI.

## Table of Contents

- [Architecture](#architecture)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [API Reference](#api-reference)
- [Advanced Usage](#advanced-usage)
- [Performance Tuning](#performance-tuning)

## Architecture

### Components

```
app.py                    # Flask web application (main entry point)
background_worker.py      # Background analysis processor
templates/
  └── index.html         # Main UI template (51KB single-file app)
data/
  ├── settings.json       # User configuration
  ├── analyses.json       # Analysis history
  └── jobs/               # Background job tracking
```

### Data Flow

1. **User Request** → Flask route handler
2. **Background Process** → Spawn worker for analysis
3. **Progress Updates** → Worker writes to job status file
4. **UI Polling** → Frontend fetches job status via AJAX
5. **Completion** → Results saved to analyses.json
6. **Display** → User views results in History page

### Job System

Background jobs are tracked via JSON files in `data/jobs/`:

```json
{
  "job_id": "AAPL_20260402_193045_abc123",
  "ticker": "AAPL",
  "status": "running",
  "progress": {
    "market": "done",
    "analysts": "active",
    "research": "pending"
  },
  "logs": ["Starting analysis...", "Fetching market data..."],
  "started_at": "2026-04-02T19:30:45",
  "stop_requested": false
}
```

## Configuration

### Settings Structure

```json
{
  "api_key": "sk-...",
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-5",
  "provider_name": "OpenAI"
}
```

### Environment Variables

Optional `.env` file:

```bash
# LLM Provider Keys
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
ANTHROPIC_API_KEY=...
XAI_API_KEY=...

# Custom endpoint
OPENAI_BASE_URL=https://api.openai.com/v1
```

### Multiple Providers

Switch between providers in Settings:

| Provider | Base URL | Models |
|----------|----------|--------|
| OpenAI | `https://api.openai.com/v1` | gpt-5, gpt-5-mini, gpt-5.2 |
| Google | `https://generativelanguage.googleapis.com/v1` | gemini-3.0-flash, gemini-3.1-pro |
| Anthropic | `https://api.anthropic.com/v1` | claude-4-sonnet, claude-4.6-opus |
| X.AI | `https://api.x.ai/v1` | grok-4, grok-4-heavy |
| Z.AI | `https://nano-gpt.com/api/v1` | zai-org/glm-5, zai-org/glm-5.1 |

## Deployment

### Production Flask Server

Use Gunicorn for production:

```bash
pip install gunicorn

# 4 worker processes
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# With timeout for long analyses
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 600 app:app
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name tradingagents.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 600s;
    }
}
```

### Docker Production

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir flask gunicorn

# Copy application
COPY . .

# Create data directories
RUN mkdir -p data/jobs

# Expose port
EXPOSE 5000

# Run with Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "600", "app:app"]
```

### Heroku Deployment

```bash
# Create app
heroku create tradingagents-ui

# Set environment
heroku config:set OPENAI_API_KEY=sk-...

# Deploy
git push heroku main

# Scale
heroku ps:scale web=1
```

**Procfile:**
```
web: gunicorn app:app --timeout 600
```

### AWS EC2 Deployment

1. **Launch EC2 instance** (Ubuntu 20.04+)
2. **Install dependencies:**
```bash
sudo apt update
sudo apt install python3-pip nginx
pip3 install -r requirements.txt
pip3 install flask gunicorn
```
3. **Clone and configure:**
```bash
git clone https://github.com/ashrinkm/TradingAgents-UI.git
cd TradingAgents-UI
```
4. **Create systemd service:**
```bash
sudo nano /etc/systemd/system/tradingagents.service
```
```ini
[Unit]
Description=TradingAgents UI
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/TradingAgents-UI
Environment="OPENAI_API_KEY=sk-..."
ExecStart=/usr/bin/python3 -m gunicorn -w 4 -b 127.0.0.1:5000 --timeout 600 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```
5. **Enable and start:**
```bash
sudo systemctl enable tradingagents
sudo systemctl start tradingagents
```
6. **Configure Nginx** (see above)

## API Reference

### REST Endpoints

#### `GET /`
Main UI page

#### `GET /api/settings`
Get current settings

**Response:**
```json
{
  "api_key": "sk-...",
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-5",
  "provider_name": "OpenAI"
}
```

#### `POST /api/settings`
Update settings

**Request:**
```json
{
  "api_key": "sk-...",
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-5",
  "provider_name": "OpenAI"
}
```

#### `POST /api/analyze`
Start new analysis

**Request:**
```json
{
  "ticker": "AAPL",
  "date": "2026-04-02",
  "analysts": ["fundamentals", "sentiment", "news", "technical"],
  "depth": 3
}
```

**Response:**
```json
{
  "job_id": "AAPL_20260402_193045_abc123",
  "status": "pending"
}
```

#### `GET /api/jobs`
Get running jobs

**Response:**
```json
[
  {
    "job_id": "AAPL_20260402_193045_abc123",
    "ticker": "AAPL",
    "status": "running",
    "progress": {...}
  }
]
```

#### `GET /api/job/<job_id>`
Get specific job status

#### `POST /api/job/<job_id>/stop`
Stop running job

#### `GET /api/analyses`
Get analysis history

**Response:**
```json
[
  {
    "id": "job_123",
    "ticker": "AAPL",
    "date": "2026-04-02",
    "status": "completed",
    "decision": "BUY",
    "completed_at": "2026-04-02T19:35:22"
  }
]
```

#### `GET /api/analysis/<analysis_id>`
Get specific analysis details

## Advanced Usage

### Batch Analysis

Run multiple analyses via script:

```python
import requests
import time

tickers = ["AAPL", "GOOGL", "MSFT", "AMZN", "NVDA"]
base_url = "http://localhost:5000"

for ticker in tickers:
    response = requests.post(f"{base_url}/api/analyze", json={
        "ticker": ticker,
        "date": "2026-04-02",
        "analysts": ["fundamentals", "sentiment", "news", "technical"],
        "depth": 3
    })
    print(f"Started {ticker}: {response.json()['job_id']}")
    time.sleep(2)  # Rate limiting
```

### Custom Analysis Pipeline

Modify `background_worker.py` to customize:

```python
# Skip certain analysts
selected_analysts = ["fundamentals", "technical"]  # Skip sentiment/news

# Adjust debate rounds
config["max_debate_rounds"] = 3  # More thorough research

# Custom data vendors
config["data_vendors"] = {
    "market": "alpha_vantage",  # Instead of yfinance
    "news": "newsapi"
}
```

### Export Analysis Results

```python
import json
from pathlib import Path

# Load analyses
analyses = json.loads(Path("data/analyses.json").read_text())

# Export to CSV
import csv
with open("analyses_export.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["ticker", "date", "decision", "confidence"])
    writer.writeheader()
    for analysis in analyses:
        writer.writerow({
            "ticker": analysis["ticker"],
            "date": analysis["date"],
            "decision": analysis["result"]["decision"],
            "confidence": analysis["result"]["confidence"]
        })
```

## Performance Tuning

### Database Optimization

For large-scale usage, replace JSON files with SQLite:

```python
import sqlite3

conn = sqlite3.connect('data/tradingagents.db')
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS analyses (
        id TEXT PRIMARY KEY,
        ticker TEXT,
        date TEXT,
        status TEXT,
        result TEXT,
        created_at TIMESTAMP
    )
''')

c.execute('CREATE INDEX idx_ticker ON analyses(ticker)')
c.execute('CREATE INDEX idx_date ON analyses(date)')
```

### Caching

Cache market data to reduce API calls:

```python
from functools import lru_cache
import pickle

@lru_cache(maxsize=128)
def get_market_data_cached(ticker, date):
    # Cache key is (ticker, date) tuple
    return get_market_data(ticker, date)
```

### Rate Limiting

Implement rate limiting for API calls:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route("/api/analyze", methods=["POST"])
@limiter.limit("10 per hour")
def analyze():
    # Analysis logic
    pass
```

### Background Worker Scaling

Run multiple worker processes:

```python
# In background_worker.py
import multiprocessing

def run_analysis_parallel(tickers):
    with multiprocessing.Pool(processes=4) as pool:
        pool.map(run_single_analysis, tickers)
```

## Monitoring

### Logging

Add structured logging:

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module
        }
        return json.dumps(log_obj)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
app.logger.addHandler(handler)
```

### Health Checks

Add health endpoint:

```python
@app.route("/health")
def health():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "jobs_running": len(get_running_jobs()),
        "analyses_count": len(load_analyses())
    }
```

### Prometheus Metrics

```python
from prometheus_flask_exporter import PrometheusMetrics

metrics = PrometheusMetrics(app)

# Custom metrics
analysis_counter = metrics.counter(
    'analysis_total', 
    'Total analyses run',
    labels={'ticker': lambda: request.json.get('ticker')}
)
```

## Security

### API Key Protection

Never expose API keys in frontend:

```python
# Bad
return jsonify({"api_key": settings["api_key"]})

# Good
return jsonify({"api_key": "*****" + settings["api_key"][-4:]})
```

### Input Validation

```python
from flask import request
import re

@app.route("/api/analyze", methods=["POST"])
def analyze():
    ticker = request.json.get("ticker", "").upper()
    
    # Validate ticker format
    if not re.match(r'^[A-Z]{1,5}$', ticker):
        return {"error": "Invalid ticker format"}, 400
    
    # Continue with analysis
```

### CORS Configuration

```python
from flask_cors import CORS

# Restrict to specific origins
CORS(app, origins=["https://yourdomain.com"])
```

## Troubleshooting

### Memory Issues

For long-running analyses:

```python
# In background_worker.py
import gc

# Force garbage collection after each analyst
gc.collect()
```

### Process Cleanup

Ensure background processes are cleaned up:

```python
import atexit
import os

def cleanup():
    # Kill all child processes
    import psutil
    parent = psutil.Process(os.getpid())
    for child in parent.children(recursive=True):
        child.kill()

atexit.register(cleanup)
```

---

For more help, check the [main README](./README.md) or [open an issue](https://github.com/ashrinkm/TradingAgents-UI/issues).
