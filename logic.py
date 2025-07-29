"""
Enhanced PDF Processing Logic

This module contains the PDFProcessor class that orchestrates:
1. OCR text extraction from PDFs
2. AI-powered part record extraction
3. Multiple output format generation
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

from services.pdfToText import extract_text_from_pdf
from services.fulltest import process_extracted_text

class PDFProcessor:
    """Enhanced PDF processor with OCR and AI capabilities"""
    
    def __init__(self):
        self.results_dir = Path("results")
        self.results_dir.mkdir(exist_ok=True)
    
    def process_pdf(self, pdf_path: str, upload_id: str, original_filename: str = None) -> Dict[str, Any]:
        """
        Process PDF through the complete pipeline
        
        Args:
            pdf_path: Path to the PDF file
            upload_id: Unique identifier for this processing session
            original_filename: Original filename for better naming
            
        Returns:
            Dictionary with processing results and file information
        """
        start_time = time.time()
        
        # Create result directory for this upload
        upload_result_dir = self.results_dir / upload_id
        upload_result_dir.mkdir(exist_ok=True)
        
        # Create status file
        status_file = upload_result_dir / "status.json"
        self._update_status(status_file, "processing", "Starting OCR extraction...")
        
        try:
            # Step 1: OCR Text Extraction
            print(f"🔍 Starting OCR extraction for {original_filename or 'uploaded file'}")
            self._update_status(status_file, "processing", "Extracting text from PDF...")
            
            text_output, json_output, txt_path, md_path = extract_text_from_pdf(
                pdf_path, 
                str(upload_result_dir)
            )
            
            # Step 2: AI Part Record Extraction
            print(f"🤖 Starting AI processing...")
            self._update_status(status_file, "processing", "Extracting part records with AI...")
            
            records, excel_path = process_extracted_text(
                txt_path, 
                str(upload_result_dir)
            )
            
            # Calculate processing metrics
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Prepare result data
            result_data = {
                "upload_id": upload_id,
                "original_filename": original_filename,
                "processing_time": round(processing_time, 2),
                "extracted_text_length": len(text_output),
                "pages_processed": len(json_output.get('pages', [])),
                "records_extracted": len(records),
                "files_generated": self._get_file_info(upload_result_dir),
                "sample_records": records[:3] if records else [],  # First 3 records as preview
                "fields_extracted": list(records[0].keys()) if records else []
            }
            
            # Update status to completed
            self._update_status(
                status_file, 
                "completed", 
                f"Successfully extracted {len(records)} part records",
                {
                    "records_extracted": len(records),
                    "processing_time": round(processing_time, 2),
                    "sample_records": records[:3] if records else [],
                    "files_generated": self._get_file_info(upload_result_dir),
                    "data": result_data
                }
            )
            
            print(f"✅ Processing completed: {len(records)} records extracted in {processing_time:.2f}s")
            
            return result_data
            
        except Exception as e:
            error_message = f"Processing failed: {str(e)}"
            print(f"❌ {error_message}")
            
            # Update status to error
            self._update_status(
                status_file, 
                "error", 
                error_message,
                {"error_details": str(e)}
            )
            
            raise e
    
    def reprocess_text(self, text_file_path: str, upload_id: str, settings: dict) -> Dict[str, Any]:
        """
        Reprocess existing extracted text with different AI settings
        
        Args:
            text_file_path: Path to the extracted text file
            upload_id: Upload identifier
            settings: New processing settings
            
        Returns:
            Updated processing results
        """
        start_time = time.time()
        
        upload_result_dir = self.results_dir / upload_id
        status_file = upload_result_dir / "status.json"
        
        try:
            self._update_status(status_file, "reprocessing", "Reprocessing with new settings...")
            
            # Apply settings to the AI processing (this could be extended)
            # For now, we'll just rerun the AI extraction
            records, excel_path = process_extracted_text(
                text_file_path, 
                str(upload_result_dir)
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            result_data = {
                "upload_id": upload_id,
                "reprocessing_time": round(processing_time, 2),
                "records_extracted": len(records),
                "files_updated": self._get_file_info(upload_result_dir),
                "sample_records": records[:3] if records else [],
                "fields_extracted": list(records[0].keys()) if records else [],
                "settings_applied": settings
            }
            
            self._update_status(
                status_file, 
                "completed", 
                f"Reprocessing completed: {len(records)} records",
                {
                    "records_extracted": len(records),
                    "reprocessing_time": round(processing_time, 2),
                    "sample_records": records[:3] if records else [],
                    "files_updated": self._get_file_info(upload_result_dir),
                    "data": result_data
                }
            )
            
            return result_data
            
        except Exception as e:
            error_message = f"Reprocessing failed: {str(e)}"
            self._update_status(status_file, "error", error_message)
            raise e
    
    def get_processing_history(self, upload_id: str) -> Optional[Dict[str, Any]]:
        """Get processing history for a specific upload"""
        status_file = self.results_dir / upload_id / "status.json"
        
        if status_file.exists():
            with open(status_file, 'r') as f:
                return json.load(f)
        
        return None
    
    def _update_status(self, status_file: Path, status: str, message: str, data: dict = None):
        """Update the status file with current processing state"""
        status_data = {
            "status": status,
            "message": message,
            "timestamp": time.time(),
            "readable_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        if data:
            status_data.update(data)
        
        with open(status_file, 'w') as f:
            json.dump(status_data, f, indent=2)
    
    def _get_file_info(self, directory: Path) -> List[Dict[str, Any]]:
        """Get information about files in the result directory"""
        files_info = []
        
        for file_path in directory.iterdir():
            if file_path.is_file() and file_path.name != "status.json":
                file_size = file_path.stat().st_size
                files_info.append({
                    "filename": file_path.name,
                    "size_bytes": file_size,
                    "size_kb": round(file_size / 1024, 1),
                    "type": self._get_file_type(file_path.suffix),
                    "description": self._get_file_description(file_path.name)
                })
        
        return files_info
    
    def _get_file_type(self, extension: str) -> str:
        """Get file type description based on extension"""
        type_map = {
            ".xlsx": "Excel Spreadsheet",
            ".txt": "Text File", 
            ".md": "Markdown Document",
            ".json": "JSON Data",
            ".pdf": "PDF Document"
        }
        return type_map.get(extension.lower(), "Unknown")
    
    def _get_file_description(self, filename: str) -> str:
        """Get user-friendly description of the file"""
        if "_parts.xlsx" in filename:
            return "Extracted part records (main output)"
        elif "_extracted.txt" in filename:
            return "Plain text extracted from PDF"
        elif "_extracted.md" in filename:
            return "Formatted text with structure"
        elif "_ocr.json" in filename:
            return "Raw OCR data (debug)"
        else:
            return "Generated file" 