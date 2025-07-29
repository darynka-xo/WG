"""
Utility functions for the PDF processing web application
"""

import os
import shutil
import time
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timedelta

def cleanup_old_files(directory: Path, days: int = 7):
    """
    Clean up files older than specified days
    
    Args:
        directory: Directory to clean
        days: Files older than this many days will be deleted
    """
    if not directory.exists():
        return
    
    cutoff_time = time.time() - (days * 24 * 60 * 60)
    cleaned_count = 0
    
    for file_path in directory.rglob("*"):
        if file_path.is_file():
            try:
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    cleaned_count += 1
            except Exception as e:
                print(f"⚠️ Could not delete {file_path}: {e}")
    
    # Remove empty directories
    for dir_path in directory.rglob("*"):
        if dir_path.is_dir() and not any(dir_path.iterdir()):
            try:
                dir_path.rmdir()
            except Exception:
                pass
    
    if cleaned_count > 0:
        print(f"🗑️ Cleaned up {cleaned_count} old files from {directory}")

def cleanup_old_files_hours(directory: Path, hours: int = 1):
    """
    Clean up files older than specified hours
    
    Args:
        directory: Directory to clean
        hours: Files older than this many hours will be deleted
    """
    if not directory.exists():
        return
    
    cutoff_time = time.time() - (hours * 60 * 60)
    cleaned_count = 0
    cleaned_size = 0
    
    for file_path in directory.rglob("*"):
        if file_path.is_file():
            try:
                file_stat = file_path.stat()
                if file_stat.st_mtime < cutoff_time:
                    cleaned_size += file_stat.st_size
                    file_path.unlink()
                    cleaned_count += 1
            except Exception as e:
                print(f"⚠️ Could not delete {file_path}: {e}")
    
    # Remove empty directories
    for dir_path in directory.rglob("*"):
        if dir_path.is_dir() and not any(dir_path.iterdir()):
            try:
                dir_path.rmdir()
            except Exception:
                pass
    
    if cleaned_count > 0:
        size_mb = cleaned_size / (1024 * 1024)
        print(f"🗑️ Cleaned up {cleaned_count} files ({size_mb:.2f} MB) from {directory} (older than {hours} hour{'s' if hours != 1 else ''})")

def cleanup_upload_and_results(upload_dir: Path, results_dir: Path, static_dir: Path, temp_dir: Path, hours: int = 1):
    """
    Comprehensive cleanup of all processing-related files
    
    Args:
        upload_dir: Upload directory to clean
        results_dir: Results directory to clean
        static_dir: Static directory to clean (OCR-related files)
        temp_dir: Temp directory to clean
        hours: Files older than this many hours will be deleted
    """
    print(f"🧹 Starting cleanup of files older than {hours} hour{'s' if hours != 1 else ''}...")
    
    # Clean uploads directory
    cleanup_old_files_hours(upload_dir, hours)
    
    # Clean results directory
    cleanup_old_files_hours(results_dir, hours)
    
    # Clean OCR-related files in static directory (but keep HTML files)
    if static_dir.exists():
        cutoff_time = time.time() - (hours * 60 * 60)
        cleaned_count = 0
        
        for file_path in static_dir.glob("*"):
            if file_path.is_file() and not file_path.name.endswith('.html'):
                try:
                    if file_path.stat().st_mtime < cutoff_time:
                        # Only clean OCR-related files (with UUIDs in name)
                        if any(char in file_path.name for char in ['-', '_']) and len(file_path.stem) > 20:
                            file_path.unlink()
                            cleaned_count += 1
                except Exception as e:
                    print(f"⚠️ Could not delete {file_path}: {e}")
        
        if cleaned_count > 0:
            print(f"🗑️ Cleaned up {cleaned_count} OCR files from {static_dir}")
    
    # Clean temp directory
    cleanup_old_files_hours(temp_dir, hours)
    
    print("✅ Cleanup completed")

