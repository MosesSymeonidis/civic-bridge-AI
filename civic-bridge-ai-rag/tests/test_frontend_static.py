from pathlib import Path


def test_chat_sources_render_as_links_when_urls_are_present():
    html = Path("app/static/index.html").read_text()
    assert "citationHtml(c, i)" in html
    assert "c.url" in html
    assert "<a href=" in html


def test_inline_source_markers_and_related_cases_render_as_links():
    html = Path("app/static/index.html").read_text()
    assert "md(data.reply, data.citations || [])" in html
    assert "citation.url" in html
    assert "caseHtml(c)" in html
    assert "c.url" in html


def test_markdown_autolinks_http_and_https_urls():
    html = Path("app/static/index.html").read_text()
    assert "https?:\\/\\/" in html
    assert '<a href="$2" target="_blank" rel="noopener">$2</a>' in html


def test_analysis_and_reporting_cards_are_collapsible_and_render_before_reply():
    html = Path("app/static/index.html").read_text()
    assert "<details" in html
    assert "reportingCard(data.reporting)" in html
    assert "add(analysisCard(data.analysis) + reportingCard(data.reporting), \"bot\");" in html
    assert "let html = md(data.reply, data.citations || [])" in html


def test_sources_render_collapsed_by_default():
    html = Path("app/static/index.html").read_text()
    assert "sourcesDetails(data.citations)" in html
    assert "Sources (${citations.length})" in html


def test_how_it_works_page_explains_backend_method():
    html = Path("app/static/how-it-works.html").read_text()
    required = [
        "How Civic Bridge AI Works",
        "Roles and age groups",
        "Teacher guidance",
        "Student guidance",
        "Semantic barriers",
        "External sources",
        "Council of Europe",
        "RFCDC",
        "human review",
        "country-specific reporting",
    ]
    for text in required:
        assert text in html
