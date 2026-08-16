# Receipt Processing Application

> [!WARNING]
> This application is created for personal use. As this application consumes AI credits, it is intended to be deployed internally only.

An automated Python application that processes receipt images using Google Gemini AI: upload one or more images (each may contain a single receipt or several), Google Gemini detects every individual receipt and extracts its total, the application computes the best combination of receipts that reaches (or comes closest to) your target amount, and the selected receipts are compiled into a PDF.

## Features

- **AI Receipt Detection**: Google Gemini detects individual receipts and extracts totals from images containing multiple receipts.
- **Smart Selection**: Algorithms pick a receipt combination that best matches your target amount (within `max_overage`).
- **Editable Receipts**: Edit extracted amounts, manually add receipts (image + amount), recompute the best selection from a chosen subset, and remove unwanted receipts.
- **Crop & Rotate Editor**: Interactive editor with bounding-box crop and rotation; recropping always works from pristine originals.
- **Auto-Rotate**: Landscape receipt images are automatically rotated to portrait for the PDF.
- **PDF & Image Output**: Produces a title-summary PDF of selected receipts and saves individual receipt images; full-screen zoom/pan viewer in the gallery.
- **Job Persistence**: Every job is saved with metadata; jobs appear in History while still processing and complete (or fail) live.
- **Configurable Settings**: Name, Gemini model, currency (symbol/code/name), and max overage are editable from the Settings page (API key remains in `.env`).
- **Responsive UI**: Works on desktop, tablet, and mobile.

## Quick Start

Run locally in three steps:

```bash
cp .env.example .env          # 1. then set your GEMINI_API_KEY inside .env
pip install -r requirements.txt  # 2. install dependencies
python app.py                 # 3. open http://localhost:5000
```

For a step-by-step walkthrough (including getting a Gemini API key), see [QUICKSTART.md](QUICKSTART.md).

## Running the App

The app is a Flask web server with two run modes: **locally** (development) and **in Docker** (deployment). Both serve the same app on port 5000; the only differences are how you start them and where job data lives.

### Prerequisites

