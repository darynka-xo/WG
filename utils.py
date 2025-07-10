import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

def cleanup_old_files(directory: Path, days: int = 7):
    """Remove files older than specified days"""
    if not directory.exists():
        return
    
    cutoff_time = datetime.now() - timedelta(days=days)
    
    for item in directory.iterdir():
        if item.is_file():
            if datetime.fromtimestamp(item.stat().st_mtime) < cutoff_time:
                item.unlink()
        elif item.is_dir():
            if datetime.fromtimestamp(item.stat().st_mtime) < cutoff_time:
                shutil.rmtree(item)

def get_file_info(file_path: Path) -> Dict[str, Any]:
    """Get file information"""
    if not file_path.exists():
        return None
    
    stat = file_path.stat()
    return {
        "name": file_path.name,
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "extension": file_path.suffix.lower()
    }

def format_bytes(size: int) -> str:
    """Format bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

def is_image_file(filename: str) -> bool:
    """Check if file is an image"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    return Path(filename).suffix.lower() in image_extensions

def is_text_file(filename: str) -> bool:
    """Check if file is a text file"""
    text_extensions = {'.txt', '.log', '.md', '.csv'}
    return Path(filename).suffix.lower() in text_extensions