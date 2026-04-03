#!/bin/bash
cd /root/.openclaw/workspace/TradingAgents
while true; do
    /root/.openclaw/workspace/TradingAgents/venv/bin/python app.py
    echo "Flask crashed, restarting in 5 seconds..."
    sleep 5
done
