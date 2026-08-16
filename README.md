# Receipt Processing Application

> [!WARNING]
> This application is created for personal use. As this application consumes AI credits, it is intended to be deployed internally only.

An automated Python application that processes receipt images using Google Gemini AI, extracts amounts intelligently, selects receipts to match a target amount, and generates a professional PDF compilation.

## Features

- **AI-Powered Detection**: Uses Google Gemini Flash 3 to detect and analyze receipts
- **Multi-receipt Processing**: Automatically detects and extracts individual receipts from images containing multiple receipts
- **Intelligent Amount Extraction**: AI-powered extraction of total amounts from receipts
- **Smart Selection**: Intelligent algorithms to select receipts that best match your target amount
- **Image Extraction**: Saves selected receipts as individual image files
- **PDF Generation**: Creates a professional PDF document with selected receipt images
- **Image Crop Editor**: Interactive crop tool to adjust receipt boundaries and rotation
- **Image Viewer**: Click any receipt image to open a zoomable, pannable viewer
- **Job Persistence**: All processing jobs are automatically saved and can be revisited later
- **Live Job History**: Jobs appear in History while still processing (with a status badge)
- **Job History**: Browse and reload previous jobs to re-crop, re-download, or review results
- **Configurable Settings**: Gemini model, currency symbol/code/name, and max overage are editable in Settings
- **Web Interface**: Easy-to-use browser-based interface for uploading and processing receipts
- **Mobile Friendly**: Responsive design works seamlessly on phones and tablets

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the web application:
   ```bash
   python app.py
   ```

3. Open your browser to http://localhost:5000

See [QUICKSTART.md](QUICKSTART.md) for detailed instructions.

## Prerequisites

- Python 3.8 or higher
- Google Gemini API key (free tier available)

### Getting a Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy your API key
5. Set it as an environment variable:

**Windows (Command Prompt):**
```cmd
set GEMINI_API_KEY=your-api-key-here
```

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY="your-api-key-here"
```

**macOS/Linux:**
```bash
export GEMINI_API_KEY="your-api-key-here"
```

Or add it to your `.env` file or system environment variables for persistence.

> **Note:** API keys are stored **only** in `.env` (or environment variables). Never put your API key in `settings.json` or the Settings page. The Gemini **model** name and currency preferences are configured on the Settings page.

## Installation

1. Clone or download this repository
2. Navigate to the project directory
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

The application is used through its web interface.

### Web Interface (Recommended)

1. Start the web server:
   ```bash
   python app.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

3. Use the web interface to:
   - Upload receipt images (drag & drop or click to select)
   - Set your target amount
   - View results and download PDF
   - Browse individual receipt images

The web interface provides a user-friendly experience with real-time feedback and visual results.

## How It Works

### 1. AI-Powered Analysis
The application uses Google Gemini Flash 3 to:
- Detect individual receipts in images
- Handle multiple receipts per image
- Extract precise bounding boxes for each receipt
- Read and understand receipt text
- Identify total amounts with high accuracy

### 2. Receipt Selection
Multiple strategies are employed to match the target amount:
- **Exact Match**: Finds combinations within tolerance
- **Best Fit**: Maximizes total without exceeding target
- **Closest Match**: Finds nearest total (may exceed target)

### 3. PDF Generation
Creates a professional PDF containing:
- Title page with summary statistics
- Individual pages for each selected receipt
- Final summary page with itemized list

## Web Interface Features

The web application provides an intuitive interface with the following features:

### Upload Page
- **Drag & Drop Upload**: Simply drag receipt images onto the upload area
- **Multi-file Selection**: Upload multiple images at once
- **File Validation**: Automatic validation of file types and sizes
- **Target Amount Input**: Easy-to-use input field with validation
- **Real-time Feedback**: Visual confirmation of selected files
- **AI Processing**: Powered by Google Gemini for accurate results

### Results Page
- **Summary Dashboard**: Visual cards showing key metrics
- **Selection Summary**: Shows the number of selected receipts out of the total (e.g. `6 / 7`)
- **Quick Actions**: Download PDF or view individual images
- **Detailed Breakdown**: Complete summary of processing results

