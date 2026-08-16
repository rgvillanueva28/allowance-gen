"""
Gemini Processor Module
Uses Google Gemini Flash 3 API for receipt detection and extraction.
"""
import json
import os
from pathlib import Path
from io import BytesIO
from PIL import Image
from google import genai
from google.genai import types
from config import CURRENCY_SYMBOL, get_gemini_model


# Configure Gemini API
def configure_gemini(api_key=None):
    """
    Configure the Gemini API with the provided API key.
    
    Args:
        api_key: Google API key. If None, reads from GEMINI_API_KEY environment variable.
    """
    if api_key is None:
        api_key = os.environ.get('GEMINI_API_KEY')
    
    if not api_key:
        raise ValueError(
            "Gemini API key not found. Please set GEMINI_API_KEY environment variable "
            "or pass api_key parameter."
        )
    
    return api_key


def optimize_image_for_gemini(img, max_dimension=2048, quality=85):
    """
    Optimize image for Gemini API by reducing size while maintaining readability.
    
    Gemini API limits:
    - Recommended: Images under 4MB each
    - Max dimensions: 3072x3072 pixels recommended
    
    Args:
        img: PIL Image object
        max_dimension: Maximum width or height in pixels (default: 2048)
        quality: JPEG quality for compression (default: 85)
    
    Returns:
        Optimized PIL Image object
    """
    # Make a copy to avoid modifying original
    img = img.copy()
    
    # Convert RGBA to RGB if needed (for JPEG compatibility)
    if img.mode == 'RGBA':
        # Create white background
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3] if len(img.split()) == 4 else None)
        img = background
    elif img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')
    
    # Resize if too large
    width, height = img.size
    if width > max_dimension or height > max_dimension:
        # Calculate new dimensions maintaining aspect ratio
        ratio = min(max_dimension / width, max_dimension / height)
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        print(f"  Resized image from {width}x{height} to {new_width}x{new_height}")
    
    return img


def process_receipts_with_gemini(image_paths, api_key=None, model=None):
    """
    Process receipt images using Gemini Flash 3 API.
    
    Args:
        image_paths: List of paths to receipt images
        api_key: Optional Gemini API key
        model: Optional Gemini model name (defaults to Settings/config)
        
    Returns:
        List of receipt dictionaries with 'id', 'file_id', 'amount', 'box', 'image'
    """
    api_key = configure_gemini(api_key)
    
    if model is None:
        model = get_gemini_model()
    
    # Initialize Gemini client
    client = genai.Client(api_key=api_key)
    
    # Prepare images for Gemini
    images_for_gemini = []
    image_objects = {}
    
    for idx, image_path in enumerate(image_paths):
        try:
            img = Image.open(image_path)
            # Store original image (full resolution)
            image_objects[f"receipts_{idx}"] = img.copy()
            
            # Optimize image for Gemini API (reduce size while maintaining readability)
            optimized_img = optimize_image_for_gemini(img)
            images_for_gemini.append(optimized_img)
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            continue
    
    if not images_for_gemini:
        print("No valid images to process.")
        return []
    
    # Construct the prompt
    prompt = """Analyze these images to find all receipts.

For every individual receipt found across these images:
1. Identify the 'file_id' it belongs to (receipts_0, receipts_1, etc., based on image order).
2. If an image has multiple receipts, assign a sub-index (e.g., receipts_0_1, receipts_0_2).
3. Extract the TOTAL amount as a number (just the number, no currency symbols).
4. Provide a 'box' which is the bounding box surrounding only that specific receipt, in the format [ymin, xmin, ymax, xmax]. Use a scale of 0 to 1000 where [0,0] is top-left and [1000,1000] is bottom-right.

Important:
- Look for the TOTAL, GRAND TOTAL, TOTAL DUE, AMOUNT DUE line on each receipt. Make sure that it's not CHANGE.
- Extract only the final amount to pay
- Be precise with bounding boxes to capture the entire receipt add some allowance for padding around the receipt if neccessary. It's better to slightly overestimate the bounding box than to cut off parts of the receipt.
- If a single image contains one receipt, use the format: receipts_0_0 (not just receipts_0)

Return ONLY a valid JSON array of objects, no other text:
[{"id": "receipts_0_1", "file_id": "receipts_0", "total": 15.50, "box": [100, 150, 400, 450]}]

If no receipts are found, return an empty array: []"""
    
    try:
        # Send to Gemini
        print(f"Sending {len(images_for_gemini)} image(s) to Gemini API...")
        
        # Create the content parts with prompt and images
        contents = [prompt]
        total_size = 0
        
        # Add images as parts - convert PIL images to bytes with JPEG compression
        for idx, img in enumerate(images_for_gemini):
            # Convert PIL Image to bytes using JPEG for smaller size
            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=85, optimize=True)
            img_bytes = img_byte_arr.getvalue()
            
            # Log size for debugging
            size_mb = len(img_bytes) / (1024 * 1024)
            total_size += len(img_bytes)
            print(f"  Image {idx+1}: {size_mb:.2f}MB")
            
            contents.append(types.Part.from_bytes(data=img_bytes, mime_type='image/jpeg'))
        
        total_size_mb = total_size / (1024 * 1024)
        print(f"  Total request size: {total_size_mb:.2f}MB")
        
        # Generate content using the new API
        response = client.models.generate_content(
            model=model,
            contents=contents
        )
        
        # Extract JSON from response
        response_text = response.text.strip()
        
        # Clean up response text (remove markdown code blocks if present)
        if response_text.startswith('```'):
            # Remove markdown code block
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text
            response_text = response_text.replace('```json', '').replace('```', '').strip()
        
        print(f"Gemini response: {response_text[:200]}...")
        
        # Parse JSON response
        receipts_data = json.loads(response_text)
        
        if not isinstance(receipts_data, list):
            print("Error: Gemini response is not a list")
            return []
        
        print(f"Found {len(receipts_data)} receipt(s)")
        
        # Process each receipt
        processed_receipts = []
        for receipt_data in receipts_data:
            try:
                receipt_id = receipt_data.get('id', '')
                file_id = receipt_data.get('file_id', '')
                total = float(receipt_data.get('total', 0))
                box = receipt_data.get('box', [0, 0, 1000, 1000])
                
                # Get the source image
                source_image = image_objects.get(file_id)
                if source_image is None:
                    print(f"Warning: Source image not found for {file_id}")
                    continue
                
                # Extract receipt region from image using bounding box
                receipt_image = extract_receipt_from_box(source_image, box)
                
                processed_receipts.append({
                    'id': receipt_id,
                    'file_id': file_id,
                    'amount': total,
                    'box': box,
                    'image': receipt_image,
                    'source': file_id,
                    'text': f"Receipt {receipt_id}, Total: {CURRENCY_SYMBOL}{total:.2f}"
                })
                
                print(f"  Processed receipt {receipt_id}: {CURRENCY_SYMBOL}{total:.2f}")
                
            except Exception as e:
                print(f"Error processing receipt data: {e}")
                continue
        
        return processed_receipts
        
    except json.JSONDecodeError as e:
        print(f"Error parsing Gemini response as JSON: {e}")
        print(f"Response was: {response_text}")
        return []
    except Exception as e:
        error_msg = str(e).lower()
        if 'rate' in error_msg or 'quota' in error_msg:
            print(f"⚠️ Gemini API rate limit exceeded: {e}")
            print("Tip: Wait a few moments or reduce the number of images.")
        elif 'too large' in error_msg or 'size' in error_msg:
            print(f"⚠️ Images too large for Gemini API: {e}")
            print("Tip: Try uploading fewer or smaller images.")
        elif '401' in error_msg or 'unauthorized' in error_msg or 'api key' in error_msg:
            print(f"⚠️ API Key error: {e}")
            print("Tip: Check that your GEMINI_API_KEY environment variable is set correctly.")
        else:
            print(f"Error calling Gemini API: {e}")
        return []


