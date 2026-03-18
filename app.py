"""
Web Application for Receipt Processing
Flask-based web interface for uploading and processing receipts.
"""
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session, jsonify
from werkzeug.utils import secure_filename
import os
import uuid
from pathlib import Path
from datetime import datetime
import shutil
import json
from PIL import Image
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from gemini_processor import process_receipts_with_gemini
from receipt_selector import select_receipts_by_target
from pdf_generator import generate_pdf_from_receipts
from config import CURRENCY_SYMBOL, MAX_OVERAGE_ALLOWED


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration
UPLOAD_FOLDER = Path('uploads')
OUTPUT_FOLDER = Path('web_output')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB (increased for multiple high-res images)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create necessary directories
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_job_metadata(job_id, metadata):
    """Save job metadata to JSON file for persistence."""
    try:
        metadata_path = OUTPUT_FOLDER / job_id / 'metadata.json'
        metadata['saved_at'] = datetime.now().isoformat()
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        print(f"Error saving metadata: {e}")


def load_job_metadata(job_id):
    """Load job metadata from JSON file."""
    try:
        metadata_path = OUTPUT_FOLDER / job_id / 'metadata.json'
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading metadata: {e}")
    return None


def get_all_jobs():
    """Get list of all saved jobs with metadata."""
    jobs = []
    try:
        for job_dir in OUTPUT_FOLDER.iterdir():
            if job_dir.is_dir():
                metadata = load_job_metadata(job_dir.name)
                if metadata:
                    metadata['job_id'] = job_dir.name
                    jobs.append(metadata)
        # Sort by saved_at timestamp, newest first
        jobs.sort(key=lambda x: x.get('saved_at', ''), reverse=True)
    except Exception as e:
        print(f"Error getting jobs: {e}")
    return jobs


def cleanup_old_files(directory, max_age_hours=24):
    """Remove files older than max_age_hours from directory."""
    try:
        now = datetime.now()
        for item in Path(directory).iterdir():
            if item.is_file():
                age_hours = (now - datetime.fromtimestamp(item.stat().st_mtime)).total_seconds() / 3600
                if age_hours > max_age_hours:
                    item.unlink()
            elif item.is_dir():
                # Check metadata for saved jobs - don't auto-delete saved jobs
                metadata = load_job_metadata(item.name)
                if not metadata:  # Only delete if no metadata (not a saved job)
                    age_hours = (now - datetime.fromtimestamp(item.stat().st_mtime)).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        shutil.rmtree(item)
    except Exception as e:
        print(f"Cleanup error: {e}")


