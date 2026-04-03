#!/usr/bin/env python3
"""Simple test to verify TradingAgents works with nano-gpt"""
import os

# Set API config BEFORE importing TradingAgents
os.environ['OPENAI_API_KEY'] = 'sk-nano-67fb7b23-5505-491b-ac1f-c08f45ed30e0'
os.environ['OPENAI_BASE_URL'] = 'https://nano-gpt.com/api/v1'

from tradingagents.graph.trading_graph import TradingAgentsGraph

config = {
    "project_dir": "/root/.openclaw/workspace/TradingAgents/tradingagents",
    "results_dir": "/root/.openclaw/workspace/TradingAgents/results",
    "data_cache_dir": "/root/.openclaw/workspace/TradingAgents/tradingagents/dataflows/data_cache",
    "llm_provider": "openai",
    "deep_think_llm": "zai-org/glm-5",
    "quick_think_llm": "zai-org/glm-5",
    "backend_url": "https://nano-gpt.com/api/v1",
    "google_thinking_level": None,
    "openai_reasoning_effort": None,
    "anthropic_effort": None,
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    "data_vendors": {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "yfinance",
    },
    "tool_vendors": {},
}

print("Initializing TradingAgents...")
ta = TradingAgentsGraph(debug=True, config=config)
print("SUCCESS! TradingAgents is ready.")

# Quick test
print("\nRunning quick analysis on AAPL...")
ticker = "AAPL"
date = "2024-01-15"
result = ta.propagate(ticker, date)
print(f"\nResult for {ticker}:")
if result and len(result) > 1:
    print(result[1][:1000])
else:
    print("No result")
