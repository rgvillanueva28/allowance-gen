"""
PDF Generation Module
Generates PDF documents from selected receipts.
"""
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from datetime import datetime
from PIL import Image
import io
from config import CURRENCY_SYMBOL


def generate_pdf_from_receipts(receipts, output_path, page_size=letter):
    """
    Generate a PDF document containing selected receipts.
    All pages are portrait orientation. Rotations should be applied to images before calling this function.
    
    Args:
        receipts: List of receipt dictionaries with 'image' and 'amount' keys
        output_path: Path where the PDF should be saved
        page_size: Page size tuple (default: letter)
    """
    # Create PDF canvas - always use portrait orientation
    c = canvas.Canvas(output_path, pagesize=page_size)
    page_width, page_height = page_size
    
    # Set minimal margins
    margin = 0.25 * inch
    usable_width = page_width - (2 * margin)
    usable_height = page_height - (2 * margin)
    
    # Add each receipt on a separate page (no title or summary pages)
    for idx, receipt in enumerate(receipts, 1):
        # Get the receipt image
        img = receipt['image'].copy()
        
        # Convert to RGB if needed (for JPEG compatibility)
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = img.convert('RGB')
            img = rgb_img
        
        add_receipt_to_pdf(
            c, img, idx,
            page_width, page_height,
            margin, usable_width, usable_height
        )
        c.showPage()
    
    # Save PDF
    c.save()


def add_title_page(c, receipts, page_width, page_height, margin):
    """Add a title page to the PDF."""
    # Title
    c.setFont("Helvetica-Bold", 24)
    title = "Receipt Compilation"
    title_width = c.stringWidth(title, "Helvetica-Bold", 24)
    c.drawString((page_width - title_width) / 2, page_height - margin - 1*inch, title)
    
    # Date
    c.setFont("Helvetica", 12)
    date_str = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    date_width = c.stringWidth(date_str, "Helvetica", 12)
    c.drawString((page_width - date_width) / 2, page_height - margin - 1.5*inch, date_str)
    
    # Summary info
    total_amount = sum(r['amount'] for r in receipts)
    y_pos = page_height - margin - 2.5*inch
    
    c.setFont("Helvetica", 14)
    info_lines = [
        f"Total Receipts: {len(receipts)}",
        f"Total Amount: {CURRENCY_SYMBOL}{total_amount:.2f}",
    ]
    
    for line in info_lines:
        line_width = c.stringWidth(line, "Helvetica", 14)
        c.drawString((page_width - line_width) / 2, y_pos, line)
        y_pos -= 0.3 * inch


def add_receipt_to_pdf(c, img, receipt_num, page_width, page_height, margin, usable_width, usable_height):
    """Add a single receipt to the PDF - image only, no text."""
    # Get image dimensions
    img_width, img_height = img.size
    
    # Optimize image size to reduce PDF file size
    # Target max dimension of 2400px (suitable for 8x10 at 300 DPI)
    max_dimension = 2400
    if max(img_width, img_height) > max_dimension:
        scale_factor = max_dimension / max(img_width, img_height)
        new_width = int(img_width * scale_factor)
        new_height = int(img_height * scale_factor)
        img = img.resize((new_width, new_height), Image.LANCZOS)
        img_width, img_height = img.size
    
    # Calculate aspect ratios
    img_aspect = img_height / img_width
    page_aspect = usable_height / usable_width
    
    # Scale image to fit the full page while maintaining aspect ratio
    if img_aspect > page_aspect:
        # Image is taller relative to its width than the page
        # Fit to height
        display_height = usable_height
        display_width = display_height / img_aspect
    else:
        # Image is wider relative to its height than the page
        # Fit to width
        display_width = usable_width
        display_height = display_width * img_aspect
    
    # Center the image on the page
    x_pos = (page_width - display_width) / 2
    y_pos = (page_height - display_height) / 2
    
    # Draw the image
    # Convert PIL image to ImageReader with JPEG compression
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='JPEG', quality=85, optimize=True)
    img_buffer.seek(0)
    img_reader = ImageReader(img_buffer)
    
    c.drawImage(img_reader, x_pos, y_pos, display_width, display_height)
    
    # Add 1px black border around the image
    c.setStrokeColorRGB(0, 0, 0)  # Black color
    c.setLineWidth(1)  # 1px width
    c.rect(x_pos, y_pos, display_width, display_height, stroke=1, fill=0)


def add_summary_page(c, receipts, page_width, page_height, margin):
    """Add a summary page at the end of the PDF."""
    # Title
    c.setFont("Helvetica-Bold", 18)
    title = "Summary"
    c.drawString(margin, page_height - margin - 0.5*inch, title)
    
    # Table header
    y_pos = page_height - margin - 1*inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y_pos, "No.")
    c.drawString(margin + 0.5*inch, y_pos, "Source")
    c.drawString(margin + 4*inch, y_pos, "Amount")
    
    # Draw line under header
    y_pos -= 0.15*inch
    c.line(margin, y_pos, page_width - margin, y_pos)
    
    # Table content
    y_pos -= 0.25*inch
    c.setFont("Helvetica", 10)
    
    total = 0
    for idx, receipt in enumerate(receipts, 1):
        if y_pos < margin + 1*inch:
            # Start new page if running out of space
            c.showPage()
            y_pos = page_height - margin - 0.5*inch
            c.setFont("Helvetica", 10)
        
        c.drawString(margin, y_pos, str(idx))
        
        # Truncate source path if too long
        source = receipt['source']
        if len(source) > 45:
            source = "..." + source[-42:]
        c.drawString(margin + 0.5*inch, y_pos, source)
        
        amount_str = f"{CURRENCY_SYMBOL}{receipt['amount']:.2f}"
        c.drawString(margin + 4*inch, y_pos, amount_str)
        
        total += receipt['amount']
        y_pos -= 0.25*inch
    
    # Draw line before total
    y_pos -= 0.1*inch
    c.line(margin, y_pos, page_width - margin, y_pos)
    
    # Total
    y_pos -= 0.3*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin + 3.2*inch, y_pos, "Total:")
    c.drawString(margin + 4*inch, y_pos, f"{CURRENCY_SYMBOL}{total:.2f}")
