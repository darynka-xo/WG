"""
OCR Configuration and Enhancement Module
"""

import cv2
import numpy as np
from PIL import Image
import pytesseract
from typing import Tuple, Optional, List, Dict
import re

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
    def enhance_for_table_advanced(img: Image.Image) -> Image.Image:
        """Advanced preprocessing with line removal for tables"""
        # Convert to numpy array
        img_np = np.array(img)
        
        # Convert to grayscale if needed
        if len(img_np.shape) == 3:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_np
        
        # 1. Resize for better processing
        height, width = gray.shape
        min_dimension = 2000
        if width < min_dimension or height < min_dimension:
            scale = min_dimension / min(width, height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # 2. Remove table lines first
        gray_no_lines = OCREnhancer.remove_lines(gray)
        
        # 3. Apply advanced preprocessing
        # Sharpening
        kernel_sharpen = np.array([[-1,-1,-1],
                                  [-1, 9,-1],
                                  [-1,-1,-1]])
        sharpened = cv2.filter2D(gray_no_lines, -1, kernel_sharpen)
        
        # 4. Bilateral filter for edge-preserving smoothing
        smoothed = cv2.bilateralFilter(sharpened, 9, 75, 75)
        
        # 5. Adaptive thresholding
        binary = cv2.adaptiveThreshold(smoothed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY, 15, 2)
        
        # 6. Invert if needed
        if np.mean(binary) < 127:
            binary = cv2.bitwise_not(binary)
        
        # 7. Morphological operations to clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # 8. Remove small noise
        cleaned = cv2.medianBlur(cleaned, 3)
        
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
            },
            {
                "name": "Table Specific",
                "config": "--psm 6 --oem 3 -c preserve_interword_spaces=1 -c textord_tabfind_find_tables=1 -c textord_tablefind_recognize_tables=1 -c textord_min_xheight=15"
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
            line = line.replace('«', '.')  # Another common mistake
            line = line.replace('0', 'O')  # Common confusion
            line = line.replace('1', 'l')  # Common confusion
            
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
    
    @staticmethod
    def select_best_result(text_results: List[Tuple[str, str]]) -> str:
        """Select the best OCR result from multiple attempts"""
        if not text_results:
            return ""
        
        # Score each result
        scored_results = []
        for method_name, text in text_results:
            score = OCREnhancer._score_text_quality(text)
            scored_results.append((score, method_name, text))
        
        # Sort by score (highest first)
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        # Return the best result
        return scored_results[0][2]
    
    @staticmethod
    def is_likely_table(img: Image.Image) -> bool:
        """Detect if the image is likely to contain a table"""
        # Convert to numpy array
        img_np = np.array(img)
        
        # Convert to grayscale if needed
        if len(img_np.shape) == 3:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_np
        
        # 1. Check for horizontal lines (table borders)
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
        horizontal_line_ratio = np.sum(horizontal_lines > 0) / (gray.shape[0] * gray.shape[1])
        
        # 2. Check for vertical lines
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel)
        vertical_line_ratio = np.sum(vertical_lines > 0) / (gray.shape[0] * gray.shape[1])
        
        # 3. Check aspect ratio (tables are usually wider than tall)
        aspect_ratio = gray.shape[1] / gray.shape[0]
        
        # 4. Check for regular spacing (table cells)
        # Use edge detection to find potential cell boundaries
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (gray.shape[0] * gray.shape[1])
        
        # 5. Check for text density
        # Apply threshold to get binary image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        text_density = np.sum(binary == 0) / (gray.shape[0] * gray.shape[1])  # Black pixels
        
        # Scoring system
        score = 0
        
        # Line detection score
        if horizontal_line_ratio > 0.01:  # At least 1% horizontal lines
            score += 2
        if vertical_line_ratio > 0.01:    # At least 1% vertical lines
            score += 2
        
        # Aspect ratio score (tables are usually wider)
        if 1.2 < aspect_ratio < 4.0:
            score += 1
        elif aspect_ratio > 4.0:
            score += 0.5
        
        # Edge density score (tables have many edges)
        if 0.05 < edge_density < 0.3:
            score += 1
        
        # Text density score (tables have moderate text density)
        if 0.1 < text_density < 0.7:
            score += 1
        
        # Size score (tables are usually not too small)
        if gray.shape[0] > 100 and gray.shape[1] > 100:
            score += 1
        
        # Return True if score indicates table
        return score >= 3
    
    @staticmethod
    def _score_text_quality(text: str) -> float:
        """Score text quality for table detection"""
        if not text or len(text.strip()) < 10:
            return 0.0
        
        score = 0.0
        
        # Length score (prefer longer, meaningful text)
        score += min(len(text) / 100.0, 2.0)
        
        # Line count score (tables should have multiple lines)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        score += min(len(lines) / 5.0, 2.0)
        
        # Tab/column score (tables often have tab-separated data)
        tab_count = text.count('\t')
        score += min(tab_count / 3.0, 2.0)
        
        # Number score (tables often contain numbers)
        number_count = len(re.findall(r'\d+', text))
        score += min(number_count / 5.0, 1.0)
        
        # Word count score
        word_count = len(text.split())
        score += min(word_count / 10.0, 2.0)
        
        # Penalty for too many special characters
        special_chars = len(re.findall(r'[^\w\s\t.,]', text))
        if special_chars > len(text) * 0.1:  # More than 10% special chars
            score -= 1.0
        
        # Bonus for structured appearance (consistent line lengths)
        if len(lines) > 2:
            line_lengths = [len(line) for line in lines]
            length_variance = np.var(line_lengths) if len(line_lengths) > 1 else 0
            if length_variance < 100:  # Low variance indicates structured text
                score += 1.0
        
        # Bonus for table-like patterns
        # Check for repeated patterns (like headers)
        if len(lines) > 3:
            # Check if first line is different (header)
            first_line_words = len(lines[0].split())
            other_lines_words = [len(line.split()) for line in lines[1:]]
            if other_lines_words and all(abs(wc - first_line_words) <= 1 for wc in other_lines_words):
                score += 1.5  # Consistent column structure
        
        # Bonus for alphanumeric content (tables often mix text and numbers)
        alpha_count = len(re.findall(r'[a-zA-Z]', text))
        num_count = len(re.findall(r'\d', text))
        if alpha_count > 0 and num_count > 0:
            score += 0.5
        
        return max(score, 0.0)
