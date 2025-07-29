import json
import os
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
from .text_constructor import reconstruct_text
from .text_constructor_md import json_to_markdown

def extract_text_from_pdf(pdf_path, output_dir="outputs"):
    """
    Extract text from PDF using OCR and save to both .txt and .md formats
    
    Args:
        pdf_path (str): Path to the input PDF file
        output_dir (str): Directory to save output files
    
    Returns:
        tuple: (text_output, json_output, output_txt_path, output_md_path)
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get base name for output files
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    
    # Initialize OCR model
    print(f"🔍 Loading OCR model...")
    model = ocr_predictor(pretrained=True)
    
    # Load and process PDF
    print(f"📄 Processing PDF: {pdf_path}")
    doc = DocumentFile.from_pdf(pdf_path)
    result = model(doc)
    
    # Export to JSON
    json_output = result.export()
    
    # Reconstruct text
    print("📝 Reconstructing text...")
    text_output = reconstruct_text(json_output)
    
    # Generate output paths
    output_txt_path = os.path.join(output_dir, f"{base_name}_extracted.txt")
    output_md_path = os.path.join(output_dir, f"{base_name}_extracted.md")
    output_json_path = os.path.join(output_dir, f"{base_name}_ocr.json")
    
    # Save text output
    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write(text_output)
    print(f"✅ Text saved to: {output_txt_path}")
    
    # Generate and save markdown
    markdown_output = json_to_markdown(json_output)
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(markdown_output)
    print(f"✅ Markdown saved to: {output_md_path}")
    
    # Save JSON output for debugging
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=2)
    print(f"✅ JSON saved to: {output_json_path}")
    
    return text_output, json_output, output_txt_path, output_md_path

if __name__ == "__main__":
    # For backward compatibility
    extract_text_from_pdf("HL79.pdf")
