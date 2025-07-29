import pandas as pd
import os
from .openai_loop import generate_all_records

def save_to_excel(records, output_path):
    """Save records to Excel file"""
    df = pd.DataFrame(records)
    df.to_excel(output_path, index=False)
    print(f"✅ Excel saved to: {output_path}")

def process_extracted_text(text_file_path, output_dir="outputs"):
    """
    Process extracted text to generate part records and save to Excel
    
    Args:
        text_file_path (str): Path to the extracted text file
        output_dir (str): Directory to save output files
    
    Returns:
        tuple: (records, excel_output_path)
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Read the extracted text
    print(f"📖 Reading extracted text from: {text_file_path}")
    with open(text_file_path, "r", encoding="utf-8") as f:
        drawing_text = f.read()
    
    # Generate records using AI
    print("🤖 Processing text with AI to extract part records...")
    records = generate_all_records(drawing_text)
    
    # Generate output path
    base_name = os.path.splitext(os.path.basename(text_file_path))[0]
    # Remove '_extracted' suffix if present
    if base_name.endswith('_extracted'):
        base_name = base_name[:-10]
    
    excel_output_path = os.path.join(output_dir, f"{base_name}_parts.xlsx")
    
    # Save to Excel
    save_to_excel(records, excel_output_path)
    
    return records, excel_output_path

if __name__ == "__main__":
    # For backward compatibility
    process_extracted_text("output.txt")
