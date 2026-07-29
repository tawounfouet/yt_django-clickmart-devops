"""
Document processors (pypdf, pdf2image).

Install: pip install pypdf pdf2image
Usage:
    from .processors import extract_metadata, extract_text, generate_preview
"""


def extract_metadata(file_path):
    """Extract page_count, author, is_encrypted."""
    raise NotImplementedError("Install pypdf: pip install pypdf")


def extract_text(file_path):
    """Extract full text from PDF."""
    raise NotImplementedError("Install pypdf: pip install pypdf")


def generate_preview(file_path, output_path, page=0, dpi=150):
    """Generate a PNG preview of the first page."""
    raise NotImplementedError("Install pdf2image: pip install pdf2image")
