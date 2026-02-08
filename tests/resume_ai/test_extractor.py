"""Unit tests for resume_ai/extractor.py -- extract_resume_text.

Tests cover:
- FileNotFoundError for nonexistent path
- Successful extraction via monkeypatched pymupdf4llm
- List result handling (multi-page PDFs)
"""

import pytest


@pytest.mark.unit
class TestExtractResumeText:
    """Verify extract_resume_text reads PDFs and handles edge cases."""

    def test_file_not_found_raises(self):
        """extract_resume_text raises FileNotFoundError for nonexistent path."""
        from resume_ai.extractor import extract_resume_text

        with pytest.raises(FileNotFoundError, match="Resume PDF not found"):
            extract_resume_text("/nonexistent/path.pdf")

    def test_success_returns_markdown(self, tmp_path, monkeypatch):
        """extract_resume_text returns markdown string from pymupdf4llm."""
        import pymupdf4llm

        monkeypatch.setattr(pymupdf4llm, "to_markdown", lambda path: "# Resume\n\nContent")
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake pdf content")

        from resume_ai.extractor import extract_resume_text

        result = extract_resume_text(pdf_file)
        assert result == "# Resume\n\nContent"

    def test_list_result_joined(self, tmp_path, monkeypatch):
        """When pymupdf4llm returns a list, pages are joined with newlines."""
        import pymupdf4llm

        monkeypatch.setattr(pymupdf4llm, "to_markdown", lambda path: ["page1", "page2"])
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake pdf content")

        from resume_ai.extractor import extract_resume_text

        result = extract_resume_text(pdf_file)
        assert result == "page1\npage2"
