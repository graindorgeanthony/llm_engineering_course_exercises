# LLM Engineering - Production AI Applications

**By Anthony Graindorge** | [LinkedIn](https://www.linkedin.com/in/anthonygraindorge/)

This repository showcases my comprehensive implementations of Large Language Model (LLM) engineering projects, from foundational API integrations to production-ready RAG systems and fine-tuned models. These exercises are based on [Ed Donner's LLM Engineering course](https://www.udemy.com/course/llm-engineering-master-ai-and-large-language-models), with my own customizations and extensions.

## 🎯 What's Demonstrated Here

This repository demonstrates practical experience with:

- **LLM API Integration** across multiple providers (OpenAI, Anthropic, Ollama, Google)
- **RAG (Retrieval Augmented Generation)** systems with vector databases and evaluation frameworks
- **Model Fine-tuning** for specialized tasks and domain adaptation
- **Production Web UIs** with Gradio for interactive AI applications
- **Multi-agent Systems** with memory, planning, and tool integration
- **Cloud Deployment** using Modal for serverless AI services
- **Machine Learning** fundamentals and model evaluation techniques

## 🛠️ Technical Stack

- **Python 3.12** with type hints and modern async patterns
- **LLM APIs**: OpenAI, Anthropic Claude, Google Gemini, Ollama
- **RAG Stack**: LangChain, ChromaDB, sentence-transformers, FAISS
- **ML/DL**: scikit-learn, XGBoost, PyTorch, HuggingFace Transformers
- **UI Frameworks**: Gradio for rapid prototyping
- **Vector Databases**: ChromaDB, FAISS
- **Deployment**: Modal, Docker
- **Tools**: uv package manager, Jupyter notebooks

## 📁 Repository Structure

### Week 1: LLM Foundations
**Location**: `week1/`

Core LLM API integration and basic applications:
- Direct OpenAI API calls with prompt engineering
- Local LLM integration with Ollama
- Sales brochure generator with structured outputs
- AI tutor chatbot implementation

**Key Skills**: API integration, prompt engineering, local LLMs, conversation management

---

### Week 2: Interactive AI Applications
**Location**: `week2/`

Production-ready web applications with advanced LLM features:
- Reasoning chains for complex problem-solving
- Gradio web interfaces with real-time streaming
- Multi-model selector for comparing LLM outputs
- Tool-calling implementations for external data access
- Akinator-style guessing game with iterative questioning

**Key Skills**: Gradio UI development, streaming responses, tool/function calling, SQLite integration

**Highlights**:
- `exercise_3_llm_call_with_gradio_with_streaming.py` - Real-time token streaming
- `exercise_8_chat_with_tools.py` - Multi-tool orchestration
- `exercise_6_chat_akinator.py` - Stateful conversation game

---

### Week 3: HuggingFace & Multimodal AI
**Location**: `week3/`

Advanced model techniques and multimodal processing:
- HuggingFace Pipelines for zero-shot classification
- Tokenizer deep-dive and vocabulary analysis
- Model quantization for efficient inference
- Meeting minutes generator (audio → text → summary)
- Synthetic data generation system with Gradio app

**Key Skills**: HuggingFace ecosystem, audio processing, synthetic data, quantization techniques

**Highlights**:
- `exercise_4_meeting_minutes.py` - Complete audio-to-structured-summary pipeline
- `synthetic_data_generator/` - Full-stack synthetic data generation app

---

### Week 4: Code Intelligence & Benchmarking
**Location**: `week4/`

LLM-powered development tools:
- Cross-language code translation (Python → C/Rust)
- Comprehensive LLM benchmarking framework
- Automated documentation specialist
- Unit test generation system

**Key Skills**: Code generation, benchmarking methodology, automated testing, technical documentation

**Technical Highlights**:
- `exercise_3_llm_ultimate_benchmark.py` - Multi-model performance comparison
- `exercise_5_llm_unit_tester_specialist.py` - Test-driven development automation
- `llm_benchmark/` - Complete benchmarking application

---

### Week 5: RAG Systems & Embeddings
**Location**: `week5/`

Production RAG implementations with evaluation:
- Embedding visualization and similarity analysis
- LangChain RAG pipeline implementation
- Simple and complex RAG evaluators
- Insurance claims RAG system with domain-specific knowledge

**Key Skills**: Vector embeddings, ChromaDB, RAG architecture, evaluation metrics, LangChain

**Highlights**:
- `exercise_3_evaluator_simple_embeddings/` - Basic RAG with evaluation framework
- `exercise_4_evaluator_complex_embeddings/` - Advanced RAG with preprocessing
- `exercise_5_insurance_claims_rag/` - Production-ready domain-specific RAG
  - 200+ document knowledge base
  - Custom evaluation suite
  - Gradio interface for interactive querying

**Architecture**:
- Document ingestion and preprocessing pipelines
- Vector store optimization
- Retrieval accuracy evaluation
- Answer quality assessment

---

### Week 6: Machine Learning Foundations
**Location**: `week6/`

Classical ML and model evaluation:
- Data visualization for exploratory analysis
- Regression models (Linear Regression, Random Forest, XGBoost)
- Deep Neural Networks with PyTorch
- LLM evaluation frameworks
- Frontier model fine-tuning experiments

**Key Skills**: scikit-learn, XGBoost, PyTorch, model evaluation, fine-tuning preparation

**Project Focus**: `pricer/` - Complete pricing prediction system
- Multiple ML model implementations
- Model comparison and evaluation
- Deep learning architecture
- Dataset preprocessing and feature engineering

---

### Week 7: Model Fine-tuning
**Location**: `week7/`

Custom model training and evaluation:
- Training dataset construction and curation
- Base model evaluation and benchmarking
- Supervised fine-tuning on custom data
- Fine-tuned model evaluation and comparison
- Google Colab and local training implementations

**Key Skills**: Dataset engineering, fine-tuning workflows, model evaluation, HuggingFace training

**Projects**:
- **Pricer Fine-tuning**: Specialized pricing model
- **Shipping/Freight Booking**: Domain-specific freight cost prediction
  - Custom dataset from domain data
  - Fine-tuned model vs base model comparison
  - Evaluation pipeline with metrics

**Technical Highlights**:
- Jupyter notebooks for Colab training
- Local training scripts for GPU machines
- Comprehensive evaluation frameworks
- Before/after performance analysis

---

### Week 8: Multi-Agent Production System
**Location**: `week8/`

Enterprise-grade multi-agent application with deployment:
- Agent framework with specialized agent roles
- RAG-powered product pricing agent
- Planning agent for task decomposition
- Scanner agent for data extraction
- Messaging agent for notifications
- Persistent agent memory system
- Gradio web application
- Modal cloud deployment

**Key Skills**: Multi-agent orchestration, agent memory, cloud deployment, production architecture

**System Architecture**:
```
User Query → Planning Agent → Task Decomposition
    ↓
RAG Agent (ChromaDB) → Product Knowledge Retrieval
    ↓
Scanner Agent → Data Extraction & Validation
    ↓
Messaging Agent → User Notification
    ↓
Response with Memory Persistence
```

**Technical Highlights**:
- `agents/` - Modular agent implementations
  - `planning_agent.py` - Strategic task planning
  - `rag_pricer_agent.py` - Vector search and pricing
  - `scanner_agent.py` - Document parsing
  - `messaging_agent.py` - Communication layer
- `agent_framework.py` - Agent orchestration system
- `modal_pricer_service.py` - Serverless deployment
- `products_vectorstore/` - Persistent vector database
- `gradio_app.py` - Production web interface

**Deployment**:
- Modal cloud deployment scripts
- Environment configuration
- Vector store persistence
- Agent state management

---

## 🚀 Running the Code

**General Setup**:
```bash
# Install dependencies (from exercises/llm_engineering/)
pip install -r requirements.txt
# OR use conda
conda env create -f environment.yml
conda activate llm-eng

# Set up API keys in .env file
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"

# Run specific exercises
python week1/exercise_1_llm_call.py
python week2/exercise_8_chat_with_tools.py
python week5/exercise_5_insurance_claims_rag/app.py
python week8/gradio_app.py
```

**Week-specific notes**:
- Week 3: Requires audio files (`.mp3`, `.wav`) for transcription exercises
- Week 5: Automatic vector DB creation on first run
- Week 7: Fine-tuning requires GPU access (use Colab notebooks for cloud GPUs)
- Week 8: Modal deployment requires Modal account and setup

## 📚 Skills Demonstrated

### LLM Engineering
- Multi-provider LLM integration (OpenAI, Anthropic, Google, Ollama)
- Advanced prompt engineering and chain-of-thought
- Function/tool calling for external integrations
- Token streaming for real-time UX
- Context window management

### RAG Systems
- Vector embedding generation and optimization
- Semantic search with ChromaDB/FAISS
- Document ingestion pipelines
- Retrieval accuracy evaluation
- Answer quality assessment
- Production RAG architecture

### Model Development
- Fine-tuning workflows for domain adaptation
- Training dataset curation
- Model evaluation frameworks
- Hyperparameter optimization
- Before/after performance analysis

### Software Engineering
- Clean, modular Python architecture
- Type hints and documentation
- Error handling and logging
- Environment configuration
- Testing and evaluation frameworks

### Production Deployment
- Gradio web applications
- Cloud deployment (Modal)
- Vector database persistence
- Agent state management
- Scalable architecture patterns

### Machine Learning
- Classical ML models (regression, random forests, XGBoost)
- Deep learning with PyTorch
- Model evaluation metrics
- Feature engineering
- Data preprocessing pipelines

## 🏗️ Notable Projects

### Insurance Claims RAG System (`week5/exercise_5_insurance_claims_rag/`)
Production-ready RAG system with:
- 200+ insurance policy documents
- Custom evaluation framework
- Gradio web interface
- ChromaDB vector store
- Preprocessing pipeline

### Multi-Agent Pricing System (`week8/`)
Enterprise multi-agent application:
- 4 specialized agent types
- Persistent memory system
- RAG-powered knowledge retrieval
- Modal cloud deployment
- Production Gradio interface

### Freight Booking Fine-tuned Model (`week7/shipping/`)
Custom fine-tuned model:
- Domain-specific dataset creation
- Fine-tuning pipeline
- Comprehensive evaluation
- Before/after comparison

## 🔗 Course Reference

Original course materials: [LLM Engineering - Master AI and Large Language Models (Udemy)](https://www.udemy.com/course/llm-engineering-master-ai-and-large-language-models)

Instructor: [Ed Donner on LinkedIn](https://www.linkedin.com/in/eddonner/)

---

## 📊 Project Statistics

- **8 weeks** of progressive LLM engineering topics
- **50+ exercises** covering the full LLM engineering stack
- **3 production applications** with web UIs
- **2 fine-tuned models** for specialized domains
- **3 RAG systems** with evaluation frameworks
- **1 multi-agent system** with cloud deployment

---

## 📧 Contact

**Anthony Graindorge**  
[LinkedIn](https://www.linkedin.com/in/anthonygraindorge/)

Feel free to reach out if you'd like to discuss these implementations or LLM engineering in general.
