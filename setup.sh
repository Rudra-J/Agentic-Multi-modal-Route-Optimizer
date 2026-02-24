#!/bin/bash
# Quick setup script for development environment
# Run this after cloning: bash setup.sh

echo "🚀 Setting up Agentic Auto Routing System..."

# Check Python version
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $PYTHON_VERSION"

# Create virtual environment
echo "📦 Creating virtual environment..."
python -m venv venv

# Activate virtual environment
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    # Windows
    source venv/Scripts/activate
else
    # macOS/Linux
    source venv/bin/activate
fi

echo "✓ Virtual environment activated"

# Install dependencies
echo "📥 Installing dependencies..."
PIP_TRUSTED_HOST_ARGS="--trusted-host pypi.org --trusted-host files.pythonhosted.org"
pip install --upgrade pip $PIP_TRUSTED_HOST_ARGS
pip install -r requirements.txt $PIP_TRUSTED_HOST_ARGS

echo "✓ Dependencies installed"

# Setup environment file
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your OPENROUTER_API_KEY"
else
    echo "✓ .env file exists"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env and add your OpenRouter API key"
echo "2. Run tests: python test_harness.py"
echo "3. Start server: uvicorn main:app --reload --port 8001"
echo "4. Visit: http://127.0.0.1:8001/"
echo ""