### Image Gallery
- **Visual Preview**: View all selected receipt images
- **Individual Download**: Download specific receipt images
- **Zoomable Viewer**: Click any receipt to open a full-screen viewer with zoom in/out, reset, and pan controls
- **Responsive Layout**: Adapts to different screen sizes

### Settings Page
- **Personal Information**: First and last name used in generated file names
- **AI Configuration**: Gemini model selection (API key stays in `.env`)
- **Currency Settings**: Symbol, code, and name used throughout the app
- **Receipt Selection**: Max overage allowed when matching a target amount

### Job Persistence & History
- **Automatic Saving**: All processing jobs are automatically saved with complete metadata
- **Live Processing Status**: Jobs appear in History immediately with a "Processing" badge while Gemini works, then update to "Completed" (or "Failed")
- **Job History Page**: Browse all previously processed jobs with preview thumbnails
- **Session Restoration**: Load any saved job to continue working with it
- **Re-crop & Re-download**: Access original images to adjust crops and regenerate PDFs
- **Job Management**: Delete old jobs you no longer need
- **No Database Required**: File-based storage keeps everything self-contained
- **Statistics Display**: Each saved job shows total receipts, selected count, and amounts
- **Visual Previews**: See thumbnail previews of the first 4 receipts in each job

#### Using Job History

1. **Access History**: Click the "History" link in the navigation menu
2. **Browse Jobs**: View all saved jobs with their processing date and statistics
3. **Load a Job**: Click "Load" to restore a previous job and continue working
4. **Delete Jobs**: Click "Delete" to remove jobs you no longer need (confirmation shown in a modal)
5. **Re-crop Images**: After loading a job, use the crop editor to adjust receipt boundaries
6. **Re-download PDF**: Generate a new PDF with updated crops or selections

All jobs are stored in the `web_output/` folder with a unique job ID. Each job includes:
- Original uploaded images
- Processed receipt images
- All metadata (amounts, selections, timestamps)
- Generated PDF files

Jobs persist until manually deleted or the `web_output/` folder is cleared. Jobs without metadata (older than 24 hours) are automatically cleaned up.

### Additional Features
- **Auto-cleanup**: Temporary files without saved metadata are automatically removed after 24 hours
- **Session Management**: Each processing job is isolated with unique IDs
- **Error Handling**: User-friendly error messages and guidance
- **Responsive Design**: Works on desktop, tablet, and mobile devices

## Deployment

### Local Development
```bash
python app.py
```
The server will start on `http://localhost:5000`

### Production Deployment

For production deployment, use a WSGI server like Gunicorn:

1. Install Gunicorn:
   ```bash
   pip install gunicorn
   ```

2. Run with Gunicorn:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

3. Set environment variables:
   ```bash
   export SECRET_KEY='your-secret-key-here'
   export FLASK_ENV='production'
   ```

### Configuration Options

User-facing preferences are managed on the **Settings page** (`/settings`) and stored in `settings.json`:
- `first_name` / `last_name`: Personalized download file names
- `gemini_model`: Google Gemini model used for processing
- `currency_symbol` / `currency_code` / `currency_name`: Display currency
- `max_overage`: Maximum amount the selection may exceed the target

Edit `app.py` or set environment variables:
- `SECRET_KEY`: Session encryption key (required for production)
- `MAX_FILE_SIZE`: Maximum upload file size (default: 16MB)
- `UPLOAD_FOLDER`: Directory for temporary uploads
- `OUTPUT_FOLDER`: Directory for processed files
- `GEMINI_API_KEY`: Your Google Gemini API key (required, keep in `.env`)

### Docker Deployment

The repository includes a `Dockerfile` and `docker-compose.yml`. To run with Docker Compose:

```bash
docker compose up --build
```

Or build and run manually:
```bash
docker build -t receipt-processor .
docker run -p 5000:5000 receipt-processor
```

## Project Structure

