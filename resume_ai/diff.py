"""HTML diff generation for comparing original vs tailored resume text.

Provides a side-by-side visual comparison so users can verify that the LLM
did not fabricate experience or qualifications -- a key anti-fabrication
guardrail for the resume tailoring pipeline.
"""

import difflib


def generate_resume_diff_html(original_text: str, tailored_text: str) -> str:
    """Generate an HTML table showing side-by-side differences.

    Parameters
    ----------
    original_text:
        The original resume text (plain text or Markdown).
    tailored_text:
        The tailored resume text produced by the LLM.

    Returns
    -------
    str
        An HTML ``<table>`` element with color-coded additions, changes,
        and deletions.  Suitable for embedding in a web page.
    """
    original_lines = original_text.splitlines()
    tailored_lines = tailored_text.splitlines()

    differ = difflib.HtmlDiff(tabsize=2, wrapcolumn=80)
    return differ.make_table(
        fromlines=original_lines,
        tolines=tailored_lines,
        fromdesc="Original Resume",
        todesc="Tailored Resume",
        context=True,
        numlines=3,
    )


def wrap_diff_html(diff_table: str) -> str:
    """Wrap a raw diff table in a styled container for dashboard display.

    Parameters
    ----------
    diff_table:
        The HTML table string produced by :func:`generate_resume_diff_html`.

    Returns
    -------
    str
        The table wrapped in a ``<div class="resume-diff">`` with inline CSS
        for readable formatting and color-coded additions/deletions.
    """
    css = (
        "<style>"
        ".resume-diff table { width: 100%; border-collapse: collapse; "
        "font-size: 12px; font-family: monospace; }"
        ".resume-diff td { padding: 2px 6px; vertical-align: top; }"
        ".resume-diff th { padding: 4px 6px; text-align: left; "
        "background: #f3f4f6; font-weight: bold; }"
        ".resume-diff .diff_add { background: #d1fae5; }"
        ".resume-diff .diff_chg { background: #fef3c7; }"
        ".resume-diff .diff_sub { background: #fee2e2; }"
        ".resume-diff .diff_header { background: #e5e7eb; }"
        "</style>"
    )
    return f'{css}\n<div class="resume-diff">\n{diff_table}\n</div>'
