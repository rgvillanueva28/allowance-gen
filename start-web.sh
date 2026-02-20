#!/bin/bash
# Unix/Linux/macOS startup script for Receipt Processor Web Application

echo "========================================"
echo "Receipt Processor - Web Application"
echo "========================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created."
    echo ""
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Checking dependencies..."
pip install -r requirements.txt --quiet

# Check API key
echo ""
echo "Checking Gemini API key..."
if [ -z "$GEMINI_API_KEY" ]; then
    echo "WARNING: GEMINI_API_KEY environment variable not set!"
    echo ""
    echo "Please set your Gemini API key:"
    echo "  export GEMINI_API_KEY='your-api-key-here'"
    echo ""
    echo "Get your API key from: https://aistudio.google.com/app/apikey"
    echo ""
    exit 1
else
    echo "API key found: ${GEMINI_API_KEY:0:10}..."
fi

# Start the application
echo ""
echo "========================================"
echo "Starting web server..."
echo "Navigate to: http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo "========================================"
echo ""

python app.py