def get_file_info(directory: Path) -> List[Dict[str, Any]]:
    """
    Get detailed information about files in a directory
    
    Args:
        directory: Directory to scan
        
    Returns:
        List of file information dictionaries
    """
    files_info = []
    
    if not directory.exists():
        return files_info
    
    for file_path in directory.iterdir():
        if file_path.is_file() and file_path.name != "status.json":
            try:
                stat = file_path.stat()
                
                # Determine file type for the download URL
                file_type = get_file_category_for_download(file_path.name)
                
                files_info.append({
                    "filename": file_path.name,
                    "size_bytes": stat.st_size,
                    "size_kb": round(stat.st_size / 1024, 1),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": get_file_type_from_extension(file_path.suffix),
                    "category": get_file_category(file_path.name),
                    "download_url": f"/download/{directory.name}/{file_type}/{file_path.name}"
                })
            except Exception as e:
                print(f"⚠️ Could not get info for {file_path}: {e}")
    
    # Sort by category and then by name
    files_info.sort(key=lambda x: (x["category"], x["filename"]))
    return files_info

def get_file_type_from_extension(extension: str) -> str:
    """Get human-readable file type from extension"""
    type_map = {
        ".xlsx": "Excel Spreadsheet",
        ".xls": "Excel Spreadsheet (Legacy)",
        ".txt": "Text File",
        ".md": "Markdown Document",
        ".json": "JSON Data",
        ".pdf": "PDF Document",
        ".csv": "CSV Data",
        ".zip": "ZIP Archive",
        ".png": "PNG Image",
        ".jpg": "JPEG Image",
        ".jpeg": "JPEG Image"
    }
    return type_map.get(extension.lower(), "Unknown File Type")

def get_file_category(filename: str) -> str:
    """Categorize files based on their purpose"""
    filename_lower = filename.lower()
    
    if "_parts.xlsx" in filename_lower:
        return "1_main_output"
    elif "_extracted.txt" in filename_lower:
        return "2_extracted_text"
    elif "_extracted.md" in filename_lower:
        return "3_formatted_text"
    elif "_ocr.json" in filename_lower:
        return "4_debug_data"
    elif filename_lower.endswith(".zip"):
        return "5_archives"
    else:
        return "6_other"

def get_file_category_for_download(filename: str) -> str:
    """Get file category for download URL routing"""
    filename_lower = filename.lower()
    
    if filename_lower.endswith('.xlsx') or filename_lower.endswith('.xls'):
        return "excel"
    elif filename_lower.endswith('.txt'):
        return "text"
    elif filename_lower.endswith('.md'):
        return "markdown"
    elif filename_lower.endswith('.json'):
        return "json"
    elif filename_lower.endswith('.zip'):
        return "archive"
    else:
        return "file"

def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def ensure_directory_exists(path: Path) -> Path:
    """Ensure directory exists, create if it doesn't"""
    path.mkdir(parents=True, exist_ok=True)
    return path

def safe_filename(filename: str) -> str:
    """Make filename safe for filesystem"""
    # Remove or replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    # Ensure it's not empty
    if not filename:
        filename = "unnamed_file"
    
    return filename

def get_disk_usage(directory: Path) -> Dict[str, Any]:
    """Get disk usage information for a directory"""
    try:
        total_size = 0
        file_count = 0
        
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
                file_count += 1
        
        return {
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_count": file_count,
            "formatted_size": format_file_size(total_size)
        }
    except Exception:
        return {
            "total_size_bytes": 0,
            "total_size_mb": 0,
            "file_count": 0,
            "formatted_size": "0 B"
        }

def validate_upload_file(file) -> bool:
    """Validate uploaded file"""
    # Check file size (max 50MB)
    max_size = 50 * 1024 * 1024  # 50MB
    
    # Note: This is a simplified check. In production, you'd want more thorough validation
    if hasattr(file, 'size') and file.size > max_size:
        return False
    
    # Check file extension
    if not file.filename.lower().endswith('.pdf'):
        return False
    
    return True

def create_processing_summary(result_data: Dict[str, Any]) -> str:
    """Create a human-readable processing summary"""
    summary_parts = []
    
    if "original_filename" in result_data:
        summary_parts.append(f"📄 File: {result_data['original_filename']}")
    
    if "processing_time" in result_data:
        summary_parts.append(f"⏱️ Time: {result_data['processing_time']}s")
    
    if "records_extracted" in result_data:
        summary_parts.append(f"📊 Records: {result_data['records_extracted']}")
    
    if "pages_processed" in result_data:
        summary_parts.append(f"📑 Pages: {result_data['pages_processed']}")
    
    if "extracted_text_length" in result_data:
        text_length = result_data['extracted_text_length']
        summary_parts.append(f"📝 Text: {text_length:,} chars")
    
    return " | ".join(summary_parts)