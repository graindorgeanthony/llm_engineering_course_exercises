---
title: Deal_Finder
app_file: gradio_app.py
sdk: gradio
sdk_version: 5.49.1
---
# 🤖 Agentic AI Deal Finder Framework

An autonomous multi-agent system that hunts for amazing deals using LangChain, LangGraph, and multiple AI models.

![Architecture Diagram](https://via.placeholder.com/800x400?text=Agentic+AI+Framework)

## 🎯 Features

- **Multi-Agent Architecture**: Coordinated agents working together using LangGraph
- **Vector Store (ChromaDB)**: Semantic search for similar products
- **Dual Pricing Models**:
  - RAG-based pricer using OpenRouter frontier models (GPT-4)
  - Fine-tuned Hugging Face model via Modal
- **Scanner Agent**: Identifies promising deals from RSS feeds
- **Planning Agent**: Coordinates workflow with state management
- **Messaging Agent**: Sends push notifications via Pushover
- **Beautiful Gradio UI**: Interactive dashboard with real-time logs and visualization
- **Memory & Logging**: Persistent storage and comprehensive logging

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Framework                          │
│                  (Memory & Logging)                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Planning Agent                             │
│              (LangGraph Workflow)                           │
└────┬────────────────┬────────────────┬──────────────────────┘
     │                │                │
     ▼                ▼                ▼
┌─────────┐   ┌──────────────┐   ┌─────────────┐
│ Scanner │   │   Ensemble   │   │  Messaging  │
│  Agent  │   │    Pricer    │   │    Agent    │
└─────────┘   └──────┬───────┘   └─────────────┘
                     │
              ┌──────┴──────┐
              ▼             ▼
         ┌─────────┐   ┌─────────┐
         │   RAG   │   │   HF    │
         │ Pricer  │   │ Pricer  │
         └────┬────┘   └────┬────┘
              │             │
              ▼             ▼
       [Vector Store]  [Modal Service]
```

## 📦 Installation

### 1. Clone and Setup Environment

```bash
cd /Users/anthony/Documents/Code/AI\ Engineer/llm_engineering_course_exercises/week8

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Set up Environment Variables

Create a `.env` file:

```bash
# Required: OpenRouter API Key
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Optional: Pushover for notifications
PUSHOVER_USER=your_pushover_user_key
PUSHOVER_TOKEN=your_pushover_app_token

# Optional: Hugging Face (if using Modal)
HUGGINGFACE_TOKEN=your_hf_token
```

### 3. Deploy Modal Service (Recommended)

The framework uses Modal by default for the Hugging Face pricer model. Deploy it:

```bash
# Quick deployment (interactive script)
./deploy_modal.sh
```

Or manually:

```bash
# Setup Modal account
modal setup

# Add Hugging Face secret to Modal
modal secret create huggingface-secret HUGGINGFACE_TOKEN=your_token

# Deploy the pricer service
modal deploy modal_pricer_service.py
```

See [MODAL_DEPLOYMENT.md](MODAL_DEPLOYMENT.md) for detailed instructions.

**Note**: If you skip this step, the framework will automatically fall back to a mock pricer, but you won't get real price estimates from the fine-tuned model.

## 🚀 Usage

### Running the Gradio UI

```bash
python gradio_app.py
```

This will launch an interactive web interface where you can:
- 🚀 Run the agent framework with live RSS feeds
- 💰 View discovered deals in real-time
- 📋 See agent logs with color-coded messages
- 🎨 Visualize the vector store in 3D
- 📊 Load sample data into vector store
- 📈 View framework statistics
- ✅ Toggle Modal on/off (checked by default)

### Running from Command Line

```python
from agent_framework import AgentFramework

# Initialize framework (Modal enabled by default)
framework = AgentFramework()

# Load sample data (if vector store is empty)
if framework.vector_store.count() == 0:
    framework.load_sample_data(200)

# Run the framework
opportunities = framework.run()

# View results
for opp in opportunities:
    print(f"Product: {opp.deal.product_description[:50]}...")
    print(f"Price: ${opp.deal.price:.2f}")
    print(f"Estimate: ${opp.estimate:.2f}")
    print(f"Discount: ${opp.discount:.2f}")
    print(f"URL: {opp.deal.url}\n")
```

## 🔧 Configuration

### Agent Framework Options

```python
AgentFramework(
    api_key="your_openrouter_key",  # Optional, reads from env
    use_modal=True,                 # Default: True (uses Modal HF pricer)
    test_mode=False                 # Set True for testing without API calls
)
```

**Note**: With `use_modal=True` (default), the framework will:
1. Try to connect to your deployed Modal service
2. If Modal is not deployed or connection fails, automatically fall back to mock pricer
3. Continue working with just the RAG pricer

### Customizing Agents

You can customize agent behavior by modifying:

- `DEAL_THRESHOLD` in `planning_agent.py` (minimum discount to trigger notification)
- Model selection in each agent (e.g., change from GPT-4 to Claude)
- Number of similar products in RAG search
- RSS feed sources in `models.py`

## 📁 Project Structure

```
week8/
├── agent_framework.py          # Main framework orchestration
├── models.py                   # Pydantic models & data structures
├── utils.py                    # Logging utilities & base agent class
├── vector_store.py             # ChromaDB vector store wrapper
├── modal_pricer_service.py     # Modal service for HF model
├── gradio_app.py               # Gradio UI application
├── agents/
│   ├── __init__.py
│   ├── scanner_agent.py        # Scans RSS feeds for deals
│   ├── rag_pricer_agent.py     # RAG + HF + Ensemble pricers
│   ├── messaging_agent.py      # Push notifications
│   └── planning_agent.py       # LangGraph workflow coordinator
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── .env                        # Environment variables (create this)
├── agent_memory.json           # Persistent memory (auto-generated)
└── products_vectorstore/       # ChromaDB data (auto-generated)
```

## 🎨 Key Components

### 1. Scanner Agent
- Fetches deals from RSS feeds (DealNews)
- Uses LangChain with structured outputs
- Filters for detailed descriptions and clear prices
- Removes duplicates based on memory

### 2. RAG Pricer Agent
- Performs semantic search in vector store
- Finds 5 most similar products
- Uses frontier model (GPT-4) with context
- Returns price estimate

### 3. Hugging Face Pricer Agent
- Uses fine-tuned Llama model
- Deployed via Modal for scalability
- Falls back to mock pricer if Modal not deployed

### 4. Ensemble Pricer Agent
- Combines RAG (80%) + HF (20%) estimates
- Weighted ensemble for better accuracy
- Can be customized with different weights

### 5. Planning Agent
- Coordinates workflow using LangGraph
- State management with typed dictionaries
- Conditional edges based on results
- Handles errors gracefully

### 6. Messaging Agent
- Crafts engaging messages using Claude
- Sends push notifications via Pushover
- Falls back to console logging if not configured

## 🧪 Testing

### Test Individual Agents

```python
# Test Scanner Agent
from agents.scanner_agent import ScannerAgent

scanner = ScannerAgent(api_key="your_key")
deals = scanner.test_scan()  # Uses test data
print(f"Found {len(deals.deals)} test deals")

# Test RAG Pricer
from vector_store import VectorStore
from agents.rag_pricer_agent import RAGPricerAgent

vector_store = VectorStore()
pricer = RAGPricerAgent(vector_store, api_key="your_key")
price = pricer.price("Apple MacBook Pro 16-inch M3")
print(f"Estimated price: ${price:.2f}")
```

### Load Sample Data

```python
framework = AgentFramework()
framework.load_sample_data(100)  # Load 100 sample products
print(f"Vector store has {framework.vector_store.count()} items")
```

## 🔔 Push Notifications Setup

1. Create a Pushover account: https://pushover.net/
2. Create an application in Pushover
3. Get your User Key and API Token
4. Add to `.env`:
   ```
   PUSHOVER_USER=your_user_key
   PUSHOVER_TOKEN=your_api_token
   ```

## 🌐 OpenRouter Setup

1. Create account at https://openrouter.ai/
2. Add credits to your account
3. Generate API key
4. Add to `.env`:
   ```
   OPENROUTER_API_KEY=your_key_here
   ```

## 🚢 Modal Deployment

Modal allows you to deploy the Hugging Face pricer model to the cloud:

```bash
# Login to Modal
modal setup

# Add secret
modal secret create huggingface-secret HUGGINGFACE_TOKEN=your_hf_token

# Deploy
modal deploy modal_pricer_service.py

# Check deployment
modal app list

# View logs
modal app logs agentic-pricer-service
```

## 📊 Visualization

The Gradio UI includes:
- **3D t-SNE visualization** of product embeddings
- **Real-time agent logs** with color coding
- **Interactive table** of discovered deals
- **Statistics dashboard** with metrics

## 🛠️ Troubleshooting

### Vector Store Empty
```python
framework = AgentFramework()
framework.load_sample_data(200)
```

### Modal Not Working
Set `use_modal=False` to use mock pricer:
```python
framework = AgentFramework(use_modal=False)
```

### API Rate Limits
The framework respects rate limits and handles errors gracefully. If you hit limits:
- Reduce frequency of runs
- Use test mode for development
- Consider caching results

### Memory Issues
Reset memory if it gets too large:
```python
framework = AgentFramework()
framework.reset_memory()
```

## 📚 Learn More

- **LangChain**: https://python.langchain.com/
- **LangGraph**: https://langchain-ai.github.io/langgraph/
- **ChromaDB**: https://docs.trychroma.com/
- **Modal**: https://modal.com/docs
- **OpenRouter**: https://openrouter.ai/docs

## 🤝 Contributing

Feel free to extend this framework:
- Add more RSS feed sources
- Implement additional agents
- Improve pricing models
- Add more notification channels (Telegram, SMS, etc.)
- Create custom visualizations

## 📝 License

This project is for educational purposes as part of the LLM Engineering course.

## 🎓 Credits

Inspired by the week8 materials from the LLM Engineering course, reimagined with:
- LangChain/LangGraph for simpler agent coordination
- OpenRouter for frontier model access
- Modern Gradio UI with enhanced visualization
- Comprehensive error handling and logging

---

Built with ❤️ using LangChain, LangGraph, and OpenRouter