def extract_receipt_from_box(image, box):
    """
    Extract a receipt region from an image using bounding box coordinates.
    
    Args:
        image: PIL Image object
        box: Bounding box [ymin, xmin, ymax, xmax] in scale 0-1000
        
    Returns:
        PIL Image of the extracted receipt region
    """
    width, height = image.size
    
    # Convert from 0-1000 scale to pixel coordinates
    ymin, xmin, ymax, xmax = box
    
    # Convert to pixels
    left = int(xmin * width / 1000)
    top = int(ymin * height / 1000)
    right = int(xmax * width / 1000)
    bottom = int(ymax * height / 1000)
    
    # Ensure coordinates are within bounds
    left = max(0, min(left, width))
    right = max(0, min(right, width))
    top = max(0, min(top, height))
    bottom = max(0, min(bottom, height))
    
    # Ensure valid dimensions
    if right <= left or bottom <= top:
        print(f"Warning: Invalid bounding box {box}, using full image")
        return image
    
    # Crop the image
    try:
        cropped = image.crop((left, top, right, bottom))
        return cropped
    except Exception as e:
        print(f"Error cropping image: {e}")
        return image


def validate_receipt_data(receipt_data):
    """
    Validate that receipt data has all required fields.
    
    Args:
        receipt_data: Dictionary with receipt information
        
    Returns:
        Boolean indicating if data is valid
    """
    required_fields = ['id', 'file_id', 'total', 'box']
    
    for field in required_fields:
        if field not in receipt_data:
            return False
    
    # Validate total is a number
    try:
        float(receipt_data['total'])
    except (ValueError, TypeError):
        return False
    
    # Validate box is a list of 4 numbers
    box = receipt_data.get('box', [])
    if not isinstance(box, list) or len(box) != 4:
        return False
    
    try:
        [float(x) for x in box]
    except (ValueError, TypeError):
        return False
    
    return True


# Backwards compatibility functions
def detect_and_extract_receipts(image_path, api_key=None):
    """
    Backwards compatible function for single image processing.
    
    Args:
        image_path: Path to image file
        api_key: Optional Gemini API key
        
    Returns:
        List of receipt dictionaries
    """
    return process_receipts_with_gemini([image_path], api_key)


def extract_receipt_amounts(receipts):
    """
    Backwards compatible function - receipts already have amounts from Gemini.
    
    Args:
        receipts: List of receipt dictionaries
        
    Returns:
        Same list (amounts already extracted)
    """
    return receipts
