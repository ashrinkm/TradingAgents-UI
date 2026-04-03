#!/bin/bash
cd /root/.openclaw/workspace/TradingAgents
source venv/bin/activate
streamlit run web_ui.py --server.port 8501 --server.address 0.0.0.0