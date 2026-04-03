#!/usr/bin/env python3
"""
Background worker for TradingAgents analysis.
Runs independently and writes progress to a job file.
"""
import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

# Add TradingAgents to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

DATA_DIR = Path(__file__).parent / "data"
JOBS_DIR = DATA_DIR / "jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)


def run_job(job_id: str, ticker: str, analysis_date: str, analysts: list, depth: int, config_dict: dict):
    """Run analysis and update job file with progress"""
    job_file = JOBS_DIR / f"{job_id}.json"
    
    def update_job(**updates):
        """Update job status file"""
        job_file.write_text(json.dumps(updates, indent=2, default=str))
    
    # Initialize job
    update_job(
        job_id=job_id,
        ticker=ticker,
        date=analysis_date,
        analysts=analysts,
        depth=depth,
        status="running",
        started_at=datetime.now().isoformat(),
        progress={},
        logs=[],
        result=None,
        error=None,
        config=config_dict
    )
    
    def add_log(msg: str, log_type: str = "info"):
        """Add a log entry"""
        try:
            job = json.loads(job_file.read_text())
            logs = job.get("logs", [])
            logs.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "type": log_type,
                "msg": msg
            })
            if len(logs) > 100:
                logs = logs[-100:]
            update_job(**{**job, "logs": logs})
        except:
            pass
    
    def update_progress(**kwargs):
        """Update progress state"""
        try:
            job = json.loads(job_file.read_text())
            progress = job.get("progress", {})
            progress.update(kwargs)
            update_job(**{**job, "progress": progress})
        except:
            pass
    
    try:
        # Set environment
        os.environ['OPENAI_API_KEY'] = config_dict.get("api_key", "")
        os.environ['OPENAI_BASE_URL'] = config_dict.get("base_url", "")
        
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        
        config = {
            "project_dir": "/root/.openclaw/workspace/TradingAgents/tradingagents",
            "results_dir": "/root/.openclaw/workspace/TradingAgents/results",
            "data_cache_dir": "/root/.openclaw/workspace/TradingAgents/tradingagents/dataflows/data_cache",
            "llm_provider": "openai",
            "deep_think_llm": config_dict.get("model", "zai-org/glm-5.1"),
            "quick_think_llm": config_dict.get("model", "zai-org/glm-5.1"),
            "backend_url": config_dict.get("base_url", ""),
            "max_debate_rounds": depth,
            "max_risk_discuss_rounds": depth,
        }
        
        add_log("Initializing analysis...", "info")
        update_progress(init="done", market="active")
        
        ta = TradingAgentsGraph(selected_analysts=analysts, debug=True, config=config)
        init_state = ta.propagator.create_initial_state(ticker, str(analysis_date))
        args = ta.propagator.get_graph_args()
        
        add_log(f"Starting analysis for {ticker}", "success")
        
        final_state = None
        for chunk in ta.graph.stream(init_state, **args):
            # Check for stop signal
            try:
                job = json.loads(job_file.read_text())
                if job.get("stop_requested"):
                    add_log("Analysis stopped by user", "error")
                    update_job(**{**job, "status": "stopped", "stopped_at": datetime.now().isoformat()})
                    return
            except:
                pass
            
            # Update progress based on chunk content
            if chunk.get("market_report"):
                update_progress(market="done", analysts="active")
                add_log("Market analysis complete", "success")
            
            if any(chunk.get(k) for k in ["sentiment_report", "news_report", "fundamentals_report"]):
                add_log("Analyst reports generated", "success")
            
            if chunk.get("investment_debate_state"):
                update_progress(analysts="done", research="active")
                add_log("Research team debating", "agent")
            
            if chunk.get("trader_investment_plan"):
                update_progress(research="done", trading="active")
                add_log("Trading plan created", "success")
            
            if chunk.get("risk_debate_state"):
                update_progress(trading="done", risk="active")
                add_log("Risk assessment in progress", "agent")
            
            if chunk.get("final_trade_decision"):
                update_progress(risk="done", final="done")
                add_log("Final decision reached", "success")
            
            # Log messages
            if chunk.get("messages"):
                last = chunk["messages"][-1]
                content = str(getattr(last, "content", ""))[:80]
                if content:
                    add_log(content, "agent")
            
            final_state = chunk
        
        if final_state:
            decision = ta.process_signal(final_state.get("final_trade_decision", ""))
            
            # Save to analyses history
            analyses_file = DATA_DIR / "analyses.json"
            analyses = []
            if analyses_file.exists():
                try:
                    analyses = json.loads(analyses_file.read_text())
                except:
                    analyses = []
            
            analysis_record = {
                "ticker": ticker,
                "date": str(analysis_date),
                "decision": decision,
                "timestamp": datetime.now().isoformat(),
                "analysts": analysts,
                "depth": depth,
                "full_data": {k: v for k, v in final_state.items() if v}
            }
            analyses.insert(0, analysis_record)
            if len(analyses) > 50:
                analyses = analyses[:50]
            analyses_file.write_text(json.dumps(analyses, indent=2, default=str))
            
            # Update job as complete
            add_log("Analysis complete!", "success")
            update_job(
                status="completed",
                completed_at=datetime.now().isoformat(),
                result=decision,
                final_state={k: str(v)[:1000] for k, v in final_state.items() if v}
            )
        else:
            add_log("No final state returned", "error")
            update_job(status="failed", error="No final state returned")
            
    except Exception as e:
        import traceback
        error_msg = str(e)
        add_log(f"Error: {error_msg}", "error")
        try:
            job = json.loads(job_file.read_text())
            update_job(**{**job, "status": "failed", "error": error_msg, "traceback": traceback.format_exc()})
        except:
            pass


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--analysts", required=True, help="Comma-separated analysts")
    parser.add_argument("--depth", type=int, default=1)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    
    args = parser.parse_args()
    
    config = {
        "api_key": args.api_key,
        "base_url": args.base_url,
        "model": args.model
    }
    
    run_job(
        job_id=args.job_id,
        ticker=args.ticker,
        analysis_date=args.date,
        analysts=args.analysts.split(","),
        depth=args.depth,
        config_dict=config
    )
