"""
Configuration settings for the receipt processing application.
Modify these settings to customize the application behavior.
"""

# Google Gemini API Configuration
# Set your API key as an environment variable: GEMINI_API_KEY
# Get your API key from: https://aistudio.google.com/app/apikey
# Note: This application uses the google.genai package (latest)
GEMINI_API_KEY = None  # Will read from environment variable if not set
GEMINI_MODEL = 'gemini-2.0-flash-exp'  # Model to use for processing

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
VERBOSE_LOGGING = False  # Set to True for detailed Gemini API logsut'
DEFAULT_RECEIPTS_DIR = 'selected_receipts'
DEFAULT_PDF_NAME = 'selected_receipts.pdf'

# Image Processing Configuration
IMAGE_PREPROCESSING = {
    'gaussian_blur_kernel': (5, 5),
    'adaptive_threshold_block_size': 11,
    'adaptive_threshold_C': 2,
}

# Debug Configuration
DEBUG_MODE = False  # Set to True to save intermediate processing images
DEBUG_OUTPUT_DIR = 'debug'
