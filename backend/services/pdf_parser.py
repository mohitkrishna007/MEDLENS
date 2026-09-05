import os
from PIL import Image

def extract_text_from_file(file_path: str) -> dict:
    """
    Robust PDF and Image text extraction pipeline.
    Strategy:
    1. PyMuPDF (fitz) with layout sort=True & block extraction.
    2. Fallback to PyPDF if PyMuPDF unavailable.
    3. Fallback to OCR if extracted text is empty or < 50 characters.
    4. Diagnostic logging.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    filename = os.path.basename(file_path)
    ext = os.path.splitext(file_path)[1].lower()
    ocr_used = False
    full_text = ""
    pages = []
    page_count = 1

    print(f"\n==========================================")
    print(f"[PDF Processing Pipeline] PDF received: {filename}")

    if ext == ".pdf":
        # 1. Try PyMuPDF (fitz)
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            page_count = len(doc)
            
            for idx, page in enumerate(doc):
                # Extract sorted text blocks to preserve column order
                blocks = page.get_text("blocks", sort=True)
                block_texts = []
                for b in blocks:
                    # b format: (x0, y0, x1, y1, text, block_no, block_type)
                    if len(b) >= 5 and b[4].strip():
                        block_texts.append(b[4].strip())
                
                page_txt = "\n".join(block_texts)
                if not page_txt.strip():
                    page_txt = page.get_text("text", sort=True) or ""
                    
                pages.append({"page_number": idx + 1, "text": page_txt})
                full_text += f"\n--- Page {idx + 1} ---\n" + page_txt

            doc.close()
        except Exception as err_mupdf:
            print(f"[PDF Pipeline Notice] PyMuPDF extraction warning: {err_mupdf}. Falling back to PyPDF...")
            try:
                from pypdf import PdfReader
                reader = PdfReader(file_path)
                page_count = len(reader.pages)
                full_text = ""
                pages = []
                for idx, page in enumerate(reader.pages):
                    txt = page.extract_text() or ""
                    pages.append({"page_number": idx + 1, "text": txt})
                    full_text += f"\n--- Page {idx + 1} ---\n" + txt
            except Exception as err_pypdf:
                print(f"[PDF Pipeline Error] PyPDF failed: {err_pypdf}")

        # 2. OCR Fallback if text is empty or insufficient (< 50 chars)
        clean_text = full_text.strip()
        if len(clean_text) < 50:
            print(f"[PDF Pipeline Notice] Insufficient text extracted ({len(clean_text)} chars). Attempting OCR fallback...")
            ocr_text = _attempt_ocr(file_path)
            if ocr_text and len(ocr_text.strip()) > len(clean_text):
                full_text = ocr_text
                ocr_used = True
                print(f"[PDF Pipeline Notice] OCR fallback produced {len(full_text)} characters.")

        # 3. Final Verification & Logging
        final_clean = full_text.strip()
        print(f"[PDF Processing Pipeline] Pages detected: {page_count}")
        print(f"[PDF Processing Pipeline] Text extraction characters: {len(final_clean)}")
        print(f"[PDF Processing Pipeline] OCR used: {'yes' if ocr_used else 'no'}")
        print(f"[PDF Processing Pipeline] Extracted text preview:\n{final_clean[:300]}")
        print(f"==========================================\n")

        if len(final_clean) < 10:
            raise ValueError(f"Unable to extract readable text from PDF '{filename}'. The file may be image-only without OCR layers, password protected, or corrupt.")

        return {
            "text": final_clean,
            "page_count": page_count,
            "pages": pages,
            "ocr_used": ocr_used
        }

    elif ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]:
        try:
            img = Image.open(file_path)
            ocr_text = _attempt_ocr(file_path)
            txt = ocr_text if ocr_text else f"[Scanned Image: {filename} ({img.size[0]}x{img.size[1]})]"
            ocr_used = bool(ocr_text)
            
            print(f"[Image Processing Pipeline] Image received: {filename}")
            print(f"[Image Processing Pipeline] OCR used: {'yes' if ocr_used else 'no'}")
            print(f"[Image Processing Pipeline] Extracted text preview:\n{txt[:300]}")
            
            return {
                "text": txt,
                "page_count": 1,
                "pages": [{"page_number": 1, "text": txt}],
                "ocr_used": ocr_used
            }
        except Exception as e:
            raise ValueError(f"Failed to process image file '{filename}': {str(e)}")

    elif ext in [".txt", ".csv"]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            txt = f.read()
        return {
            "text": txt,
            "page_count": 1,
            "pages": [{"page_number": 1, "text": txt}],
            "ocr_used": False
        }
    else:
        raise ValueError(f"Unsupported file extension: {ext}")

def _attempt_ocr(file_path: str) -> str:
    """Attempts OCR on PDF or Image file using pytesseract or fitz OCR if installed."""
    try:
        import pytesseract
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            import fitz
            doc = fitz.open(file_path)
            ocr_pages = []
            for page in doc:
                pix = page.get_pixmap(dpi=150)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                txt = pytesseract.image_to_string(img)
                ocr_pages.append(txt)
            doc.close()
            return "\n".join(ocr_pages)
        else:
            img = Image.open(file_path)
            return pytesseract.image_to_string(img)
    except Exception as e:
        print(f"[OCR Notice] pytesseract OCR unavailable or failed: {e}")
        return ""
