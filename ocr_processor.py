"""
OCR Processing Module
Extracts text and amounts from receipt images using OCR.
"""
import re
import pytesseract
from receipt_detector import preprocess_for_ocr


# Common patterns for currency amounts
AMOUNT_PATTERNS = [
    r'\$\s*(\d+[,\d]*\.?\d*)',  # $123.45 or $1,234.56
    r'(?:total|amount|sum|grand total|balance|due)[:\s]*\$?\s*(\d+[,\d]*\.?\d+)',  # Total: $123.45
    r'(\d+[,\d]*\.\d{2})\s*(?:total|usd|cad|eur)?',  # 123.45 total
]

# Keywords that often precede or follow the total amount
TOTAL_KEYWORDS = [
    'total', 'grand total', 'amount due', 'balance', 'sum',
    'amount', 'subtotal', 'payment', 'charged', 'balance due'
]


def extract_receipt_amounts(receipts):
    """
    Extract amounts from receipt images using OCR.
    
    Args:
        receipts: List of receipt dictionaries with 'image' key
        
    Returns:
        List of receipt dictionaries with added 'amount' and 'text' keys
    """
    receipts_with_amounts = []
    
    for receipt in receipts:
        try:
            # Preprocess image for better OCR
            processed_img = preprocess_for_ocr(receipt['image'])
            
            # Perform OCR
            text = pytesseract.image_to_string(
                processed_img,
                config='--psm 6'  # Assume uniform block of text
            )
            
            # Extract amount
            amount = extract_total_amount(text)
            
            if amount is not None:
                receipt['amount'] = amount
                receipt['text'] = text
                receipts_with_amounts.append(receipt)
            else:
                print(f"  Warning: Could not extract amount from receipt "
                      f"(source: {receipt['source']}, index: {receipt['index']})")
        
        except Exception as e:
            print(f"  Error processing receipt (source: {receipt['source']}, "
                  f"index: {receipt['index']}): {str(e)}")
    
    return receipts_with_amounts


def extract_total_amount(text):
    """
    Extract the total amount from OCR text.
    
    Args:
        text: OCR extracted text from receipt
        
    Returns:
        Float value of the total amount, or None if not found
    """
    # Normalize text
    text_lower = text.lower()
    lines = text.split('\n')
    
    amounts_found = []
    
    # Strategy 1: Look for explicit total keywords
    for line in lines:
        line_lower = line.lower()
        for keyword in TOTAL_KEYWORDS:
            if keyword in line_lower:
                # Try to extract amount from this line
                amount = extract_amount_from_line(line)
                if amount:
                    amounts_found.append((amount, 10))  # High priority
    
    # Strategy 2: Try all amount patterns
    for pattern in AMOUNT_PATTERNS:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                # Get the captured group (the numeric part)
                amount_str = match.group(1)
                # Remove commas and convert to float
                amount = float(amount_str.replace(',', ''))
                if amount > 0:
                    amounts_found.append((amount, 5))  # Medium priority
            except (ValueError, IndexError):
                continue
    
    # Strategy 3: Look for any decimal number with 2 decimal places
    decimal_pattern = r'\b(\d+\.\d{2})\b'
    matches = re.finditer(decimal_pattern, text)
    for match in matches:
        try:
            amount = float(match.group(1))
            if amount > 0:
                amounts_found.append((amount, 1))  # Low priority
        except ValueError:
            continue
    
    if not amounts_found:
        return None
    
    # Sort by priority (highest first), then by amount (largest first)
    amounts_found.sort(key=lambda x: (-x[1], -x[0]))
    
    # Return the highest priority, largest amount
    return amounts_found[0][0]


def extract_amount_from_line(line):
    """
    Extract a monetary amount from a single line of text.
    
    Args:
        line: Single line of text
        
    Returns:
        Float value or None
    """
    # Try to find currency amounts
    patterns = [
        r'\$\s*(\d+[,\d]*\.?\d*)',
        r'(\d+[,\d]*\.\d{2})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            try:
                amount_str = match.group(1).replace(',', '')
                amount = float(amount_str)
                if amount > 0:
                    return amount
            except ValueError:
                continue
    
    return None


def validate_amount(amount, min_amount=0.01, max_amount=100000.0):
    """
    Validate that an amount is within reasonable bounds.
    
    Args:
        amount: The amount to validate
        min_amount: Minimum valid amount
        max_amount: Maximum valid amount
        
    Returns:
        Boolean indicating if amount is valid
    """
    return amount is not None and min_amount <= amount <= max_amount
