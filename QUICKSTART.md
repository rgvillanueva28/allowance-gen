# Quick Start Guide - Receipt Processor Web Application

## Prerequisites

1. **Python 3.8+** installed
2. **Google Gemini API Key** (free tier available)

### Get Your Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy your API key

### Set Your API Key

**Windows (Command Prompt):**
```cmd
set GEMINI_API_KEY=your-api-key-here
```

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY="your-api-key-here"
```

**macOS/Linux:**
```bash
export GEMINI_API_KEY="your-api-key-here"
```

**Permanent Setup (Recommended):**
Add to your system environment variables or create a `.env` file in the project directory.

> **Note:** Your API key is always kept in `.env` — never store it in the app's Settings page. The Settings page only lets you choose the Gemini **model** and currency preferences.

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify API key is set:**
   ```bash
   # Windows (Command Prompt)
   echo %GEMINI_API_KEY%
   
   # Windows (PowerShell)
   echo $env:GEMINI_API_KEY
   
   # macOS/Linux
   echo $GEMINI_API_KEY
   ```

## Running the Web Application

1. **Start the server:**
   ```bash
   python app.py
   ```

2. **Open your browser:**
   Navigate to: http://localhost:5000

3. **Upload and process receipts:**
   - Drag and drop receipt images or click to select
   - Enter your target amount
   - Click "Process Receipts"
   - View results and download PDF

4. **Configure settings (optional):**
   - Visit **Settings** in the navigation menu
   - Set your Gemini model, currency symbol/code/name, and max overage
   - Click "Save Settings"

## Troubleshooting

### API Key Not Found
If you see "Gemini API key not found":
- Make sure you've set the `GEMINI_API_KEY` environment variable
- Restart your terminal/command prompt after setting it
- Verify the key is correct at [Google AI Studio](https://aistudio.google.com/app/apikey)

### Import Errors
Run: `pip install -r requirements.txt`

### Port Already in Use
Change the port in `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Changed from 5000
```

### Rate Limiting
If you hit API rate limits:
- Wait a few moments between requests
- The free tier is generous but has limits
- Consider upgrading for higher throughput

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Edit [config.py](config.py) to customize settings

## Support

For issues or questions:
- Check the README troubleshooting section
- Verify all dependencies are installed
- Ensure receipt images are clear and well-lit
