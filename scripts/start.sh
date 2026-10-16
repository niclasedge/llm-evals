#!/bin/bash

# LLM Evaluator Start Script

set -e

echo "🚀 Starting LLM Evaluator..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file from example..."
    cp .env.example .env
    echo "❗ Please edit .env file with your API keys before running the application."
fi

# Initialize database
echo "🗄️  Initializing database..."
python init_db.py

# Start the application
echo "🌟 Starting application..."
python run.py

echo "✅ LLM Evaluator started successfully!"
echo "🌐 Open http://localhost:8000 in your browser"