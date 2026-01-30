#!/bin/bash

# Setup script for Agentic AI Framework

echo "🤖 Setting up Agentic AI Framework..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"
echo ""

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✅ Pip upgraded"
echo ""

# Install requirements
echo "📥 Installing dependencies..."
echo "   This may take a few minutes..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ All dependencies installed successfully"
else
    echo "❌ Error installing dependencies"
    exit 1
fi
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found"
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file and add your API keys:"
    echo "   - OPENROUTER_API_KEY (required)"
    echo "   - PUSHOVER_USER and PUSHOVER_TOKEN (optional)"
    echo "   - HUGGINGFACE_TOKEN (optional, for Modal)"
else
    echo "✅ .env file exists"
fi
echo ""

# Create directories
echo "📁 Creating directories..."
mkdir -p products_vectorstore
echo "✅ Directories created"
echo ""

echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Run: source venv/bin/activate"
echo "3. Run: python gradio_app.py"
echo ""
echo "Or try the example usage:"
echo "   python example_usage.py"
echo ""