```
allowance-gen/
├── app.py                  # Web application server (Flask)
├── gemini_processor.py     # Google Gemini AI integration
├── receipt_selector.py     # Receipt selection algorithms
├── pdf_generator.py        # PDF generation
├── config.py               # Configuration settings (fallback defaults)
├── requirements.txt        # Python dependencies
├── .gitignore             # Git ignore rules
├── .dockerignore          # Docker ignore rules
├── Dockerfile             # Docker image definition
├── docker-compose.yml     # Docker Compose setup
├── .env.example           # Example environment variables
├── README.md              # This file
├── QUICKSTART.md          # Quick start guide
├── templates/             # HTML templates for web interface
│   ├── base.html         # Base template
│   ├── index.html        # Upload page
│   ├── results.html      # Results page
│   ├── images.html       # Image gallery
│   ├── history.html      # Job history page
│   ├── settings.html     # Settings page
│   ├── crop_editor.html  # Interactive crop editor
│   └── about.html        # About page
├── static/                # Static assets
│   └── style.css         # Stylesheet
├── settings.json          # User preferences (model, currency, names) from Settings page (gitignored)
├── uploads/               # Web app uploads (temporary)
└── web_output/            # Web app output with job persistence
    ├── <job_id>/          # Individual job folders
    │   ├── originals/     # Pristine uploaded images
    │   ├── receipts/      # Processed/cropped receipt images
    │   ├── metadata.json  # Job metadata and session data
    │   └── *.pdf          # Generated PDF files
    └── ...
```

## Module Documentation

### gemini_processor.py
- `process_receipts_with_gemini(image_paths, api_key=None, model=None)`: Process receipts using Gemini AI (model from Settings by default)
- `extract_receipt_from_box(image, box)`: Extract receipt region using bounding box
- `configure_gemini(api_key)`: Configure Gemini API with key
- `validate_receipt_data(receipt_data)`: Validate receipt data structure

### receipt_selector.py
- `select_receipts_by_target(receipts, target_amount)`: Selects receipts to match target
- `find_exact_match(receipts, target, tolerance)`: Finds exact combination
- `find_best_fit_subset(receipts, target)`: Finds best fit without exceeding
- `find_closest_match(receipts, target)`: Finds closest total

### pdf_generator.py
- `generate_pdf_from_receipts(receipts, output_path)`: Generates PDF document
- `add_title_page(...)`: Adds title page to PDF
- `add_receipt_to_pdf(...)`: Adds receipt page to PDF
- `add_summary_page(...)`: Adds summary page to PDF

## Troubleshooting

### API Key Issues
If you get an error about missing API key:
1. Ensure you've set the `GEMINI_API_KEY` environment variable
2. Verify your API key is valid at [Google AI Studio](https://aistudio.google.com/app/apikey)
3. Check that the environment variable is set in the current terminal session

### API Rate Limits
If you hit rate limits:
- Free tier has generous limits but may require waiting between requests
- Consider upgrading to paid tier for higher throughput
- Process images in smaller batches

### Poor Detection Accuracy
If receipts are not being detected correctly:
- Ensure images are clear and well-lit
- Receipt text should be legible
- Avoid heavy shadows or glare
- Try higher resolution images

### No Amounts Extracted
If amounts are not being extracted:
- Verify receipts have a clear TOTAL or GRAND TOTAL line
- Check that the receipt is not upside down or rotated
- Ensure the receipt is not heavily damaged or faded

### Can't Match Target Amount
The selection algorithm will:
1. First try to find an exact match
2. Then try to get as close as possible without exceeding
3. Finally find the closest match (may exceed)

If no receipts are selected, check that your target is reasonable given the available receipt amounts.

## Dependencies

- **Flask**: Web framework for the user interface
- **Werkzeug**: WSGI utility library for Flask
- **google-genai**: Google Gemini AI API client (latest version)
- **Pillow**: Image manipulation
- **reportlab**: PDF generation

## Future Enhancements

Potential improvements for future versions:
- **API Endpoints**: RESTful API for programmatic access
- **Database Integration**: Store receipt history and processing results
- **User Authentication**: Multi-user support with accounts
- **Advanced ML**: Machine learning models for better amount detection
- **Multi-language Support**: OCR support for receipts in different languages
- **Cloud Storage**: Integration with cloud storage services (S3, Google Cloud)
- **Email Integration**: Send PDF directly via email
- **Batch Processing**: Queue system for processing large numbers of receipts
- **Mobile App**: Native mobile applications for iOS and Android
- **Receipt Analytics**: Spending analytics and visualization
- **Cloud OCR Services**: Integration with Google Vision, AWS Textract
- **Export Formats**: Support for Excel, CSV exports in addition to PDF

## License

This project is provided as-is for educational and personal use.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.
