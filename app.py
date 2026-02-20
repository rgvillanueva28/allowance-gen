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
        
        # Select receipts based on target amount
        selected_receipts = select_receipts_by_target(receipts_with_amounts, target_amount)
        
        if not selected_receipts:
            flash('Could not select receipts to match target amount.', 'warning')
            return redirect(url_for('index'))
        
        total_selected = sum(r['amount'] for r in selected_receipts)
        print(f"[Job {job_id}] Selected {len(selected_receipts)} receipt(s), total: ${total_selected:.2f}")
        
        # Generate PDF
        output_dir = OUTPUT_FOLDER / job_id
        output_dir.mkdir(exist_ok=True)
        
        receipts_dir = output_dir / 'receipts'
        receipts_dir.mkdir(exist_ok=True)
        
        # Create originals directory to preserve source images
        originals_dir = output_dir / 'originals'
        originals_dir.mkdir(exist_ok=True)
        
        # Save receipt images and store amounts
        receipt_data = []
        for i, receipt in enumerate(selected_receipts, 1):
            # Save display version (cropped receipt)
            image_path = receipts_dir / f"receipt_{i}.png"
            receipt['image'].save(str(image_path))
            
            # Save ORIGINAL uploaded image (before AI cropping) to originals folder
            file_id = receipt.get('file_id', f"receipts_0")
            original_upload_path = file_id_to_path.get(file_id)
            if original_upload_path:
                # Copy the actual uploaded image file
                original_path = originals_dir / f"receipt_{i}.png"
                original_img = Image.open(original_upload_path)
                original_img.save(str(original_path))
            
            receipt_data.append({
                'filename': f"receipt_{i}.png",
                'amount': receipt['amount'],
                'id': receipt.get('id', f'receipt_{i}'),
                'box': receipt.get('box', [0, 0, 1000, 1000]),  # Store original bounding box
                'file_id': receipt.get('file_id', 'receipts_0')
            })
        
        # Generate PDF
        pdf_path = output_dir / 'selected_receipts.pdf'
        generate_pdf_from_receipts(selected_receipts, str(pdf_path))
        
        # Store job info in session
        session['job_id'] = job_id
        session['total_receipts'] = len(receipts_with_amounts)
        session['selected_count'] = len(selected_receipts)
        session['target_amount'] = target_amount
        session['selected_total'] = total_selected
        session['pdf_path'] = str(pdf_path)
        session['receipt_data'] = receipt_data
        
        # Save job metadata for persistence
        metadata = {
            'created_at': datetime.now().isoformat(),
            'total_receipts': len(receipts_with_amounts),
            'selected_count': len(selected_receipts),
            'target_amount': float(target_amount),
            'selected_total': float(total_selected),
            'receipt_data': receipt_data,
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
    
    # Get receipt data with amounts from session
    receipt_data = session.get('receipt_data', [])
    
    return render_template(
        'images.html',
        receipts=receipt_data,
        job_id=job_id
    )


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
