"""
Example/Test script for the receipt processing application.
This demonstrates how to use the modules programmatically.
"""
from pathlib import Path
from gemini_processor import process_receipts_with_gemini
from receipt_selector import select_receipts_by_target
from pdf_generator import generate_pdf_from_receipts


def example_basic_usage():
    """
    Example of basic usage - processing a single image.
    """
    print("=== Example 1: Basic Usage ===\n")
    
    # Check if example image exists
    image_path = "example_receipt.jpg"
    if not Path(image_path).exists():
        print(f"Note: Example image '{image_path}' not found.")
        print("Place a receipt image in the project directory to run this example.\n")
        return
    
    # Process receipts with Gemini AI
    print("Processing receipt with Gemini AI...")
    receipts_with_amounts = process_receipts_with_gemini([image_path])
    
    if not receipts_with_amounts:
        print("No receipts found or processed.\n")
        return
    
    print(f"Processed {len(receipts_with_amounts)} receipt(s)")
    for i, r in enumerate(receipts_with_amounts, 1):
        print(f"  Receipt {i}: ${r['amount']:.2f}")
    print()
    
    # Select receipts for target amount
    target = 50.00
    selected = select_receipts_by_target(receipts_with_amounts, target)
    total = sum(r['amount'] for r in selected)
    print(f"Selected {len(selected)} receipt(s) for target ${target:.2f}")
    print(f"Total selected: ${total:.2f}\n")
    
    # Generate PDF
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    pdf_path = output_dir / "example_output.pdf"
    generate_pdf_from_receipts(selected, str(pdf_path))
    print(f"Generated PDF: {pdf_path}\n")


def example_multiple_images():
    """
    Example of processing multiple images.
    """
    print("=== Example 2: Multiple Images ===\n")
    
    image_paths = ["receipt1.jpg", "receipt2.jpg", "receipt3.jpg"]
    available_images = [p for p in image_paths if Path(p).exists()]
    
    if not available_images:
        print(f"Note: No example images found.")
        print("Place receipt images (receipt1.jpg, receipt2.jpg, etc.) in the project directory.\n")
        return
    
    # Process all images at once with Gemini
    print(f"Processing {len(available_images)} images with Gemini AI...")
    receipts_with_amounts = process_receipts_with_gemini(available_images)
    
    print(f"Successfully processed {len(receipts_with_amounts)} receipt(s)")
    
    for i, r in enumerate(receipts_with_amounts, 1):
        print(f"  Receipt {i} ({r['id']}): ${r['amount']:.2f}")
    print()


def example_programmatic_selection():
    """
    Example of using different selection strategies.
    """
    print("=== Example 3: Selection Strategies ===\n")
    
    # Create mock receipts for demonstration
    from PIL import Image
    mock_receipts = [
        {'amount': 15.99, 'image': Image.new('RGB', (100, 100)), 'source': 'mock1'},
        {'amount': 23.45, 'image': Image.new('RGB', (100, 100)), 'source': 'mock2'},
        {'amount': 8.50, 'image': Image.new('RGB', (100, 100)), 'source': 'mock3'},
        {'amount': 42.00, 'image': Image.new('RGB', (100, 100)), 'source': 'mock4'},
        {'amount': 12.75, 'image': Image.new('RGB', (100, 100)), 'source': 'mock5'},
    ]
    
    targets = [50.00, 30.00, 75.00]
    
    for target in targets:
        selected = select_receipts_by_target(mock_receipts, target)
        total = sum(r['amount'] for r in selected)
        print(f"Target: ${target:.2f}")
        print(f"  Selected: {len(selected)} receipt(s), Total: ${total:.2f}")
        print(f"  Difference: ${abs(target - total):.2f}\n")


def example_custom_pdf():
    """
    Example of generating a custom PDF.
    """
    print("=== Example 4: Custom PDF Generation ===\n")
    
    from PIL import Image, ImageDraw, ImageFont
    
    # Create sample receipt images with text
    receipts = []
    amounts = [12.50, 25.99, 8.75]
    
    for i, amount in enumerate(amounts, 1):
        # Create a simple receipt image
        img = Image.new('RGB', (400, 600), 'white')
        draw = ImageDraw.Draw(img)
        
        # Draw some text
        draw.text((20, 20), f"RECEIPT #{i}", fill='black')
        draw.text((20, 500), f"TOTAL: ${amount:.2f}", fill='black')
        
        receipts.append({
            'amount': amount,
            'image': img,
            'source': f'sample_{i}.jpg',
            'index': i-1
        })
    
    # Generate PDF
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    pdf_path = output_dir / "custom_example.pdf"
    
    generate_pdf_from_receipts(receipts, str(pdf_path))
    print(f"Generated custom PDF: {pdf_path}")
    print(f"Contains {len(receipts)} receipt(s) with total ${sum(r['amount'] for r in receipts):.2f}\n")


def main():
    """
    Run all examples.
    """
    print("Receipt Processing Application - Examples\n")
    print("=" * 60)
    print()
    
    try:
        example_basic_usage()
    except Exception as e:
        print(f"Example 1 error: {e}\n")
    
    try:
        example_multiple_images()
    except Exception as e:
        print(f"Example 2 error: {e}\n")
    
    try:
        example_programmatic_selection()
    except Exception as e:
        print(f"Example 3 error: {e}\n")
    
    try:
        example_custom_pdf()
    except Exception as e:
        print(f"Example 4 error: {e}\n")
    
    print("=" * 60)
    print("\nExamples completed!")
    print("\nTo run the main application:")
    print("  python main.py <image_files> -t <target_amount>")


if __name__ == '__main__':
    main()
