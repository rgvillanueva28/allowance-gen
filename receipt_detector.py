"""
Receipt Detection Module
Detects and extracts individual receipts from images.
"""
import cv2
import numpy as np
from PIL import Image


def detect_and_extract_receipts(image_path):
    """
    Detect and extract individual receipts from an image.
    
    Args:
        image_path: Path to the input image file
        
    Returns:
        List of dictionaries containing receipt information:
        [{'image': PIL.Image, 'source': str, 'index': int}, ...]
    """
    # Read image
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Unable to read image '{image_path}'")
        return []
    
    # Create a copy for processing
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply preprocessing
    # Use adaptive thresholding to handle varying lighting conditions
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blurred, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 
        11, 2
    )
    
    # Find contours
    contours, _ = cv2.findContours(
        thresh, 
        cv2.RETR_EXTERNAL, 
        cv2.CHAIN_APPROX_SIMPLE
    )
    
    # Filter and sort contours by area
    min_area = 10000  # Minimum area to be considered a receipt
    receipt_contours = []
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > min_area:
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            # Filter by aspect ratio (receipts are typically taller than wide)
            aspect_ratio = h / w if w > 0 else 0
            if 0.5 < aspect_ratio < 5:  # Reasonable receipt proportions
                receipt_contours.append((x, y, w, h, area))
    
    receipts = []
    
    if not receipt_contours:
        # If no contours found, treat the entire image as a single receipt
        print(f"  No distinct receipts detected in '{image_path}', treating as single receipt.")
        pil_img = Image.open(image_path)
        receipts.append({
            'image': pil_img,
            'source': image_path,
            'index': 0
        })
    else:
        # Sort by y-coordinate (top to bottom) then x-coordinate (left to right)
        receipt_contours.sort(key=lambda r: (r[1], r[0]))
        
        print(f"  Detected {len(receipt_contours)} receipt(s) in '{image_path}'")
        
        # Extract each receipt
        for idx, (x, y, w, h, area) in enumerate(receipt_contours):
            # Add padding
            padding = 10
            x_start = max(0, x - padding)
            y_start = max(0, y - padding)
            x_end = min(img.shape[1], x + w + padding)
            y_end = min(img.shape[0], y + h + padding)
            
            # Extract receipt region
            receipt_img = img[y_start:y_end, x_start:x_end]
            
            # Convert to PIL Image
            receipt_pil = Image.fromarray(cv2.cvtColor(receipt_img, cv2.COLOR_BGR2RGB))
            
            receipts.append({
                'image': receipt_pil,
                'source': image_path,
                'index': idx
            })
    
    return receipts


def preprocess_for_ocr(image):
    """
    Preprocess an image for better OCR accuracy.
    
    Args:
        image: PIL Image object
        
    Returns:
        PIL Image object
    """
    # Convert to numpy array
    img_array = np.array(image)
    
    # Convert to grayscale if color
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    
    # Apply denoising
    denoised = cv2.fastNlMeansDenoising(gray)
    
    # Apply adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11, 2
    )
    
    # Convert back to PIL Image
    return Image.fromarray(thresh)
