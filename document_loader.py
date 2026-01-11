from PyPDF2 import PdfReader

def load_pdf(file_path_or_fileobj):
    """
    Accepts either a filesystem path (str) or a file-like object (e.g., Flask FileStorage.stream).
    """
    reader = PdfReader(file_path_or_fileobj)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text() or ""
        text += extracted
    return text