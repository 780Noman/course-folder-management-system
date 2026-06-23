"""Guard against template bugs that leak text to the page.

Django's ``{# ... #}`` comment must be on a SINGLE line. A multi-line one is not
recognised as a comment and is rendered as visible text. This test scans every
project template and fails if any line opens ``{#`` without closing ``#}`` on the
same line, so this class of bug cannot return unnoticed.
"""

from pathlib import Path

import pytest

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _template_files():
    return sorted(TEMPLATES_DIR.rglob("*.html"))


def test_templates_directory_found():
    assert TEMPLATES_DIR.is_dir()
    assert _template_files(), "no templates found to check"


@pytest.mark.parametrize(
    "template", _template_files(), ids=lambda p: str(p.name)
)
def test_no_multiline_django_comments(template):
    offenders = []
    for lineno, line in enumerate(
        template.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if "{#" in line and "#}" not in line:
            offenders.append(f"{template.relative_to(TEMPLATES_DIR)}:{lineno}: {line.strip()}")
    assert not offenders, (
        "Multi-line Django comments leak as visible text; keep {# #} on one line:\n"
        + "\n".join(offenders)
    )
