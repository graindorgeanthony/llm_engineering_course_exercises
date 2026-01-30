# 🚀 Quick Start Guide

Get up and running with the Agentic AI Framework in 5 minutes!

## Prerequisites

- Python 3.9 or higher
- OpenRouter API key ([Get one here](https://openrouter.ai/))

## Installation (Easy Way)

### macOS/Linux:

```bash
cd llm_engineering_course_exercises/week8
chmod +x setup.sh
./setup.sh
```

### Windows:

```bash
cd llm_engineering_course_exercises\week8
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## Configuration

Edit `.env` file and add your OpenRouter API key:

```bash
OPENROUTER_API_KEY=your_key_here
```

**Optional but Recommended**: 
- Pushover credentials for push notifications
- Hugging Face token for Modal deployment (see next step)

## Deploy to Modal (Recommended)

For real price estimates using the fine-tuned model:

```bash
./deploy_modal.sh
```

This will:
1. Setup Modal authentication
2. Add your Hugging Face token
3. Deploy the pricer service to Modal

See [MODAL_DEPLOYMENT.md](MODAL_DEPLOYMENT.md) for detailed instructions.

**Skip this?** The framework will work without Modal but use a mock pricer instead.

## Run the App

### Option 1: Gradio UI (Recommended)

```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
python gradio_app.py
```

Your browser will open automatically with the interactive dashboard!

### Option 2: Command Line

```bash
python example_usage.py
```

This runs through several examples showing different features.

### Option 3: Python Script

```python
from agent_framework import AgentFramework

# Initialize
framework = AgentFramework()

# Load sample data
framework.load_sample_data(100)

# Run the framework
opportunities = framework.run()

# View results
for opp in opportunities:
    print(f"Deal: {opp.deal.product_description[:50]}...")
    print(f"Discount: ${opp.discount:.2f}\n")
```

## What Happens When You Run?

1. **Scanner Agent** fetches deals from RSS feeds
2. **RAG Pricer** searches vector store for similar products
3. **HF Pricer** uses Hugging Face model to estimate prices (if Modal deployed)
4. **Ensemble Pricer** combines estimates with weighted average
5. **Planning Agent** coordinates the workflow using LangGraph
6. **Messaging Agent** sends notifications for great deals (if configured)

## Features to Try

### 1. Load Sample Data
Click "📊 Load Sample Data" in the UI to populate the vector store with 200 sample products.

### 2. Run Agent Framework
Click "🚀 Run Agent Framework" to scan for deals, price them, and find opportunities.

### 3. View Logs
Watch the real-time color-coded logs showing what each agent is doing.

### 4. Explore Visualization
See the 3D t-SNE visualization of product embeddings in the vector store.

### 5. Click on Deals
Click any row in the opportunities table to send a push notification (if Pushover configured).

## Testing Without RSS Feeds

The Scanner Agent has a `test_scan()` method that returns test data:

```python
from agents.scanner_agent import ScannerAgent

scanner = ScannerAgent(api_key="your_key")
deals = scanner.test_scan()  # Returns 5 test deals
```

## Common Issues

### "No API key found"
- Make sure you created `.env` file from `.env.example`
- Add your OpenRouter API key to `.env`

### "Vector store is empty"
- Run `framework.load_sample_data(100)` to add sample products
- Or wait for the first RSS feed scan

### "Modal not working"
- Set `use_modal=False` to use mock pricer instead
- Modal deployment is optional

## Next Steps

- 📖 Read the full [README.md](README.md) for detailed documentation
- 🔧 Customize agent behavior in respective agent files
- 📊 Add more RSS feed sources in `models.py`
- 🚀 Deploy Modal service for production Hugging Face pricer
- 🔔 Set up Pushover for real push notifications

## Getting Help

Common commands:

```bash
# Check if everything is working
python example_usage.py

# Start the UI
python gradio_app.py

# Check vector store
python -c "from vector_store import VectorStore; print(VectorStore().count())"

# Reset memory
python -c "from agent_framework import AgentFramework; AgentFramework().reset_memory()"
```

## Architecture Overview

```
📱 Gradio UI
    ↓
🧠 Agent Framework (Memory & Logging)
    ↓
📋 Planning Agent (LangGraph)
    ├── 🔍 Scanner Agent (RSS feeds)
    ├── 💰 Ensemble Pricer
    │   ├── RAG Pricer (Vector Store + GPT-4)
    │   └── HF Pricer (Llama via Modal)
    └── 📨 Messaging Agent (Push notifications)
```

Enjoy finding amazing deals with AI! 🎉
