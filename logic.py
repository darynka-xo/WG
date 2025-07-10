import os
import numpy as np
from PIL import Image
from pathlib import Path
import pytesseract
from pytesseract import Output
import cv2
from ultralytics import YOLO
from ultralyticsplus import render_result
from pdf2image import convert_from_path
from typing import Dict, List, Any
import base64
from io import BytesIO
from ocr_config import OCREnhancer

class PDFProcessor:
    def __init__(self):
        # Configuration
        self.MODEL_PATH = 'best.pt'
        self.RESULT_DIR = Path('results')
        
        # Windows-specific paths (commented out for Linux)
        # self.TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        # self.POPPLER_PATH = r'C:\poppler-24.08.0\Library\bin'
        
        # Set tesseract path (not needed on Linux - uses system installation)
        # pytesseract.pytesseract.tesseract_cmd = self.TESSERACT_CMD
        
        # Load YOLO model
        self.model = YOLO(self.MODEL_PATH)
        self.model.overrides['conf'] = 0.25
        self.model.overrides['iou'] = 0.45
        self.model.overrides['agnostic_nms'] = False
        self.model.overrides['max_det'] = 1000
        
        # Optimize for CPU if no GPU available
        import torch
        if not torch.cuda.is_available():
            self.model.overrides['device'] = 'cpu'
            # Reduce image size for faster CPU processing
            self.model.overrides['imgsz'] = 640
    
    def process_pdf(self, pdf_path: str, upload_id: str) -> Dict[str, Any]:
        """Process PDF and return results data"""
        # Convert PDF to images with higher DPI for better OCR
        images = convert_from_path(
            pdf_path, 
            dpi=400,  # Increased from 300
            fmt='png',
            thread_count=4,
            use_pdftocairo=True,  # Better rendering
            grayscale=False
        )
        
        # Create output directory
        output_dir = self.RESULT_DIR / upload_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results_data = {
            "upload_id": upload_id,
            "total_pages": len(images),
            "pages": []
        }
        
        # Process each page
        for page_num, page_img in enumerate(images, 1):
            page_data = self._process_page(page_img, page_num, output_dir)
            results_data["pages"].append(page_data)
        
        return results_data
    
    def _process_page(self, page_img: Image.Image, page_num: int, output_dir: Path) -> Dict[str, Any]:
        """Process single page"""
        page_folder = output_dir / f'page_{page_num}'
        page_folder.mkdir(exist_ok=True)
        
        # Save original page
        page_path = page_folder / 'page.png'
        page_img.save(page_path)
        
        # Create thumbnail for preview
        thumbnail = self._create_thumbnail(page_img)
        thumb_path = page_folder / 'thumbnail.png'
        thumbnail.save(thumb_path)
        
        # YOLO detection
        results = self.model.predict(page_img)
        
        # Render detection result
        rendered = render_result(model=self.model, image=page_img, result=results[0])
        rendered_path = page_folder / 'yolo_result.jpg'
        rendered.save(rendered_path)
        
        # Create detection thumbnail
        detection_thumb = self._create_thumbnail(rendered)
        detection_thumb_path = page_folder / 'yolo_thumbnail.jpg'
        detection_thumb.save(detection_thumb_path)
        
        # Process detections
        detections = []
        for i, box in enumerate(results[0].boxes.data):
            detection_data = self._process_detection(page_img, box, i, page_folder)
            detections.append(detection_data)
        
        return {
            "page_number": page_num,
            "original": {
                "full": f"page_{page_num}/page.png",
                "thumbnail": f"page_{page_num}/thumbnail.png"
            },
            "detection": {
                "full": f"page_{page_num}/yolo_result.jpg",
                "thumbnail": f"page_{page_num}/yolo_thumbnail.jpg"
            },
            "detections": detections
        }
    
    def _process_detection(self, page_img: Image.Image, box, index: int, page_folder: Path) -> Dict[str, Any]:
        """Process single detection"""
        x1, y1, x2, y2, *_ = [int(v.item()) for v in box]
        
        # Crop region
        cropped_np = np.array(page_img)[y1:y2, x1:x2]
        cropped_img = Image.fromarray(cropped_np)
        
        # Detect if this is likely a table
        is_table = OCREnhancer.is_likely_table(cropped_img)
        
        # Enhanced preprocessing for better OCR
        processed_img = OCREnhancer.enhance_for_table(cropped_img)
        processed_img_advanced = OCREnhancer.enhance_for_table_advanced(cropped_img)
        
        # Save cropped image
        crop_filename = f'crop_{index + 1}.png'
        crop_path = page_folder / crop_filename
        cropped_img.save(crop_path)
        
        # Save processed images for debugging
        processed_filename = f'crop_{index + 1}_processed.png'
        processed_path = page_folder / processed_filename
        processed_img.save(processed_path)
        
        processed_advanced_filename = f'crop_{index + 1}_processed_advanced.png'
        processed_advanced_path = page_folder / processed_advanced_filename
        processed_img_advanced.save(processed_advanced_path)
        
        # Create thumbnail
        crop_thumb = self._create_thumbnail(cropped_img, size=(200, 200))
        crop_thumb_filename = f'crop_{index + 1}_thumb.png'
        crop_thumb_path = page_folder / crop_thumb_filename
        crop_thumb.save(crop_thumb_path)
        
        # OCR with multiple configs for tables
        text_results = []
        
        # If detected as table, prioritize table-specific methods
        if is_table:
            # Try structured table extraction first
            try:
                table_text = OCREnhancer.extract_table_with_structure(processed_img)
                if table_text and len(table_text) > 20:
                    text_results.append(("Structured Table", table_text))
            except Exception as e:
                print(f"Structured extraction failed: {e}")
            
            # Try structured extraction with advanced preprocessing
            try:
                table_text_advanced = OCREnhancer.extract_table_with_structure(processed_img_advanced)
                if table_text_advanced and len(table_text_advanced) > 20:
                    text_results.append(("Structured Table (Advanced)", table_text_advanced))
            except Exception as e:
                print(f"Advanced structured extraction failed: {e}")
            
            # Try table-specific OCR configurations
            table_configs = [
                {
                    "name": "Table Specific",
                    "config": "--psm 6 --oem 3 -c preserve_interword_spaces=1 -c textord_tabfind_find_tables=1 -c textord_tablefind_recognize_tables=1 -c textord_min_xheight=15"
                },
                {
                    "name": "High DPI Table",
                    "config": "--psm 6 --oem 3 --dpi 300 -c tessedit_char_whitelist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-.,/() ' -c preserve_interword_spaces=1 -c textord_tabfind_find_tables=1 -c textord_tablefind_recognize_tables=1"
                }
            ]
            
            for ocr_config in table_configs:
                try:
                    text = pytesseract.image_to_string(processed_img, config=ocr_config["config"], lang='eng').strip()
                    if text and len(text) > 10:
                        processed_text = OCREnhancer.process_table_text(text)
                        text_results.append((ocr_config["name"], processed_text))
                except Exception as e:
                    print(f"Table OCR config {ocr_config['name']} failed: {e}")
                
                try:
                    text = pytesseract.image_to_string(processed_img_advanced, config=ocr_config["config"], lang='eng').strip()
                    if text and len(text) > 10:
                        processed_text = OCREnhancer.process_table_text(text)
                        text_results.append((f"{ocr_config['name']} (Advanced)", processed_text))
                except Exception as e:
                    print(f"Advanced table OCR config {ocr_config['name']} failed: {e}")
        
        # Try general OCR configurations
        for ocr_config in OCREnhancer.get_optimized_configs():
            try:
                text = pytesseract.image_to_string(processed_img, config=ocr_config["config"], lang='eng').strip()
                if text and len(text) > 10:
                    processed_text = OCREnhancer.process_table_text(text)
                    text_results.append((ocr_config["name"], processed_text))
            except Exception as e:
                print(f"OCR config {ocr_config['name']} failed: {e}")
            
            try:
                text = pytesseract.image_to_string(processed_img_advanced, config=ocr_config["config"], lang='eng').strip()
                if text and len(text) > 10:
                    processed_text = OCREnhancer.process_table_text(text)
                    text_results.append((f"{ocr_config['name']} (Advanced)", processed_text))
            except Exception as e:
                print(f"Advanced OCR config {ocr_config['name']} failed: {e}")
        
        # Also try with original image for comparison
        try:
            text_original = pytesseract.image_to_string(cropped_img, config="--psm 6 --oem 3", lang='eng').strip()
            if text_original:
                text_results.append(("Original Image", text_original))
        except:
            pass
        
        # Select the best result
        best_text = OCREnhancer.select_best_result(text_results)
        
        # Save the best result only
        text_filename = None
        if best_text:
            text_filename = f'crop_{index + 1}_text.txt'
            text_path = page_folder / text_filename
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(best_text)
        
        return {
            "index": index + 1,
            "bbox": [x1, y1, x2, y2],
            "is_table": is_table,
            "image": {
                "full": crop_filename,
                "thumbnail": crop_thumb_filename,
                "processed": processed_filename,
                "processed_advanced": processed_advanced_filename
            },
            "text": {
                "content": best_text if best_text else None,
                "file": text_filename
            }
        }
    
    def _preprocess_for_ocr(self, img: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results"""
        import cv2
        
        # Convert PIL to OpenCV format
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive thresholding for better text extraction
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY, 11, 2)
        
        # Denoise
        denoised = cv2.medianBlur(thresh, 1)
        
        # Morphological operations to clean up
        kernel = np.ones((1,1), np.uint8)
        cleaned = cv2.morphologyEx(denoised, cv2.MORPH_CLOSE, kernel)
        
        # Invert if needed (dark text on light background)
        # Check if image is mostly white (inverted)
        if np.mean(cleaned) > 127:
            cleaned = cv2.bitwise_not(cleaned)
        
        # Scale up for better OCR (if image is small)
        height, width = cleaned.shape
        if width < 300 or height < 300:
            scale_factor = max(300/width, 300/height)
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            cleaned = cv2.resize(cleaned, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # Convert back to PIL
        return Image.fromarray(cleaned)
    
    def _reconstruct_table_from_tsv(self, tsv_data: Dict) -> str:
        """Reconstruct table structure from TSV data"""
        if not tsv_data['text']:
            return ""
        
        # Group by line numbers
        lines = {}
        for i, text in enumerate(tsv_data['text']):
            if text.strip():
                line_num = tsv_data['line_num'][i]
                if line_num not in lines:
                    lines[line_num] = []
                lines[line_num].append({
                    'text': text,
                    'left': tsv_data['left'][i],
                    'word_num': tsv_data['word_num'][i]
                })
        
        # Sort words in each line by position
        result_lines = []
        for line_num in sorted(lines.keys()):
            words = sorted(lines[line_num], key=lambda x: x['left'])
            line_text = ' '.join(word['text'] for word in words)
            result_lines.append(line_text)
        
        return '\n'.join(result_lines)
    
    def _create_thumbnail(self, img: Image.Image, size=(300, 300)) -> Image.Image:
        """Create thumbnail preserving aspect ratio"""
        img_copy = img.copy()
        img_copy.thumbnail(size, Image.Resampling.LANCZOS)
        return img_copy