@app.route('/')
def index():
    """Render the main upload page."""
    # Cleanup old files on each page load
    cleanup_old_files(UPLOAD_FOLDER)
    cleanup_old_files(OUTPUT_FOLDER)
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file upload and receipt processing."""
    try:
        # Validate target amount
        target_amount = request.form.get('target_amount')
        if not target_amount:
            flash('Please enter a target amount.', 'error')
            return redirect(url_for('index'))
        
        try:
            target_amount = float(target_amount)
            if target_amount <= 0:
                flash('Target amount must be positive.', 'error')
                return redirect(url_for('index'))
        except ValueError:
            flash('Invalid target amount.', 'error')
            return redirect(url_for('index'))
        
        # Check if files were uploaded
        if 'files[]' not in request.files:
            flash('No files uploaded.', 'error')
            return redirect(url_for('index'))
        
        files = request.files.getlist('files[]')
        if not files or files[0].filename == '':
            flash('No files selected.', 'error')
            return redirect(url_for('index'))
        
        # Create unique session ID for this processing job
        job_id = str(uuid.uuid4())
        job_folder = UPLOAD_FOLDER / job_id
        job_folder.mkdir(exist_ok=True)
        
        # Save uploaded files
        uploaded_paths = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = job_folder / filename
                file.save(filepath)
                uploaded_paths.append(str(filepath))
            else:
                flash(f'File {file.filename} has invalid extension.', 'warning')
        
        if not uploaded_paths:
            flash('No valid image files uploaded.', 'error')
            return redirect(url_for('index'))
        
        # Process receipts with Gemini AI
        print(f"\n[Job {job_id}] Processing {len(uploaded_paths)} file(s) with Gemini AI...")
        
        # Process all images at once with Gemini
        receipts_with_amounts = process_receipts_with_gemini(uploaded_paths)
        print(f"[Job {job_id}] Processed {len(receipts_with_amounts)} receipt(s)")
        
        # Create a mapping of file_id to uploaded file path for originals
        file_id_to_path = {}
        for idx, path in enumerate(uploaded_paths):
            file_id_to_path[f"receipts_{idx}"] = path
        
        if not receipts_with_amounts:
            flash('No receipts detected or amounts could not be extracted.', 'error')
            return redirect(url_for('index'))
        
        # Generate PDF
        output_dir = OUTPUT_FOLDER / job_id
        output_dir.mkdir(exist_ok=True)
        
        receipts_dir = output_dir / 'receipts'
        receipts_dir.mkdir(exist_ok=True)
        
        # Create originals directory to preserve source images
        originals_dir = output_dir / 'originals'
        originals_dir.mkdir(exist_ok=True)
        
        # Save ALL receipt images (not just selected ones)
        all_receipt_data = []
        for i, receipt in enumerate(receipts_with_amounts, 1):
            # Get the cropped receipt image from Gemini AI
            img = receipt['image']
            
            # Auto-rotate landscape images to portrait for PDF
            img_width, img_height = img.size
            if img_width > img_height:
                # Image is landscape, rotate 90 degrees counter-clockwise to portrait
                img = img.rotate(90, expand=True)
                print(f"[Job {job_id}] Auto-rotated receipt_{i} from landscape to portrait")
            
            # Save display version (cropped and rotated receipt)
            image_path = receipts_dir / f"receipt_{i}.png"
            img.save(str(image_path))
            
            # Update the receipt image in the list for PDF generation
            receipt['image'] = img
            
            # Save ORIGINAL uploaded image (before AI cropping) to originals folder
            file_id = receipt.get('file_id', f"receipts_0")
            original_upload_path = file_id_to_path.get(file_id)
            if original_upload_path:
                # Copy the actual uploaded image file (unmodified)
                original_path = originals_dir / f"receipt_{i}.png"
                original_img = Image.open(original_upload_path)
                original_img.save(str(original_path))
            
            all_receipt_data.append({
                'filename': f"receipt_{i}.png",
                'amount': receipt['amount'],
                'id': receipt.get('id', f'receipt_{i}'),
                'box': receipt.get('box', [0, 0, 1000, 1000]),  # Store original bounding box
                'file_id': receipt.get('file_id', 'receipts_0')
            })
        
        # Now select optimal receipts based on target amount
        selected_receipts = select_receipts_by_target(receipts_with_amounts, target_amount)
        
        if not selected_receipts:
            flash('Could not select receipts to match target amount.', 'warning')
            return redirect(url_for('index'))
        
        # Find indices of selected receipts in the all_receipts array
        selected_indices = []
        for selected in selected_receipts:
            for i, receipt in enumerate(receipts_with_amounts):
                if (receipt['amount'] == selected['amount'] and 
                    receipt.get('id') == selected.get('id') and
                    i not in selected_indices):  # Avoid duplicates
                    selected_indices.append(i)
                    break
        
        total_selected = sum(r['amount'] for r in selected_receipts)
        print(f"[Job {job_id}] Detected {len(receipts_with_amounts)} receipt(s)")
        print(f"[Job {job_id}] Selected {len(selected_receipts)} receipt(s), total: {CURRENCY_SYMBOL}{total_selected:.2f}")
        print(f"[Job {job_id}] Selected indices: {selected_indices}")
        
        # Generate PDF with selected receipts only
        pdf_receipts = [receipts_with_amounts[i] for i in selected_indices]
        pdf_path = output_dir / 'selected_receipts.pdf'
        generate_pdf_from_receipts(pdf_receipts, str(pdf_path))
        
        # Store job info in session
        session['job_id'] = job_id
        session['total_receipts'] = len(receipts_with_amounts)
        session['selected_count'] = len(selected_receipts)
        session['target_amount'] = target_amount
        session['selected_total'] = total_selected
        session['pdf_path'] = str(pdf_path)
        session['receipt_data'] = all_receipt_data  # Store ALL receipts
        session['selected_indices'] = selected_indices  # Store which are selected
        
        # Save job metadata for persistence
        metadata = {
            'created_at': datetime.now().isoformat(),
            'total_receipts': len(receipts_with_amounts),
            'selected_count': len(selected_receipts),
            'target_amount': float(target_amount),
            'selected_total': float(total_selected),
            'receipt_data': all_receipt_data,  # Store ALL receipts
            'selected_indices': selected_indices,  # Store selection
            'pdf_path': str(pdf_path),
            'status': 'completed'
        }
        save_job_metadata(job_id, metadata)
        
        return redirect(url_for('results'))
        
    except Exception as e:
        print(f"Error processing receipts: {e}")
        flash(f'Error processing receipts: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/results')
def results():
    """Display processing results."""
    job_id = session.get('job_id')
    if not job_id:
        flash('No processing results available.', 'warning')
        return redirect(url_for('index'))
    
    return render_template(
        'results.html',
        total_receipts=session.get('total_receipts', 0),
        selected_count=session.get('selected_count', 0),
        target_amount=session.get('target_amount', 0),
        selected_total=session.get('selected_total', 0),
        difference=abs(session.get('target_amount', 0) - session.get('selected_total', 0))
    )


@app.route('/download')
def download():
    """Download the generated PDF."""
    pdf_path = session.get('pdf_path')
    if not pdf_path or not Path(pdf_path).exists():
        flash('PDF file not found.', 'error')
        return redirect(url_for('index'))
    
    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=f'receipts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
        mimetype='application/pdf'
    )


@app.route('/view-images')
def view_images():
    """View individual receipt images."""
    job_id = session.get('job_id')
    if not job_id:
        flash('No images available.', 'warning')
        return redirect(url_for('index'))
    
    receipts_dir = OUTPUT_FOLDER / job_id / 'receipts'
    if not receipts_dir.exists():
        flash('Receipt images not found.', 'error')
        return redirect(url_for('results'))
    
    # Get ALL receipt data from session
    receipt_data = session.get('receipt_data', [])
    selected_indices = session.get('selected_indices', list(range(len(receipt_data))))
    target_amount = session.get('target_amount', 0)
    
    # Calculate selected total from selected indices
    selected_total = sum(receipt_data[i]['amount'] for i in selected_indices if i < len(receipt_data))
    
    return render_template(
        'images.html',
        receipts=receipt_data,  # ALL receipts
        selected_indices=selected_indices,  # Which are selected
        job_id=job_id,
        target_amount=target_amount,
        selected_total=selected_total
    )


@app.route('/update-amount', methods=['POST'])
def update_amount():
    """Update the amount for a specific receipt."""
    try:
        data = request.json
        receipt_index = int(data.get('index'))
        new_amount = float(data.get('amount'))
        
        if new_amount < 0:
            return jsonify({'success': False, 'error': 'Amount must be positive'})
        
        job_id = session.get('job_id')
        if not job_id:
            return jsonify({'success': False, 'error': 'Session expired'})
        
        # Update receipt data in session
        receipt_data = session.get('receipt_data', [])
        if receipt_index < 0 or receipt_index >= len(receipt_data):
            return jsonify({'success': False, 'error': 'Invalid receipt index'})
        
        old_amount = receipt_data[receipt_index]['amount']
        receipt_data[receipt_index]['amount'] = new_amount
        session['receipt_data'] = receipt_data
        
        # Update totals
        new_total = sum(r['amount'] for r in receipt_data)
        session['selected_total'] = new_total
        
        # Update metadata
        metadata = load_job_metadata(job_id)
        if metadata:
            metadata['selected_total'] = new_total
            metadata['receipt_data'] = receipt_data
            metadata['last_modified'] = datetime.now().isoformat()
            save_job_metadata(job_id, metadata)
        
        print(f"[Job {job_id}] Updated receipt {receipt_index}: {CURRENCY_SYMBOL}{old_amount:.2f} → {CURRENCY_SYMBOL}{new_amount:.2f}")
        
        return jsonify({
            'success': True,
            'new_total': new_total,
            'target_amount': session.get('target_amount', 0)
        })
    
    except Exception as e:
        print(f"Error updating amount: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/add-manual-receipt', methods=['POST'])
def add_manual_receipt():
    """Manually add a receipt without AI processing."""
    try:
        job_id = session.get('job_id')
        if not job_id:
            return jsonify({'success': False, 'error': 'Session expired'})
        
        # Get uploaded file and amount
        if 'receipt_image' not in request.files:
            return jsonify({'success': False, 'error': 'No image provided'})
        
        file = request.files['receipt_image']
        amount = float(request.form.get('amount', 0))
        
        if amount <= 0:
            return jsonify({'success': False, 'error': 'Amount must be positive'})
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type'})
        
        # Get current receipt data
        receipt_data = session.get('receipt_data', [])
        next_num = len(receipt_data) + 1
        
        # Save the image
        job_folder = OUTPUT_FOLDER / job_id
        receipts_dir = job_folder / 'receipts'
        originals_dir = job_folder / 'originals'
        receipts_dir.mkdir(exist_ok=True)
        originals_dir.mkdir(exist_ok=True)
        
        filename = f"receipt_{next_num}.png"
        
        # Save uploaded image
        img = Image.open(file)
        
        # Auto-rotate landscape images to portrait for PDF
        img_width, img_height = img.size
        if img_width > img_height:
            # Image is landscape, rotate 90 degrees counter-clockwise to portrait
            img = img.rotate(90, expand=True)
            print(f"[Job {job_id}] Auto-rotated manual receipt_{next_num} from landscape to portrait")
        
        # Save to receipts folder (rotated if needed)
        receipt_path = receipts_dir / filename
        img.save(str(receipt_path))
        
        # Save to originals folder (also rotated for consistency)
        original_path = originals_dir / filename
        img.save(str(original_path))
        
        # Add to receipt data
        new_receipt = {
            'filename': filename,
            'amount': amount,
            'id': f'manual_{next_num}',
            'box': [0, 0, 1000, 1000],
            'file_id': f'manual_{next_num}'
        }
        receipt_data.append(new_receipt)
        
        # Update session
        session['receipt_data'] = receipt_data
        session['selected_count'] = len(receipt_data)
        new_total = sum(r['amount'] for r in receipt_data)
        session['selected_total'] = new_total
        
        # Update metadata
        metadata = load_job_metadata(job_id)
        if metadata:
            metadata['selected_count'] = len(receipt_data)
            metadata['selected_total'] = new_total
            metadata['receipt_data'] = receipt_data
            metadata['last_modified'] = datetime.now().isoformat()
            save_job_metadata(job_id, metadata)
        
        print(f"[Job {job_id}] Manually added receipt: {CURRENCY_SYMBOL}{amount:.2f}")
        
        return jsonify({
            'success': True,
            'receipt': new_receipt,
            'new_total': new_total,
            'new_count': len(receipt_data)
        })
    
    except Exception as e:
        print(f"Error adding manual receipt: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/regenerate-pdf', methods=['POST'])
def regenerate_pdf():
    """Regenerate PDF with current receipt data (after amount edits or additions)."""
    try:
        job_id = session.get('job_id')
        if not job_id:
            return jsonify({'success': False, 'error': 'Session expired'})
        
        # Get selected indices from request (if provided), otherwise use session
        data = request.get_json() or {}
        selected_indices = data.get('selected_indices')
        
        # Get current receipt data from session
        receipt_data = session.get('receipt_data', [])
        
        if not receipt_data:
            return jsonify({'success': False, 'error': 'No receipts found'})
        
        # If selected_indices not provided in request, use session default
        if selected_indices is None:
            selected_indices = session.get('selected_indices', list(range(len(receipt_data))))
        
        if not selected_indices or len(selected_indices) == 0:
            return jsonify({'success': False, 'error': 'No receipts selected'})
        
        # Load images for SELECTED receipts only
        receipts_dir = OUTPUT_FOLDER / job_id / 'receipts'
        processed_receipts = []
        
        for idx in selected_indices:
            if 0 <= idx < len(receipt_data):
                receipt_info = receipt_data[idx]
                image_path = receipts_dir / receipt_info['filename']
                
                if not image_path.exists():
                    continue
                
                img = Image.open(image_path)
                processed_receipts.append({
                    'image': img,
                    'amount': receipt_info['amount'],
                    'id': receipt_info['id'],
                    'source': receipt_info.get('id', receipt_info['filename'])
                })
        
        if not processed_receipts:
            return jsonify({'success': False, 'error': 'No valid receipt images found'})
        
        # Calculate selected total
        selected_total = sum(r['amount'] for r in processed_receipts)
        
        # Generate PDF with selected receipts
        pdf_path = OUTPUT_FOLDER / job_id / 'selected_receipts.pdf'
        generate_pdf_from_receipts(processed_receipts, str(pdf_path))
        
        # Update session with new selection
        session['pdf_path'] = str(pdf_path)
        session['selected_indices'] = selected_indices
        session['selected_count'] = len(processed_receipts)
        session['selected_total'] = selected_total
        
        # Update metadata with new selection
        metadata = load_job_metadata(job_id)
        if metadata:
            metadata['last_modified'] = datetime.now().isoformat()
            metadata['pdf_regenerated'] = True
            metadata['selected_indices'] = selected_indices
            metadata['selected_count'] = len(processed_receipts)
            metadata['selected_total'] = selected_total
            save_job_metadata(job_id, metadata)
        
        print(f"[Job {job_id}] PDF regenerated with {len(processed_receipts)} selected receipts, total: {CURRENCY_SYMBOL}{selected_total:.2f}")
        
        return jsonify({
            'success': True,
            'selected_count': len(processed_receipts),
            'selected_total': selected_total
        })
    
    except Exception as e:
        print(f"Error regenerating PDF: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/recompute-selection', methods=['POST'])
def recompute_selection():
    """Recompute optimal receipt selection from a subset of receipts."""
    try:
        job_id = session.get('job_id')
        if not job_id:
            return jsonify({'success': False, 'error': 'Session expired'})
        
        data = request.get_json()
        selected_indices = data.get('selected_indices', [])
        
        if not selected_indices:
            return jsonify({'success': False, 'error': 'No receipts selected'})
        
        # Get all receipts from session
        all_receipts = session.get('receipt_data', [])
        target_amount = session.get('target_amount', 0)
        
        if not all_receipts:
            return jsonify({'success': False, 'error': 'No receipts found'})
        
        # Filter to only selected receipts
        available_receipts = []
        for idx in selected_indices:
            if 0 <= idx < len(all_receipts):
                receipt = all_receipts[idx].copy()
                receipt['original_index'] = idx
                available_receipts.append(receipt)
        
        print(f"[Job {job_id}] Recomputing selection from {len(available_receipts)} available receipts")
        print(f"[Job {job_id}] Selected indices from user: {selected_indices}")
        print(f"[Job {job_id}] Available receipts amounts: {[r['amount'] for r in available_receipts]}")
        print(f"[Job {job_id}] Target amount: {CURRENCY_SYMBOL}{target_amount}")
        
        # Run selection algorithm on the available receipts
        from receipt_selector import select_receipts_by_target
        from config import MAX_OVERAGE_ALLOWED
        
        selected_receipts = select_receipts_by_target(
            available_receipts, 
            target_amount,
            max_overage=MAX_OVERAGE_ALLOWED
        )
        
        # Get original indices of selected receipts
        optimal_indices = [r['original_index'] for r in selected_receipts]
        selected_total = sum(r['amount'] for r in selected_receipts)
        
        print(f"[Job {job_id}] Optimal selection: {len(selected_receipts)} receipts, total: {CURRENCY_SYMBOL}{selected_total:.2f}")
        print(f"[Job {job_id}] Optimal indices: {optimal_indices}")
        
        # Update session with new selection
        session['selected_indices'] = optimal_indices
        session['selected_count'] = len(optimal_indices)
        session['selected_total'] = selected_total
        
        # Regenerate PDF with new selection
        receipts_dir = OUTPUT_FOLDER / job_id / 'receipts'
        processed_receipts = []
        
        for idx in optimal_indices:
            if 0 <= idx < len(all_receipts):
                receipt_info = all_receipts[idx]
                image_path = receipts_dir / receipt_info['filename']
                
                if image_path.exists():
                    img = Image.open(image_path)
                    processed_receipts.append({
                        'image': img,
                        'amount': receipt_info['amount'],
                        'id': receipt_info['id'],
                        'source': receipt_info.get('id', receipt_info['filename'])
                    })
        
        # Generate PDF with new selection
        if processed_receipts:
            pdf_path = OUTPUT_FOLDER / job_id / 'selected_receipts.pdf'
            generate_pdf_from_receipts(processed_receipts, str(pdf_path))
            session['pdf_path'] = str(pdf_path)
            print(f"[Job {job_id}] PDF regenerated with {len(processed_receipts)} receipts")
        
        # Update metadata
        metadata = load_job_metadata(job_id)
        if metadata:
            metadata['selected_indices'] = optimal_indices
            metadata['selected_count'] = len(optimal_indices)
            metadata['selected_total'] = selected_total
            metadata['last_recomputed'] = datetime.now().isoformat()
            metadata['pdf_regenerated'] = True
            save_job_metadata(job_id, metadata)
        
        return jsonify({
            'success': True,
            'selected_indices': optimal_indices,
            'selected_count': len(optimal_indices),
            'selected_total': selected_total,
            'target_amount': target_amount
        })
    
    except Exception as e:
        print(f"Error recomputing selection: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/remove-receipt', methods=['POST'])
def remove_receipt():
    """Permanently remove a receipt from the job."""
    try:
        job_id = session.get('job_id')
        if not job_id:
            return jsonify({'success': False, 'error': 'Session expired'})
        
        data = request.get_json()
        index = data.get('index')
        
        if index is None or index < 0:
            return jsonify({'success': False, 'error': 'Invalid receipt index'})
        
        # Get receipts from session
        receipt_data = session.get('receipt_data', [])
        
        if index >= len(receipt_data):
            return jsonify({'success': False, 'error': 'Receipt not found'})
        
        # Get receipt to remove
        receipt_to_remove = receipt_data[index]
        
        # Delete image files
        receipts_dir = OUTPUT_FOLDER / job_id / 'receipts'
        originals_dir = OUTPUT_FOLDER / job_id / 'originals'
        
        receipt_file = receipts_dir / receipt_to_remove['filename']
        if receipt_file.exists():
            receipt_file.unlink()
        
        # Try to remove original if it exists
        original_file = originals_dir / receipt_to_remove['filename']
        if original_file.exists():
            original_file.unlink()
        
        # Remove from session
        receipt_data.pop(index)
        session['receipt_data'] = receipt_data
        
        # Update selected_indices: remove the deleted index and shift down indices > deleted index
        selected_indices = session.get('selected_indices', [])
        updated_indices = []
        for idx in selected_indices:
            if idx < index:
                updated_indices.append(idx)  # Keep as is
            elif idx > index:
                updated_indices.append(idx - 1)  # Shift down
            # if idx == index, we skip it (removed)
        
        session['selected_indices'] = updated_indices
        
        # Update metadata
        metadata = load_job_metadata(job_id)
        if metadata:
            metadata['receipt_count'] = len(receipt_data)
            metadata['receipt_data'] = receipt_data
            metadata['selected_indices'] = updated_indices
            metadata['selected_count'] = len(updated_indices)
            metadata['last_modified'] = datetime.now().isoformat()
            save_job_metadata(job_id, metadata)
        
        print(f"[Job {job_id}] Receipt {receipt_to_remove['id']} removed. {len(receipt_data)} receipts remaining")
        
        return jsonify({
            'success': True,
            'remaining_count': len(receipt_data)
        })
    
    except Exception as e:
        print(f"Error removing receipt: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/image/<job_id>/<filename>')
def get_image(job_id, filename):
    """Serve a receipt image."""
    image_path = OUTPUT_FOLDER / job_id / 'receipts' / secure_filename(filename)
    if not image_path.exists():
        flash('Image not found.', 'error')
        return redirect(url_for('index'))
    
    return send_file(image_path, mimetype='image/png')


@app.route('/original-image/<job_id>/<filename>')
def get_original_image(job_id, filename):
    """Serve an original (uncropped) receipt image."""
    image_path = OUTPUT_FOLDER / job_id / 'originals' / secure_filename(filename)
    if not image_path.exists():
        # Fallback to regular receipt if original doesn't exist
        image_path = OUTPUT_FOLDER / job_id / 'receipts' / secure_filename(filename)
        if not image_path.exists():
            flash('Image not found.', 'error')
            return redirect(url_for('index'))
    
    return send_file(image_path, mimetype='image/png')


@app.route('/crop-editor')
def crop_editor():
    """Display crop editor page."""
    job_id = session.get('job_id')
    if not job_id:
        flash('No images available.', 'warning')
        return redirect(url_for('index'))
    
    receipts_dir = OUTPUT_FOLDER / job_id / 'receipts'
    if not receipts_dir.exists():
        flash('Receipt images not found.', 'error')
        return redirect(url_for('results'))
    
    # Get receipt data from session
    receipt_data = session.get('receipt_data', [])
    
    return render_template(
        'crop_editor.html',
        receipts=receipt_data,
        job_id=job_id
    )


@app.route('/save-crops', methods=['POST'])
def save_crops():
    """Apply crops to images and regenerate PDF."""
    try:
        data = request.json
        job_id = data.get('job_id')
        crops = data.get('crops', {})
        rotations = data.get('rotations', {})
        
        if not job_id or job_id != session.get('job_id'):
            return jsonify({'success': False, 'error': 'Invalid job ID'})
        
        receipts_dir = OUTPUT_FOLDER / job_id / 'receipts'
        originals_dir = OUTPUT_FOLDER / job_id / 'originals'
        
        if not originals_dir.exists():
            return jsonify({'success': False, 'error': 'Original images not found'})
        
        # Get receipt data from session
        receipt_data = session.get('receipt_data', [])
        processed_receipts = []
        
        # Process each receipt with crops and rotations FROM ORIGINALS
        for idx, receipt_info in enumerate(receipt_data):
            # Always load from original pristine image
            original_path = originals_dir / receipt_info['filename']
            if not original_path.exists():
                continue
            
            # Load original image
            img = Image.open(original_path).copy()
            
            # Apply rotation if specified
            rot = int(rotations.get(str(idx), 0))
            if rot != 0:
                img = img.rotate(-rot, expand=True)  # Negative for clockwise
            
            # Apply crop if specified
            crop_data = crops.get(str(idx), {'x': 0, 'y': 0, 'width': 1, 'height': 1})
            if crop_data['width'] < 1 or crop_data['height'] < 1:
                width, height = img.size
                left = int(crop_data['x'] * width)
                top = int(crop_data['y'] * height)
                right = int((crop_data['x'] + crop_data['width']) * width)
                bottom = int((crop_data['y'] + crop_data['height']) * height)
                img = img.crop((left, top, right, bottom))
            
            # Save cropped image to receipts dir (display version)
            display_path = receipts_dir / receipt_info['filename']
            img.save(str(display_path))
            
            # Add to processed list
            processed_receipts.append({
                'image': img,
                'amount': receipt_info['amount'],
                'id': receipt_info['id'],
                'source': receipt_info.get('id', receipt_info['filename'])
            })
        
        # Regenerate PDF with cropped images
        pdf_path = OUTPUT_FOLDER / job_id / 'selected_receipts.pdf'
        generate_pdf_from_receipts(processed_receipts, str(pdf_path))
        
        # Update metadata with crop information
        metadata = load_job_metadata(job_id)
        if metadata:
            metadata['last_modified'] = datetime.now().isoformat()
            metadata['crops_applied'] = True
            save_job_metadata(job_id, metadata)
        
        flash('Crops applied and PDF regenerated successfully!', 'success')
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error saving crops: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/history')
def history():
    """Display job history."""
    jobs = get_all_jobs()
    return render_template('history.html', jobs=jobs)


@app.route('/load-job/<job_id>')
def load_job(job_id):
    """Load a saved job into session."""
    metadata = load_job_metadata(job_id)
    
    if not metadata:
        flash('Job not found or metadata missing.', 'error')
        return redirect(url_for('history'))
    
    # Check if job files exist
    job_dir = OUTPUT_FOLDER / job_id
    if not job_dir.exists():
        flash('Job directory not found.', 'error')
        return redirect(url_for('history'))
    
    # Restore session from metadata
    session['job_id'] = job_id
    session['total_receipts'] = metadata.get('total_receipts', 0)
    session['selected_count'] = metadata.get('selected_count', 0)
    session['target_amount'] = metadata.get('target_amount', 0)
    session['selected_total'] = metadata.get('selected_total', 0)
    session['pdf_path'] = metadata.get('pdf_path', '')
    session['receipt_data'] = metadata.get('receipt_data', [])
    
    # Load selected_indices, default to all if not present
    receipt_data = metadata.get('receipt_data', [])
    session['selected_indices'] = metadata.get('selected_indices', list(range(len(receipt_data))))
    
    flash(f'Job loaded successfully! Created {metadata.get("created_at", "Unknown")}', 'success')
    return redirect(url_for('results'))


@app.route('/delete-job/<job_id>', methods=['POST'])
def delete_job(job_id):
    """Delete a saved job."""
    try:
        job_dir = OUTPUT_FOLDER / job_id
        if job_dir.exists():
            shutil.rmtree(job_dir)
            flash('Job deleted successfully.', 'success')
        else:
            flash('Job not found.', 'error')
    except Exception as e:
        flash(f'Error deleting job: {str(e)}', 'error')
    
    return redirect(url_for('history'))


@app.route('/about')
def about():
    """Display about page."""
    return render_template('about.html')


@app.errorhandler(413)
def too_large(e):
    """Handle file too large error."""
    flash(f'File size exceeds {MAX_FILE_SIZE // (1024*1024)}MB limit. Please use smaller images or fewer files.', 'error')
    return redirect(url_for('index'))


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Receipt Processing Web Application")
    print("="*60)
    print("\nStarting server...")
    print("Open your browser and navigate to: http://localhost:5000")
    print("\nPress Ctrl+C to stop the server\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
