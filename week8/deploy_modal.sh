#!/bin/bash

# Modal Deployment Script for Hugging Face Pricer

echo "🚀 Modal Deployment Script"
echo "=========================="
echo ""

# Check if modal is installed
if ! command -v modal &> /dev/null; then
    echo "❌ Modal CLI not found"
    echo "Installing Modal..."
    pip install modal
fi

echo "✅ Modal CLI found"
echo ""

# Check if modal is authenticated
if ! modal token list &> /dev/null; then
    echo "🔐 Modal authentication required"
    echo "Running modal setup..."
    modal setup
else
    echo "✅ Modal already authenticated"
fi

echo ""

# Check if secret exists
echo "🔍 Checking for Hugging Face secret..."
if modal secret list | grep -q "huggingface-secret"; then
    echo "✅ Hugging Face secret found"
else
    echo "⚠️  Hugging Face secret not found"
    echo ""
    read -p "Do you want to create it now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your Hugging Face token: " HF_TOKEN
        modal secret create huggingface-secret HUGGINGFACE_TOKEN=$HF_TOKEN
        echo "✅ Secret created"
    else
        echo "❌ Cannot deploy without Hugging Face secret"
        echo "Create it manually with:"
        echo "  modal secret create huggingface-secret HUGGINGFACE_TOKEN=your_token"
        exit 1
    fi
fi

echo ""
echo "📦 Deploying to Modal..."
echo "This will take a few minutes on first deployment..."
echo ""

modal deploy modal_pricer_service.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Deployment successful!"
    echo ""
    echo "Next steps:"
    echo "1. View your app: modal app list"
    echo "2. Check logs: modal app logs agentic-pricer-service"
    echo "3. Run the framework: python gradio_app.py"
    echo ""
    echo "The framework will now use Modal by default!"
else
    echo ""
    echo "❌ Deployment failed"
    echo "Check the error messages above"
    echo ""
    echo "Common issues:"
    echo "- Invalid Hugging Face token"
    echo "- Model not found (update HF_USER and RUN_NAME in modal_pricer_service.py)"
    echo "- Modal account issues (try: modal setup)"
fi
