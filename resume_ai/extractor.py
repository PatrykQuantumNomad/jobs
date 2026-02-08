"""PDF text extraction as structured Markdown.

Uses ``pymupdf4llm`` to convert a PDF resume into Markdown that preserves
headings, bullet points, and formatting -- suitable for feeding into an LLM
as context for resume tailoring.
"""

from pathlib import Path

import pymupdf4llm


def extract_resume_text(pdf_path: str | Path) -> str:
    """Extract text from a PDF file and return it as Markdown.

    Parameters
    ----------
    pdf_path:
        Path to the PDF file.  Accepts both ``str`` and ``Path`` objects.

    Returns
    -------
    str
        Markdown representation of the PDF content.

    Raises
    ------
    FileNotFoundError
        If the PDF file does not exist at the given path.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"Resume PDF not found: {path}")
    result = pymupdf4llm.to_markdown(str(path))
    if isinstance(result, list):
        return "\n".join(str(page) for page in result)
    return result
