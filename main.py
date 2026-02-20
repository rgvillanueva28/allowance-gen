"""
Receipt Processing Application
Main entry point for the receipt processing system.
"""
import argparse
import os
from pathlib import Path
from dotenv import load_dotenv
from gemini_processor import process_receipts_with_gemini
from receipt_selector import select_receipts_by_target
from pdf_generator import generate_pdf_from_receipts

# Load environment variables from .env file
load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description='Process receipt images and generate a PDF with selected receipts.'
    )
    parser.add_argument(
        'images',
        nargs='+',
        help='Path(s) to receipt image files'
    )
    parser.add_argument(
        '-t', '--target',
        type=float,
        required=True,
        help='Target total amount for receipt selection'
    )
    parser.add_argument(
        '-o', '--output',
        default='selected_receipts.pdf',
        help='Output PDF filename (default: selected_receipts.pdf)'
    )
    parser.add_argument(
        '--output-dir',
        default='output',
        help='Directory for output files (default: output/)'
    )
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    receipts_dir = output_dir / 'selected_receipts'
    receipts_dir.mkdir(exist_ok=True)
    
    # Validate image files
    valid_images = []
    for image_path in args.images:
        if not os.path.exists(image_path):
            print(f"Warning: Image file '{image_path}' not found. Skipping.")
        else:
            valid_images.append(image_path)
    
    if not valid_images:
        print("No valid image files found. Exiting.")
        return
    
    print(f"Processing {len(valid_images)} image file(s)...")
    
    # Step 1: Process receipts using Gemini AI
    print("\n[Step 1/3] Analyzing receipts using Google Gemini AI...")
    print("  Detecting receipts and extracting amounts...")
    
    receipts_with_amounts = process_receipts_with_gemini(valid_images)
    
    if not receipts_with_amounts:
        print("No receipts found or processed. Exiting.")
        return
    
    print(f"\nSuccessfully processed {len(receipts_with_amounts)} receipt(s):")
    for i, receipt in enumerate(receipts_with_amounts, 1):
        print(f"  Receipt {i} ({receipt['id']}): ${receipt['amount']:.2f}")
    
    # Step 2: Select receipts based on target amount
    print(f"\n[Step 2/3] Selecting receipts to match target amount of ${args.target:.2f}...")
    selected_receipts = select_receipts_by_target(receipts_with_amounts, args.target)
    
    if not selected_receipts:
        print("No receipts selected. Unable to meet target amount.")
        return
    
    total_selected = sum(r['amount'] for r in selected_receipts)
    print(f"Selected {len(selected_receipts)} receipt(s) with total: ${total_selected:.2f}")
    
    # Step 3: Save selected receipt images and generate PDF
    print("\n[Step 3/3] Generating PDF with selected receipts...")
    saved_images = []
    for i, receipt in enumerate(selected_receipts, 1):
        image_path = receipts_dir / f"receipt_{i}.png"
        receipt['image'].save(str(image_path))
        saved_images.append(str(image_path))
        print(f"  Saved receipt {i} to {image_path}")
    
    # Generate PDF
    output_pdf = output_dir / args.output
    generate_pdf_from_receipts(selected_receipts, str(output_pdf))
    
    print(f"\n✓ Successfully generated PDF: {output_pdf}")
    print(f"✓ Selected receipts saved to: {receipts_dir}")
    print(f"\nSummary:")
    print(f"  Total receipts found: {len(receipts_with_amounts)}")
    print(f"  Receipts selected: {len(selected_receipts)}")
    print(f"  Target amount: ${args.target:.2f}")
    print(f"  Selected total: ${total_selected:.2f}")
    print(f"  Difference: ${abs(args.target - total_selected):.2f}")


if __name__ == '__main__':
    main()
