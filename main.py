#!/usr/bin/env python3
"""
Main OCR and Part Extraction Pipeline

This script processes PDF documents to extract part information using OCR and AI:
1. PDF → OCR Text Extraction (using pdfToText.py)
2. Text → AI Part Record Extraction (using fulltest.py)

Usage:
    python main.py <pdf_path>
    python main.py <pdf_path> --output-dir <directory>

Example:
    python main.py HL79.pdf
    python main.py AN929.pdf --output-dir results
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from pathlib import Path
import uuid
from typing import List, Dict
import json
import asyncio
from contextlib import asynccontextmanager

# OCR imports
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
import matplotlib.pyplot as plt

from logic import PDFProcessor
from utils import cleanup_old_files, get_file_info, cleanup_upload_and_results

# Configuration
UPLOAD_DIR = Path("uploads")
RESULTS_DIR = Path(__file__).parent / "results"
STATIC_DIR = Path("static")
TEMP_DIR = Path("temp")
TEMPLATES_DIR = Path("templates")

# File cleanup settings
CLEANUP_HOURS = 1  # Clean files older than 1 hour
CLEANUP_INTERVAL = 300  # Run cleanup every 5 minutes (300 seconds)

# Background task control
cleanup_task = None

async def periodic_cleanup():
    """Background task to periodically clean up old files"""
    while True:
        try:
            cleanup_upload_and_results(UPLOAD_DIR, RESULTS_DIR, STATIC_DIR, TEMP_DIR, CLEANUP_HOURS)
        except Exception as e:
            print(f"⚠️ Cleanup task error: {e}")
        
        # Wait for next cleanup cycle
        await asyncio.sleep(CLEANUP_INTERVAL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    global cleanup_task
    
    # Startup
    print("🚀 Starting Enhanced PDF Part Extraction API...")
    
    # Create directories
    for dir_path in [UPLOAD_DIR, RESULTS_DIR, STATIC_DIR, TEMP_DIR, TEMPLATES_DIR]:
        dir_path.mkdir(exist_ok=True)
    
    # Initial cleanup
    cleanup_upload_and_results(UPLOAD_DIR, RESULTS_DIR, STATIC_DIR, TEMP_DIR, CLEANUP_HOURS)
    print("✅ Initial cleanup completed")
    
    # Start periodic cleanup task
    cleanup_task = asyncio.create_task(periodic_cleanup())
    print(f"🕒 Started periodic cleanup (every {CLEANUP_INTERVAL // 60} minutes, files older than {CLEANUP_HOURS} hour)")
    
    yield
    
    # Shutdown
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
    print("🛑 Application shutdown complete")

app = FastAPI(title="Enhanced PDF Part Extraction API", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/files", StaticFiles(directory="results"), name="files")

# Initialize processor
processor = PDFProcessor()

# Initialize OCR model (load once at startup)
print("🔍 Loading OCR model...")
ocr_model = ocr_predictor(pretrained=True)
print("✅ OCR model loaded successfully")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main index page"""
    try:
        with open(TEMPLATES_DIR / "index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Template not found")

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process PDF file with enhanced OCR and AI extraction"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Generate unique ID for this upload
    upload_id = str(uuid.uuid4())
    
    # Save uploaded file
    upload_path = UPLOAD_DIR / f"{upload_id}.pdf"
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Process PDF with enhanced pipeline
        result_data = processor.process_pdf(str(upload_path), upload_id, original_filename=file.filename)
        
        # Note: Don't delete upload immediately - let periodic cleanup handle it
        # This allows for potential reprocessing or debugging
        
        return {
            "upload_id": upload_id,
            "status": "success",
            "data": result_data,
            "message": f"Successfully processed {file.filename}. Files will be automatically cleaned up after {CLEANUP_HOURS} hour."
        }
    except Exception as e:
        # Cleanup on error
        if upload_path.exists():
            upload_path.unlink()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/status/{upload_id}")
async def get_processing_status(upload_id: str):
    """Get processing status for a specific upload"""
    result_dir = RESULTS_DIR / upload_id
    if not result_dir.exists():
        return {"status": "not_found", "message": "Upload ID not found"}
    
    # Check for completion markers
    status_file = result_dir / "status.json"
    if status_file.exists():
        with open(status_file, 'r') as f:
            return json.load(f)
    
    return {"status": "processing", "message": "Still processing..."}

