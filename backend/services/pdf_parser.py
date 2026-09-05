import os
from pypdf import PdfReader
from PIL import Image

def extract_text_from_file(file_path: str) -> dict:
    """
    Extracts text, page count, and metadata from uploaded PDF or Image file.
    Returns: {"text": str, "page_count": int, "pages": list[dict]}
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".pdf":
        try:
            reader = PdfReader(file_path)
            pages = []
            full_text = ""
            for idx, page in enumerate(reader.pages):
                txt = page.extract_text() or ""
                pages.append({"page_number": idx + 1, "text": txt})
                full_text += f"\n--- Page {idx + 1} ---\n" + txt
            
            return {
                "text": full_text.strip(),
                "page_count": len(reader.pages),
                "pages": pages
            }
        except Exception as e:
            # Fallback handling
            return {"text": f"[PDF Parsing Error: {str(e)}]", "page_count": 1, "pages": []}
            
    elif ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]:
        try:
            # For image files, extract text snippet or metadata
            img = Image.open(file_path)
            txt = f"[Image File: {os.path.basename(file_path)} - Resolution {img.size[0]}x{img.size[1]}]"
            return {
                "text": txt,
                "page_count": 1,
                "pages": [{"page_number": 1, "text": txt}]
            }
        except Exception as e:
            return {"text": f"[Image Processing Error: {str(e)}]", "page_count": 1, "pages": []}
            
    elif ext in [".txt", ".csv"]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            txt = f.read()
        return {
            "text": txt,
            "page_count": 1,
            "pages": [{"page_number": 1, "text": txt}]
        }
    else:
        raise ValueError(f"Unsupported file extension: {ext}")
