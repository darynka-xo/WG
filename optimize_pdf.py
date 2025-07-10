#!/usr/bin/env python3
"""
Optimize PDF conversion for better OCR results
"""

from pdf2image import convert_from_path
import sys
from pathlib import Path

def optimize_pdf_conversion(pdf_path: str, output_dir: str = "optimized_pages"):
    """Convert PDF with optimal settings for OCR"""
    
    Path(output_dir).mkdir(exist_ok=True)
    
    print(f"Converting PDF: {pdf_path}")
    
    # Try different DPI settings
    dpi_settings = [300, 400, 600]
    
    for dpi in dpi_settings:
        print(f"\nConverting with DPI: {dpi}")
        
        try:
            # Convert with high quality settings
            images = convert_from_path(
                pdf_path, 
                dpi=dpi,
                fmt='png',
                thread_count=4,
                use_pdftocairo=True,  # Better quality
                output_folder=output_dir,
                grayscale=False,  # Keep color for now
                size=(None, None),  # Don't resize
                paths_only=False
            )
            
            # Save pages
            for i, img in enumerate(images):
                output_path = Path(output_dir) / f"page_{i+1}_dpi{dpi}.png"
                img.save(output_path, 'PNG', optimize=True, quality=100)
                print(f"  Saved: {output_path}")
                
        except Exception as e:
            print(f"  Error with DPI {dpi}: {e}")
    
    print(f"\nConversion complete! Check {output_dir} folder.")
    print("\nRecommendations:")
    print("1. Use higher DPI (400-600) for small text")
    print("2. Check which DPI gives clearest text")
    print("3. Update logic.py to use optimal DPI")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python optimize_pdf.py <pdf_path>")
        sys.exit(1)
    
    optimize_pdf_conversion(sys.argv[1])
