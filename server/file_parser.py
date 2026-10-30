import io
import docx
import PyPDF2
from fastapi import HTTPException, UploadFile, status


async def extract_text_from_upload(file: UploadFile) -> tuple[str, str]:
    """
    Extracts UTF-8 text from an uploaded .txt, .docx, or .pdf file.
    Returns (extracted_text, status_message).
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file uploaded.",
        )

    filename = file.filename.lower()
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if filename.endswith(".txt"):
        for encoding in ("utf-8", "utf-8-sig", "utf-16", "latin-1"):
            try:
                text = raw_bytes.decode(encoding).strip()
                if text:
                    return text, f"Extracted {len(text)} characters from '{file.filename}'."
            except Exception:
                continue
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not decode the text file. Please upload a valid UTF-8 text file.",
        )

    elif filename.endswith(".docx"):
        try:
            doc = docx.Document(io.BytesIO(raw_bytes))
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
            text = "\n\n".join(paragraphs)
            if not text:
                raise ValueException("No text paragraphs found in Word document.")
            return text, f"Extracted {len(paragraphs)} paragraph(s) from '{file.filename}'."
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to extract text from Word (.docx) file: {e}",
            )

    elif filename.endswith(".pdf"):
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(raw_bytes))
            pages_text = []
            for page in reader.pages:
                pt = page.extract_text()
                if pt and pt.strip():
                    pages_text.append(pt.strip())
            text = "\n\n".join(pages_text)
            if not text:
                raise ValueError("No selectable text found in PDF file.")
            return text, f"Extracted text from {len(pages_text)} PDF page(s) in '{file.filename}'."
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to extract text from PDF file: {e}",
            )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload a .txt, .docx, or .pdf file.",
        )


def create_docx_bytes(text: str) -> io.BytesIO:
    """Creates an in-memory Word (.docx) document from normalized Tamil Unicode text."""
    doc = docx.Document()
    for para in (text or "").split("\n\n"):
        if para.strip():
            doc.add_paragraph(para.strip())
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