@app.get("/results/{upload_id}")
async def get_results_info(upload_id: str):
    """Get information about generated results"""
    result_dir = RESULTS_DIR / upload_id
    if not result_dir.exists():
        raise HTTPException(status_code=404, detail="Results not found")
    
    # Get the status information which contains processing results
    status_file = result_dir / "status.json"
    status_data = {}
    if status_file.exists():
        with open(status_file, 'r') as f:
            status_data = json.load(f)
    
    # Get file information
    results_info = get_file_info(result_dir)
    
    return {
        "upload_id": upload_id,
        "results": results_info,
        "status": "completed",
        "processing_data": status_data.get("data", {}),
        "records_extracted": status_data.get("records_extracted", 0),
        "processing_time": status_data.get("processing_time", 0),
        "sample_records": status_data.get("sample_records", [])
    }

@app.get("/download/{upload_id}/{file_type}/{filename}")
async def download_file(upload_id: str, file_type: str, filename: str):
    """Download specific file"""
    file_path = RESULTS_DIR / upload_id / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type based on file extension
    media_types = {
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel',
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.json': 'application/json',
        '.zip': 'application/zip',
        '.pdf': 'application/pdf',
        '.csv': 'text/csv'
    }
    
    file_ext = Path(filename).suffix.lower()
    media_type = media_types.get(file_ext, 'application/octet-stream')
    
    # Set appropriate filename for download
    download_filename = filename
    
    return FileResponse(
        path=file_path,
        filename=download_filename,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={download_filename}"}
    )

@app.get("/download-all/{upload_id}")
async def download_all(upload_id: str):
    """Download all results as ZIP"""
    import zipfile
    
    result_dir = RESULTS_DIR / upload_id
    if not result_dir.exists():
        raise HTTPException(status_code=404, detail="Results not found")
    
    # Create ZIP file
    zip_path = TEMP_DIR / f"results_{upload_id}.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(result_dir):
            for file in files:
                if file == 'status.json':  # Skip internal status files
                    continue
                file_path = Path(root) / file
                arcname = str(file_path.relative_to(result_dir))
                zipf.write(file_path, arcname)
    
    return FileResponse(
        path=zip_path,
        filename=f"results_{upload_id}.zip",
        media_type='application/zip'
    )

@app.post("/reprocess/{upload_id}")
async def reprocess_with_different_settings(upload_id: str, settings: dict):
    """Reprocess existing upload with different AI settings"""
    result_dir = RESULTS_DIR / upload_id
    if not result_dir.exists():
        raise HTTPException(status_code=404, detail="Original results not found")
    
    try:
        # Find the extracted text file
        text_files = list(result_dir.glob("*_extracted.txt"))
        if not text_files:
            raise HTTPException(status_code=404, detail="Extracted text not found")
        
        # Reprocess with new settings
        new_results = processor.reprocess_text(str(text_files[0]), upload_id, settings)
        
        return {
            "upload_id": upload_id,
            "status": "reprocessed",
            "data": new_results,
            "message": "Successfully reprocessed with new settings"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reprocessing failed: {str(e)}")

@app.get("/ocr-viewer/{upload_id}", response_class=HTMLResponse)
async def ocr_viewer(upload_id: str):
    """Interactive OCR viewer with multi-page overlay (no .show(), true overlay)"""
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches

    result_dir = RESULTS_DIR / upload_id
    if not result_dir.exists():
        raise HTTPException(status_code=404, detail="Upload not found")

    # Try to locate the PDF
    pdf_files = list(result_dir.glob("*.pdf"))
    upload_pdf = UPLOAD_DIR / f"{upload_id}.pdf"

    pdf_path = pdf_files[0] if pdf_files else upload_pdf
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")

    try:
        print(f"📄 OCR Viewer: Processing PDF {pdf_path}")
        doc = DocumentFile.from_pdf(str(pdf_path))
        result = ocr_model(doc)
        ocr_data = result.export()
        num_pages = len(ocr_data["pages"])

        # Convert PDF pages to images
        import fitz  # PyMuPDF
        pdf_doc = fitz.open(str(pdf_path))
        
        for i in range(num_pages):
            page = ocr_data["pages"][i]
            width, height = page["dimensions"]
            
            # Render PDF page as background image
            pdf_page = pdf_doc[i]
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
            pix = pdf_page.get_pixmap(matrix=mat)
            pdf_img_path = STATIC_DIR / f"{upload_id}_pdf_page_{i}.png"
            pix.save(str(pdf_img_path))
            
            # Create completely transparent overlay (no red boxes)
            fig, ax = plt.subplots(figsize=(10, 14))
            fig.patch.set_alpha(0)  # Transparent figure background
            ax.set_xlim(0, width)
            ax.set_ylim(height, 0)
            ax.axis("off")
            ax.patch.set_alpha(0)  # Transparent axes background

            # No visual elements - just transparent overlay for proper sizing
            # Save completely transparent overlay
            fig.savefig(STATIC_DIR / f"{upload_id}_ocr_overlay_{i}.png", 
                       bbox_inches="tight", dpi=150, transparent=True)
            plt.close(fig)
        
        pdf_doc.close()

        # Save OCR JSON
        ocr_data_path = STATIC_DIR / f"{upload_id}_ocr_data.json"
        with open(ocr_data_path, "w") as f:
            json.dump(ocr_data, f, indent=2)

        # Load template from templates directory
        try:
            with open(TEMPLATES_DIR / "ocr_viewer.html", "r", encoding="utf-8") as f:
                html_template = f.read()
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="OCR viewer template not found")

        # Replace the template placeholder with actual upload_id
        html_filled = html_template.replace("{{UPLOAD_ID}}", upload_id)

        return HTMLResponse(content=html_filled, status_code=200)

    except Exception as e:
        print(f"❌ OCR Viewer Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")

