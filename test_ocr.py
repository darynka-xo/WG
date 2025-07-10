#!/usr/bin/env python3
"""
Test script for enhanced OCR functionality
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from ocr_config import OCREnhancer
from PIL import Image
import numpy as np

def test_table_detection():
    """Test table detection functionality"""
    print("Testing table detection...")
    
    # Create a simple test image that looks like a table
    # This is a basic test - in real usage, you'd use actual table images
    test_img = np.ones((200, 400), dtype=np.uint8) * 255  # White background
    
    # Add some horizontal lines (table borders)
    test_img[50:52, :] = 0  # Horizontal line
    test_img[100:102, :] = 0  # Horizontal line
    test_img[150:152, :] = 0  # Horizontal line
    
    # Add some vertical lines
    test_img[:, 100:102] = 0  # Vertical line
    test_img[:, 200:202] = 0  # Vertical line
    test_img[:, 300:302] = 0  # Vertical line
    
    # Convert to PIL Image
    pil_img = Image.fromarray(test_img)
    
    # Test table detection
    is_table = OCREnhancer.is_likely_table(pil_img)
    print(f"Table detection result: {is_table}")
    
    return is_table

def test_text_quality_scoring():
    """Test text quality scoring"""
    print("\nTesting text quality scoring...")
    
    # Test cases
    test_cases = [
        ("Simple text", "This is a simple text"),
        ("Table-like text", "Name\tAge\tCity\nJohn\t25\tNYC\nJane\t30\tLA"),
        ("Numbered list", "1. First item\n2. Second item\n3. Third item"),
        ("Empty text", ""),
        ("Short text", "Hi"),
        ("Table with numbers", "Product\tPrice\tStock\nApple\t$1.99\t100\nOrange\t$2.49\t75")
    ]
    
    for name, text in test_cases:
        score = OCREnhancer._score_text_quality(text)
        print(f"{name}: {score:.2f}")

def test_enhancement_methods():
    """Test image enhancement methods"""
    print("\nTesting image enhancement methods...")
    
    # Create a test image
    test_img = np.ones((100, 200), dtype=np.uint8) * 255
    test_img[20:80, 50:150] = 0  # Add some dark area
    
    pil_img = Image.fromarray(test_img)
    
    # Test basic enhancement
    enhanced = OCREnhancer.enhance_for_table(pil_img)
    print(f"Basic enhancement: {enhanced.size}")
    
    # Test advanced enhancement
    enhanced_advanced = OCREnhancer.enhance_for_table_advanced(pil_img)
    print(f"Advanced enhancement: {enhanced_advanced.size}")

def test_optimized_configs():
    """Test optimized OCR configurations"""
    print("\nTesting optimized OCR configurations...")
    
    configs = OCREnhancer.get_optimized_configs()
    print(f"Number of configurations: {len(configs)}")
    
    for i, config in enumerate(configs):
        print(f"Config {i+1}: {config['name']}")

if __name__ == "__main__":
    print("Enhanced OCR Test Suite")
    print("=" * 40)
    
    try:
        test_table_detection()
        test_text_quality_scoring()
        test_enhancement_methods()
        test_optimized_configs()
        
        print("\n" + "=" * 40)
        print("All tests completed successfully!")
        
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc() 