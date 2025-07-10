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

from logic import PDFProcessor
from utils import cleanup_old_files, get_file_info

app = FastAPI(title="PDF Processor API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
UPLOAD_DIR = Path("uploads")
RESULTS_DIR = Path("results")
STATIC_DIR = Path("static")
TEMP_DIR = Path("temp")

# Create directories
for dir_path in [UPLOAD_DIR, RESULTS_DIR, STATIC_DIR, TEMP_DIR]:
    dir_path.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/results", StaticFiles(directory="results"), name="results")

# Initialize processor
processor = PDFProcessor()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process PDF file"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Generate unique ID for this upload
    upload_id = str(uuid.uuid4())
    
    # Save uploaded file
    upload_path = UPLOAD_DIR / f"{upload_id}.pdf"
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Process PDF
        result_data = processor.process_pdf(str(upload_path), upload_id)
        
        # Cleanup upload
        upload_path.unlink()
        
        return {
            "upload_id": upload_id,
            "status": "success",
            "data": result_data
        }
    except Exception as e:
        # Cleanup on error
        if upload_path.exists():
            upload_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{upload_id}/{file_type}/{page}/{filename}")
async def download_file(upload_id: str, file_type: str, page: str, filename: str):
    """Download specific file"""
    file_path = RESULTS_DIR / upload_id / page / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )

@app.get("/download-all/{upload_id}")
async def download_all(upload_id: str):
    """Download all results as ZIP"""
    import zipfile
    
    result_dir = RESULTS_DIR / upload_id
    if not result_dir.exists():
        raise HTTPException(status_code=404, detail="Results not found")
    
    # Create ZIP file
    zip_path = TEMP_DIR / f"{upload_id}.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(result_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = str(file_path.relative_to(result_dir))
                zipf.write(file_path, arcname)
    
    return FileResponse(
        path=zip_path,
        filename=f"results_{upload_id}.zip",
        media_type='application/zip'
    )

@app.delete("/cleanup/{upload_id}")
async def cleanup_results(upload_id: str):
    """Clean up results for specific upload"""
    result_dir = RESULTS_DIR / upload_id
    if result_dir.exists():
        shutil.rmtree(result_dir)
    
    zip_path = TEMP_DIR / f"{upload_id}.zip"
    if zip_path.exists():
        zip_path.unlink()
    
    return {"status": "cleaned"}

@app.on_event("startup")
async def startup_event():
    """Clean up old files on startup"""
    cleanup_old_files(TEMP_DIR, days=1)
    cleanup_old_files(RESULTS_DIR, days=7)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)