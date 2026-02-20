# Migration Guide: Tesseract to Google Gemini AI

## Overview

The receipt processing application has been upgraded from Tesseract OCR to Google Gemini Flash 3 AI for improved accuracy and simpler setup.

## Key Changes

### What's Different

1. **No More Tesseract Installation Required**
   - Previously: Required installing Tesseract OCR system software
   - Now: Only requires a free Google Gemini API key

2. **Better Accuracy**
   - AI-powered detection and extraction
   - Better handling of various receipt formats
   - More accurate bounding box detection
   - Improved amount extraction

3. **Simplified Architecture**
   - Detection and extraction in a single API call
   - No separate detection and OCR steps
   - Cleaner, more maintainable code

### Files Changed

**New Files:**
- `gemini_processor.py` - New AI-powered processor
- `.env.example` - Environment variable template
- `MIGRATION.md` - This file

**Modified Files:**
- `main.py` - Updated to use Gemini processor
- `app.py` - Updated to use Gemini processor
- `config.py` - New Gemini configuration settings
- `requirements.txt` - Removed opencv-python and pytesseract, added google-generativeai
- `README.md` - Updated documentation
- `QUICKSTART.md` - Updated quick start guide
- `examples.py` - Updated examples
- `start-web.bat` - Check for API key instead of Tesseract
- `start-web.sh` - Check for API key instead of Tesseract
- `templates/about.html` - Updated feature descriptions
- `templates/index.html` - Updated feature descriptions
- `.gitignore` - Added .env files

**Deprecated Files (can be removed):**
- `receipt_detector.py` - Replaced by gemini_processor.py
- `ocr_processor.py` - Replaced by gemini_processor.py

## Migration Steps

### 1. Get a Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy your API key

### 2. Set Environment Variable

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

**Permanent Setup:**
Create a `.env` file in the project root:
```
GEMINI_API_KEY=your-api-key-here
```

### 3. Update Dependencies

```bash
pip install -r requirements.txt
```

This will:
- Install google-genai (new package)
- Update other dependencies

**Note:** The old `google-generativeai` package is deprecated. The application now uses `google.genai` for better support and updates.

### 4. Test the Application

**Test Command Line:**
```bash
python main.py receipt1.jpg receipt2.png -t 100.00
```

**Test Web Interface:**
```bash
python app.py
```
Then navigate to http://localhost:5000

## API Compatibility

The new `gemini_processor.py` provides backward-compatible functions:

```python
# Old way (still works with Gemini):
from gemini_processor import detect_and_extract_receipts, extract_receipt_amounts

receipts = detect_and_extract_receipts(image_path)
receipts_with_amounts = extract_receipt_amounts(receipts)

# New way (recommended):
from gemini_processor import process_receipts_with_gemini

receipts_with_amounts = process_receipts_with_gemini([image_path])
```

## Benefits of Migration

### 1. No System Dependencies
- No need to install Tesseract OCR
- Works on any OS with Python
- Easier deployment

### 2. Better Accuracy
- AI understands context better
- Handles various receipt formats
- More reliable amount extraction

### 3. Multi-Receipt Detection
- Detects multiple receipts in one image
- Provides accurate bounding boxes
- Better separation of receipts

### 4. Simpler Maintenance
- Single API for detection and extraction
- Less code to maintain
- Better error handling

## Cost Considerations

### Gemini API Pricing (as of 2026)

**Free Tier:**
- 15 requests per minute
- 1,500 requests per day
- 1 million tokens per day

**Paid Tier:**
- Pay-as-you-go pricing
- Higher rate limits
- Production SLA

For typical usage (personal expense reports), the free tier is sufficient.

## Troubleshooting

### API Key Not Found
```
ValueError: Gemini API key not found
```
**Solution:** Set the `GEMINI_API_KEY` environment variable

### Rate Limiting
```
Error: API rate limit exceeded
```
**Solution:** Wait a few moments or upgrade to paid tier

### Import Errors
```
ModuleNotFoundError: No module named 'google.generativeai'
```
**Solution:** Run `pip install -r requirements.txt`

## Rollback (If Needed)

If you need to revert to Tesseract:

1. Checkout the previous version from git
2. Install Tesseract OCR
3. Run `pip install -r requirements.txt`

## Support

- Check [README.md](README.md) for full documentation
- See [QUICKSTART.md](QUICKSTART.md) for setup help
- Review examples in `examples.py`

## Questions?

- **Q: Do I need to pay for Gemini API?**
  A: No, the free tier is generous for personal use

- **Q: Is my data secure?**
  A: Images are sent to Google's servers. Review Google's privacy policy if concerned

- **Q: Can I still use Tesseract?**
  A: The old code is available in git history, but Gemini is recommended

- **Q: What about offline processing?**
  A: Gemini requires internet. For offline, use the previous Tesseract version
