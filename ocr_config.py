"""
OCR Configuration and Enhancement Module
"""

import cv2
import numpy as np
from PIL import Image
import pytesseract
from typing import Tuple, Optional

class OCREnhancer:
    """Enhanced OCR processing for table data"""
    
    @staticmethod
    def enhance_for_table(img: Image.Image) -> Image.Image:
        """Enhanced preprocessing specifically for tables"""
        # Convert to numpy array
        img_np = np.array(img)
        
        # Convert to grayscale if needed
        if len(img_np.shape) == 3:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_np
        
        # 1. Resize if too small - INCREASED for better OCR
        height, width = gray.shape
        min_dimension = 2000  # Increased from 1000
        if width < min_dimension or height < min_dimension:
            scale = min_dimension / min(width, height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # 2. Apply sharpening filter
        kernel_sharpen = np.array([[-1,-1,-1],
                                  [-1, 9,-1],
                                  [-1,-1,-1]])
        sharpened = cv2.filter2D(gray, -1, kernel_sharpen)
        
        # 3. Noise reduction
        denoised = cv2.fastNlMeansDenoising(sharpened, None, 10, 7, 21)
        
        # 4. Adaptive thresholding for better results with varying lighting
        binary = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY, 11, 2)
        
        # 5. Invert if needed (white text on black background)
        if np.mean(binary) < 127:
            binary = cv2.bitwise_not(binary)
        
        # 6. Dilation to make text slightly bolder
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        dilated = cv2.dilate(binary, kernel, iterations=1)
        
        # 7. Remove noise with median filter
        cleaned = cv2.medianBlur(dilated, 3)
        
        return Image.fromarray(cleaned)
    
    @staticmethod
    def remove_lines(image: np.ndarray) -> np.ndarray:
        """Remove horizontal and vertical lines from table"""
        # Create kernels
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        
        # Detect lines
        horizontal_lines = cv2.morphologyEx(image, cv2.MORPH_OPEN, horizontal_kernel)
        vertical_lines = cv2.morphologyEx(image, cv2.MORPH_OPEN, vertical_kernel)
        
        # Remove lines
        image_no_h_lines = cv2.subtract(image, horizontal_lines)
        image_no_lines = cv2.subtract(image_no_h_lines, vertical_lines)
        
        # Repair text
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        repaired = cv2.morphologyEx(image_no_lines, cv2.MORPH_CLOSE, kernel)
        
        return repaired
    
    @staticmethod
    def get_optimized_configs():
        """Get list of optimized Tesseract configs for different scenarios"""
        return [
            {
                "name": "High DPI Table",
                "config": "--psm 6 --oem 3 --dpi 300 -c tessedit_char_whitelist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-.,/() ' -c preserve_interword_spaces=1 -c textord_tabfind_find_tables=1 -c textord_tablefind_recognize_tables=1"
            },
            {
                "name": "Table with Structure",
                "config": "--psm 6 --oem 3 -c preserve_interword_spaces=1 -c textord_min_xheight=20 -c textord_occupancy_threshold=0.4"
            },
            {
                "name": "Raw Line Mode",
                "config": "--psm 13 --oem 3 -c preserve_interword_spaces=1"
            },
            {
                "name": "Best Quality",
                "config": "--psm 6 --oem 3 -c tessedit_pageseg_mode=6 -c textord_heavy_nr=1"
            }
        ]
    
    @staticmethod
    def deskew_image(image: np.ndarray) -> np.ndarray:
        """Deskew image to improve OCR accuracy"""
        # Find all black pixels
        coords = np.column_stack(np.where(image > 0))
        
        # Find minimum area rectangle
        angle = cv2.minAreaRect(coords)[-1]
        
        # Adjust angle
        if angle < -45:
            angle = 90 + angle
        
        # Rotate image
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        return rotated
    
    @staticmethod
    def process_table_text(text: str) -> str:
        """Post-process OCR text to improve table formatting"""
        lines = text.strip().split('\n')
        processed_lines = []
        
        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue
            
            # Replace multiple spaces with tabs for better alignment
            # But preserve single spaces within words
            import re
            line = re.sub(r'  +', '\t', line)
            
            # Clean up common OCR errors in tables
            line = line.replace('|', 'I')  # Common OCR mistake
            line = line.replace('°', '.')  # Degree symbol to period
            line = line.replace('»', '.')  # Another common mistake
            
            processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    @staticmethod
    def extract_table_with_structure(img: Image.Image) -> str:
        """Extract table preserving structure using multiple passes"""
        import pytesseract
        
        # First pass: get word positions
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, 
                                        config="--psm 6 --oem 3 -c preserve_interword_spaces=1")
        
        # Group words by line
        lines = {}
        for i in range(len(data['text'])):
            if data['text'][i].strip():
                line_num = data['line_num'][i]
                if line_num not in lines:
                    lines[line_num] = []
                
                lines[line_num].append({
                    'text': data['text'][i],
                    'left': data['left'][i],
                    'width': data['width'][i],
                    'conf': data['conf'][i]
                })
        
        # Sort lines
        sorted_lines = sorted(lines.items())
        
        # Detect column positions
        all_positions = []
        for _, words in sorted_lines:
            for word in words:
                all_positions.append(word['left'])
        
        # Find column boundaries (cluster x positions)
        if all_positions:
            all_positions.sort()
            columns = []
            current_col = [all_positions[0]]
            
            for pos in all_positions[1:]:
                if pos - current_col[-1] > 50:  # Gap threshold
                    columns.append(sum(current_col) / len(current_col))
                    current_col = [pos]
                else:
                    current_col.append(pos)
            
            if current_col:
                columns.append(sum(current_col) / len(current_col))
        else:
            columns = []
        
        # Reconstruct table with proper alignment
        result_lines = []
        for line_num, words in sorted_lines:
            # Sort words by position
            words.sort(key=lambda x: x['left'])
            
            # Assign words to columns
            line_parts = [''] * len(columns)
            for word in words:
                # Find closest column
                if columns:
                    distances = [abs(word['left'] - col) for col in columns]
                    closest_col = distances.index(min(distances))
                    
                    if line_parts[closest_col]:
                        line_parts[closest_col] += ' ' + word['text']
                    else:
                        line_parts[closest_col] = word['text']
            
            # Join with tabs
            result_lines.append('\t'.join(line_parts))
        
        return '\n'.join(result_lines)