@app.post("/process-pdf-ocr")
async def process_pdf_for_ocr(file: UploadFile = File(...)):
    """Upload and process PDF specifically for OCR viewing"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Generate unique ID for this upload
    upload_id = str(uuid.uuid4())
    
    # Save uploaded file
    upload_path = UPLOAD_DIR / f"{upload_id}.pdf"
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Create result directory and save status
    result_dir = RESULTS_DIR / upload_id
    result_dir.mkdir(exist_ok=True)
    
    status_data = {
        "status": "ocr_ready",
        "upload_id": upload_id,
        "original_filename": file.filename,
        "created_at": str(Path(upload_path).stat().st_mtime)
    }
    
    with open(result_dir / "status.json", "w") as f:
        json.dump(status_data, f, indent=2)
    
    return {
        "upload_id": upload_id,
        "status": "success",
        "message": f"PDF uploaded successfully. Files will be automatically cleaned up after {CLEANUP_HOURS} hour.",
        "ocr_viewer_url": f"/ocr-viewer/{upload_id}"
    }

@app.delete("/cleanup/{upload_id}")
async def cleanup_results(upload_id: str):
    """Clean up results for specific upload"""
    result_dir = RESULTS_DIR / upload_id
    if result_dir.exists():
        shutil.rmtree(result_dir)
    
    # Clean up upload file
    upload_file = UPLOAD_DIR / f"{upload_id}.pdf"
    if upload_file.exists():
        upload_file.unlink()
    
    # Clean up OCR files in static
    for pattern in [f"{upload_id}_*.png", f"{upload_id}_*.json"]:
        for file_path in STATIC_DIR.glob(pattern):
            file_path.unlink()
    
    # Clean up temp files
    for zip_file in TEMP_DIR.glob(f"*{upload_id}*.zip"):
        zip_file.unlink()
    
    return {"status": "cleaned", "message": f"Cleaned up all files for {upload_id}"}

@app.get("/cleanup/status")
async def get_cleanup_status():
    """Get cleanup configuration and statistics"""
    upload_count = len(list(UPLOAD_DIR.glob("*.pdf"))) if UPLOAD_DIR.exists() else 0
    results_count = len(list(RESULTS_DIR.glob("*"))) if RESULTS_DIR.exists() else 0
    static_files = len([f for f in STATIC_DIR.glob("*") if not f.name.endswith('.html')]) if STATIC_DIR.exists() else 0
    temp_count = len(list(TEMP_DIR.glob("*"))) if TEMP_DIR.exists() else 0
    
    return {
        "cleanup_enabled": True,
        "cleanup_interval_minutes": CLEANUP_INTERVAL // 60,
        "cleanup_threshold_hours": CLEANUP_HOURS,
        "current_files": {
            "uploads": upload_count,
            "results": results_count,
            "static_temp_files": static_files,
            "temp": temp_count
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "PDF Part Extraction API",
        "version": "2.0.1",
        "cleanup_enabled": True,
        "auto_cleanup_hours": CLEANUP_HOURS
    }

if __name__ == "__main__":
    import uvicorn
    print("🌐 Starting web server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info") 