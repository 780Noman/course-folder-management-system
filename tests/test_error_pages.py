"""Custom 404/500 pages render instead of Django's bare defaults."""

import pytest
from django.template.loader import render_to_string
from django.test import Client


@pytest.mark.django_db
def test_404_uses_custom_page(settings):
    settings.DEBUG = False
    client = Client(raise_request_exception=False)
    resp = client.get("/definitely-not-a-real-page/")
    assert resp.status_code == 404
    assert b"Page not found" in resp.content
    assert b"Go to the home page" in resp.content


def test_500_template_renders_with_empty_context():
    """Django renders 500.html with an empty context — the template must be
    fully standalone (no static files / context processors)."""
    html = render_to_string("500.html")
    assert "Something went wrong" in html
    assert "{#" not in html  # no comment leak
    assert "{% static" not in html  # truly standalone
