"""Unit tests for resume_ai/diff.py -- generate_resume_diff_html and wrap_diff_html.

Tests cover:
- Diff table HTML generation for changed and identical text
- CSS and container wrapping
"""

import pytest

from resume_ai.diff import generate_resume_diff_html, wrap_diff_html


@pytest.mark.unit
class TestGenerateResumeDiffHtml:
    """Verify generate_resume_diff_html produces valid HTML diff tables."""

    def test_returns_table_for_different_text(self):
        """Diff of different text returns HTML containing <table> tags."""
        result = generate_resume_diff_html("line1\nline2", "line1\nline3")
        assert "<table" in result
        assert "</table>" in result

    def test_returns_table_for_identical_text(self):
        """Diff of identical text still returns valid HTML table."""
        text = "Same content\nOn two lines"
        result = generate_resume_diff_html(text, text)
        assert "<table" in result
        assert "</table>" in result

    def test_diff_captures_changes(self):
        """Diff output reflects actual differences (original vs tailored labels)."""
        result = generate_resume_diff_html("original line", "tailored line")
        assert "Original Resume" in result
        assert "Tailored Resume" in result


@pytest.mark.unit
class TestWrapDiffHtml:
    """Verify wrap_diff_html adds CSS and container div."""

    def test_adds_style_tag(self):
        """Wrapped output contains <style> tag."""
        result = wrap_diff_html("<table>test</table>")
        assert "<style>" in result

    def test_adds_resume_diff_container(self):
        """Wrapped output contains class='resume-diff' container div."""
        result = wrap_diff_html("<table>test</table>")
        assert 'class="resume-diff"' in result

    def test_preserves_original_content(self):
        """Original table content is preserved in wrapped output."""
        table = "<table><tr><td>hello</td></tr></table>"
        result = wrap_diff_html(table)
        assert table in result