- **Local only:** Python 3.8 or higher
- A **Google Gemini API key** — get one from [Google AI Studio](https://aistudio.google.com/app/apikey)

### Step 1 — Configure `.env` (do this once)

Copy the template and fill in your values:

```bash
cp .env.example .env
```

Then edit `.env`:

```env
GEMINI_API_KEY=your-api-key-here
SECRET_KEY=some-random-string
```

| Variable | Required | What it does |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Google Gemini API key used for receipt detection |
| `SECRET_KEY` | No | Signs Flask sessions; falls back to a hardcoded dev default if unset |

> **Notes:**
> - The app loads `.env` automatically via `python-dotenv`.
> - The `FLASK_ENV` and `DEBUG` entries in `.env.example` are **not read by the app**. `python app.py` always starts the Flask dev server with debug mode on, so you don't need to touch them.
> - Keep your API key **only** in `.env` — never in `settings.json` or the Settings page. The Gemini **model** name and currency preferences are configured on the Settings page.

### Step 2 — Choose how to run it

#### Option A: Run locally (development)

```bash
pip install -r requirements.txt
python app.py
```

- Open http://localhost:5000
- Runs the Flask dev server with debug and auto-reload enabled (restarts on code changes)
- Job data is stored in `uploads/` and `web_output/` in the project directory

*(Optional) use a virtual environment:*

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
python app.py
```

#### Option B: Run with Docker (deployment)

The repo includes a `Dockerfile` and `docker-compose.yml` that package the app and run it in a container.

```bash
docker compose up --build -d
```

- App is available at http://localhost:5000
- Your `.env` is passed into the container (`env_file`)
- `uploads/` and `web_output/` are mounted as volumes, so jobs survive container restarts
- `restart: unless-stopped` keeps it running across reboots

Stop it with `docker compose down`.

Without compose:

```bash
docker build -t receipt-processor .
docker run -p 5000:5000 --env-file .env \
  -v "$PWD/uploads:/app/uploads" -v "$PWD/web_output:/app/web_output" \
  receipt-processor
```

> **Note:** The container runs the same built-in Flask server (`python app.py`), not a WSGI server like Gunicorn. That's fine for internal/personal use, but if you ever expose it publicly, put a reverse proxy (e.g. nginx/Caddy) in front of it.

### Configuring user preferences

User-facing preferences are managed on the **Settings page** (`/settings`) and persisted to `settings.json` (gitignored):

- `first_name` / `last_name` — used in generated PDF filenames
- `gemini_model` — Google Gemini model used for processing
- `currency_symbol` / `currency_code` / `currency_name` — display currency
- `max_overage` — maximum amount the selection may exceed the target

## How It Works

### 1. AI-Powered Analysis
You upload one or more images; each image may contain a single receipt or several. All images are passed to Google Gemini in one call, which:
- Detects every individual receipt within each image
- Extracts precise bounding boxes for each receipt
- Reads the receipt text and identifies the total amount of each receipt
- Returns one extracted receipt per detected receipt, across all uploaded images

### 2. Receipt Selection
From the full list of extracted receipts, the application computes the best combination to match your target amount:
- **Exact Match**: Finds combinations within tolerance
- **Best Fit**: Maximizes total without exceeding target
- **Closest Match**: Finds nearest total (may exceed target)

### 3. PDF Generation
Creates a professional PDF containing:
- Title page with summary statistics
- Individual pages for each selected receipt
- Final summary page with itemized list

## Web Interface

The web UI has five pages, each focused on one step of the workflow:

| Page | What it does |
|------|--------------|
| **Upload** (`/`) | Drag-and-drop or click-to-select images, set the target amount, validate files. |
| **Results** (`/results`) | Summary dashboard with selection count (e.g. `6 / 7`), quick links to crop, images, and PDF download. |
| **Images** (`/images`) | Per-receipt gallery with zoom/pan viewer; edit amounts, add manual receipts, remove receipts, recompute selection, regenerate PDF. |
| **Crop Editor** (`/crop-editor`) | Adjust bounding boxes and rotation per receipt; re-crop from pristine originals and rebuild the PDF. |
| **History** (`/history`) | Browse saved jobs with thumbnails and stats; load to resume, delete old jobs. |
| **Settings** (`/settings`) | Edit your name (used in PDF filename), Gemini model, currency, and max overage. API key stays in `.env`. |

### Job Persistence

Jobs are stored as folders under `web_output/<job_id>/` containing `originals/`, `receipts/`, `metadata.json`, and `selected_receipts.pdf`. A job appears in History immediately with a `Processing` status and updates to `Completed` or `Failed` when Gemini finishes. Jobs persist indefinitely until deleted; only unsaved uploads in `uploads/` are cleaned after 24h.

### Workflow

1. Configure once in **Settings** (model, currency, name, max overage).
2. Upload one or more images (each may contain multiple receipts) and a target amount on the **Upload** page.
3. Review the **Results** dashboard, then jump to **Images** to edit/add/remove receipts or recompute the optimal subset.
4. Open the **Crop Editor** to fine-tune boxes or rotation — re-saving rebuilds the PDF from originals.
5. Download the PDF from **Results** (or via History later).

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
1. Ensure `GEMINI_API_KEY` is set in your `.env` file
2. Verify your API key is valid at [Google AI Studio](https://aistudio.google.com/app/apikey)
3. Restart the app after changing `.env`

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

### Port Already in Use
If port 5000 is taken, change it in `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Changed from 5000
```

## Dependencies

- **Flask**: Web framework for the user interface
- **Werkzeug**: WSGI utility library for Flask
- **google-genai**: Google Gemini AI API client (latest version)
- **Pillow**: Image manipulation
- **reportlab**: PDF generation

## Future Enhancements

- **REST API**: Programmatic access to upload, process, and download endpoints.
- **Database Backend**: Replace file-based job storage with SQLite/Postgres for easier querying and analytics.
- **Multi-User Auth**: Accounts, per-user job history, and shared link generation.
- **Email Delivery**: Send the generated PDF directly via email.
- **Job Queue**: Async worker for processing large batches without blocking the UI.
- **Cloud Storage & OCR**: S3/GCS storage backends; optional Google Vision / AWS Textract fallbacks for low-confidence Gemini results.
- **Exports & Analytics**: Excel/CSV export; spending trends by category and merchant.

## License

This project is provided as-is for educational and personal use.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.