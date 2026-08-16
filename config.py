"""
Configuration settings for the receipt processing application.
Modify these settings to customize the application behavior.
"""
import json
from pathlib import Path

# Currency Configuration (fallback defaults - overridden by Settings UI via settings.json)
CURRENCY_SYMBOL = '₱'  # Philippine Peso
CURRENCY_CODE = 'PHP'
CURRENCY_NAME = 'Philippine Peso'

# Receipt Selection Configuration
MAX_OVERAGE_ALLOWED = 100  # Maximum amount allowed to exceed target
EXACT_MATCH_TOLERANCE = 0.01  # Tolerance for "exact" match

# Google Gemini API Configuration
# Set your API key as an environment variable: GEMINI_API_KEY
# Get your API key from: https://aistudio.google.com/app/apikey
# Note: The Gemini model is now configured via the Settings page (settings.json),
#       NOT in this file. API keys MUST remain in .env / environment variables.
GEMINI_API_KEY = None  # Will read from environment variable if not set

# Image Processing Configuration (for Gemini input)
MAX_IMAGE_SIZE = 4096  # Maximum image dimension (pixels)
IMAGE_QUALITY = 95  # JPEG quality for compression (1-100)

# Amount Extraction Configuration
MIN_VALID_AMOUNT = 0.01    # Minimum valid amount
MAX_VALID_AMOUNT = 100000.0  # Maximum valid amount

# Gemini Processing Configuration
GEMINI_PROMPT_TEMPLATE = """Analyze these images to find all receipts.

For every individual receipt found across these images:
1. Identify the 'file_id' it belongs to (receipts_0, receipts_1, etc., based on image order).
2. If an image has multiple receipts, assign a sub-index (e.g., receipts_0_1, receipts_0_2).
3. Extract the TOTAL amount as a number (just the number, no currency symbols).
4. Provide a 'box' which is the bounding box surrounding only that specific receipt, in the format [ymin, xmin, ymax, xmax]. Use a scale of 0 to 1000 where [0,0] is top-left and [1000,1000] is bottom-right.

Important:
- Look for the TOTAL or GRAND TOTAL line on each receipt
- Extract only the final amount to pay
- Be precise with bounding boxes to capture the entire receipt
- If a single image contains one receipt, use the format: receipts_0_0 (not just receipts_0)

Return ONLY a valid JSON array of objects, no other text:
[{{"id": "receipts_0_1", "file_id": "receipts_0", "total": 15.50, "box": [100, 150, 400, 450]}}]

If no receipts are found, return an empty array: []"""

# Debug Configuration
DEBUG_MODE = False  # Set to True to save intermediate processing images
DEBUG_OUTPUT_DIR = 'debug'

SETTINGS_FILE = Path(__file__).parent / 'settings.json'

# Backwards-compatible fallback model name (Settings UI overrides this)
GEMINI_MODEL = 'gemini-3-flash-preview'


def get_runtime_settings():
    """Read user-facing settings from settings.json, falling back to config defaults."""
    defaults = {
        'first_name': '',
        'last_name': '',
        'gemini_model': GEMINI_MODEL,
        'currency_symbol': CURRENCY_SYMBOL,
        'currency_code': CURRENCY_CODE,
        'currency_name': CURRENCY_NAME,
        'max_overage': MAX_OVERAGE_ALLOWED,
    }
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
                defaults.update({k: data.get(k, defaults[k]) for k in defaults})
    except Exception as e:
        print(f"Error loading runtime settings: {e}")
    return defaults


def get_currency_symbol():
    """Return the currency symbol configured in Settings (fallback to config default)."""
    return get_runtime_settings().get('currency_symbol', CURRENCY_SYMBOL)


def get_gemini_model():
    """Return the Gemini model configured in Settings (fallback to config default)."""
    return get_runtime_settings().get('gemini_model', GEMINI_MODEL)


def get_max_overage():
    """Return the max overage configured in Settings (fallback to config default)."""
    return float(get_runtime_settings().get('max_overage', MAX_OVERAGE_ALLOWED))

# Image Processing Configuration
IMAGE_PREPROCESSING = {
    'gaussian_blur_kernel': (5, 5),
    'adaptive_threshold_block_size': 11,
    'adaptive_threshold_C': 2,
}

# Debug Configuration
DEBUG_MODE = False  # Set to True to save intermediate processing images
DEBUG_OUTPUT_DIR = 'debug'
