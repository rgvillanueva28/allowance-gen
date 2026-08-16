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
