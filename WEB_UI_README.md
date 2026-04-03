# TradingAgents Web UI

A modern, user-friendly web interface for the TradingAgents multi-agent trading framework. This UI provides an intuitive way to run trading analyses, monitor progress in real-time, and review historical results.

## Features

### 🎯 **Real-Time Analysis Monitoring**
- Watch your trading analysis progress step-by-step
- Live log streaming with status updates
- Visual progress indicators for each analyst and research phase

### 📊 **Interactive Dashboard**
- Clean, modern dark-themed interface
- Easy ticker symbol input and date selection
- Customizable analyst selection (Fundamentals, Sentiment, News, Technical)
- Adjustable analysis depth (1-5 levels)

### 📈 **Historical Analysis Review**
- Browse and search past analyses
- Filter by ticker symbol, date, or status
- View detailed analyst reports and final decisions
- Export analysis results

### ⚙️ **Settings Management**
- Configure API keys and endpoints
- Select from multiple LLM providers (GPT-5.x, Gemini 3.x, Claude 4.x, Grok 4.x)
- Customize model parameters
- Persistent configuration storage

### 🔄 **Background Job Processing**
- Long-running analyses execute in the background
- Continue working while analyses run
- Automatic job status tracking
- Ability to stop running analyses

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Virtual environment (recommended)

### Option 1: Streamlit UI (Recommended)

The Streamlit version provides a modern, responsive interface with real-time updates.

```bash
# Navigate to the TradingAgents directory
cd TradingAgents

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install streamlit

# Run the Streamlit UI
./run_web.sh
# Or manually:
# streamlit run web_ui.py --server.port 8501 --server.address 0.0.0.0
```

The UI will be available at `http://localhost:8501`

### Option 2: Flask UI

The Flask version provides a lightweight alternative with a traditional web interface.

```bash
# Navigate to the TradingAgents directory
cd TradingAgents

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install flask

# Run the Flask UI
./run_flask.sh
# Or manually:
# python app.py
```

The UI will be available at `http://localhost:5000`

## Configuration

### First-Time Setup

1. **Open the Settings Page**: Click the "Settings" button in the navigation
2. **Enter Your API Key**: Add your LLM provider API key
3. **Select Provider**: Choose your preferred LLM provider and model
4. **Save Settings**: Click "Save" to persist your configuration

### Supported LLM Providers

- **Z.AI GLM 5.1** (Default)
- **OpenAI GPT-5.x** series
- **Google Gemini 3.x** series
- **Anthropic Claude 4.x** series
- **X.AI Grok 4.x** series

### API Configuration

The Web UI supports multiple API endpoints:

```json
{
  "api_key": "your-api-key-here",
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-5",
  "provider_name": "OpenAI GPT-5"
}
```

## Usage

### Running an Analysis

1. **Select Ticker**: Enter a stock ticker symbol (e.g., AAPL, GOOGL, TSLA)
2. **Choose Date**: Select the analysis date (defaults to today)
3. **Select Analysts**: Choose which analysts to include:
   - Fundamentals Analyst
   - Sentiment Analyst
   - News Analyst
   - Technical Analyst
4. **Set Depth**: Choose analysis depth (1-5, where 5 is most comprehensive)
5. **Start Analysis**: Click "Start Analysis" to begin

### Monitoring Progress

The analysis progresses through these stages:

1. **Market Data** - Fetching current market information
2. **Analysts** - Running individual analyst reports
3. **Research** - Bullish and bearish research debates
4. **Trading Plan** - Developing trading strategy
5. **Risk Assessment** - Evaluating portfolio risks
6. **Final Decision** - Portfolio manager's final recommendation

Each stage shows:
- ✅ Completed steps
- 🔵 Currently running step
- ⭕ Pending steps

### Viewing Results

After completion:
1. Navigate to the "History" page
2. Browse past analyses by ticker or date
3. Click on any analysis to view:
   - Executive summary
   - Individual analyst reports
   - Research team debates
   - Trading decision and reasoning
   - Risk assessment

### Background Jobs

- Analyses run in background processes
- Continue using the UI while analyses execute
- Check job status in real-time
- Stop long-running analyses if needed
- Automatic job tracking and recovery

## Architecture

### Components

```
web_ui.py                 # Streamlit UI (main interface)
app.py                    # Flask UI (alternative interface)
background_worker.py      # Background analysis processor
templates/                # HTML templates for Flask UI
  └── index.html
data/                     # Persistent data storage
  ├── settings.json       # User configuration
  ├── analyses.json       # Analysis history
  └── jobs/               # Background job tracking
```

### Data Flow

1. User submits analysis request via UI
2. Background worker process spawned
3. Worker invokes TradingAgents framework
4. Progress updates written to job status file
5. UI polls for updates and displays progress
6. Final results saved to analyses history

## Deployment

### Local Development

```bash
# Streamlit (recommended for development)
streamlit run web_ui.py

# Flask (alternative)
python app.py
```

### Production Deployment

#### Streamlit Cloud

1. Push your code to GitHub
2. Connect to [Streamlit Cloud](https://streamlit.io/cloud)
3. Deploy with one click

#### Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install streamlit

COPY . .

EXPOSE 8501
CMD ["streamlit", "run", "web_ui.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
```

Build and run:
```bash
docker build -t tradingagents-ui .
docker run -p 8501:8501 tradingagents-ui
```

#### Flask with Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Troubleshooting

### Common Issues

**UI won't start:**
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- For Streamlit: `pip install streamlit`
- For Flask: `pip install flask`

**Analysis fails to start:**
- Check API key is configured in Settings
- Verify base_url is correct for your provider
- Ensure you have API credits/quota

**Background jobs not running:**
- Check `data/jobs/` directory exists and is writable
- Verify background_worker.py has execute permissions
- Check logs for error messages

**Can't see past analyses:**
- Verify `data/analyses.json` exists
- Check file permissions
- Ensure analyses completed successfully

### Logs

Check logs for debugging:
- Streamlit logs: Terminal output
- Flask logs: Terminal output  
- Job logs: `data/jobs/<job_id>.json`

## Tips & Best Practices

### Performance

- Use depth 3 for quick analyses (2-3 minutes)
- Use depth 5 for comprehensive analysis (5-10 minutes)
- Run multiple analyses in parallel for portfolio review
- Stop unused analyses to free resources

### Accuracy

- Select all analysts for most balanced view
- Use higher depth for complex decisions
- Review historical analyses for patterns
- Compare multiple tickers before trading

### Cost Management

- Start with depth 1-2 for initial screening
- Increase depth only for promising opportunities
- Monitor API usage in your provider dashboard
- Consider rate limiting for bulk analyses

## Contributing

Contributions to the Web UI are welcome! Areas for improvement:

- Additional chart visualizations
- Export formats (PDF, Excel, etc.)
- Portfolio tracking features
- Alert systems for price movements
- Backtesting integration
- Multi-language support

## License

This Web UI is part of the TradingAgents project and is licensed under the MIT License.

## Support

- **Documentation**: [TradingAgents Docs](https://github.com/TauricResearch/TradingAgents)
- **Issues**: [GitHub Issues](https://github.com/TauricResearch/TradingAgents/issues)
- **Community**: [Discord](https://discord.com/invite/hk9PGKShPK)
- **Research**: [Tauric Research](https://tauric.ai/)

---

**Note**: This UI is for research purposes. Trading performance may vary based on many factors. It is not intended as financial, investment, or trading advice. Always do your own research before making trading decisions.
