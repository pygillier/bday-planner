from app.markdown_utils import render_follow_up_markdown, render_follow_up_sms_text


def test_bold_italic_render_to_tags():
    html = str(render_follow_up_markdown("**gras** et *italique*", {}))
    assert "<strong>gras</strong>" in html
    assert "<em>italique</em>" in html


def test_links_rendered_with_safe_href():
    html = str(render_follow_up_markdown("[cliquez ici](https://example.com)", {}))
    assert '<a href="https://example.com">cliquez ici</a>' == html.replace("<p>", "").replace("</p>", "")


def test_lists_render_to_ul_li():
    html = str(render_follow_up_markdown("- item1\n- item2", {}))
    assert "<ul>" in html
    assert "<li>item1</li>" in html
    assert "<li>item2</li>" in html


def test_javascript_url_scheme_stripped():
    html = str(render_follow_up_markdown("[cliquez](javascript:alert(1))", {}))
    assert "javascript:" not in html
    # bleach drops the disallowed-protocol href but keeps the surrounding tag/text
    assert "<a>cliquez</a>" in html


def test_script_tag_is_stripped_not_rendered():
    html = str(render_follow_up_markdown("<script>alert(1)</script>", {}))
    assert "<script" not in html
    # the tag is stripped but its text content survives as plain text -- this
    # is inert once dropped into a <p>/<div>, unlike an executable <script>
    assert "alert(1)" in html


def test_disallowed_tags_stripped_but_text_kept():
    html = str(render_follow_up_markdown("<h1>Titre</h1>", {}))
    assert "<h1" not in html
    assert "Titre" in html


def test_disallowed_attributes_stripped():
    html = str(render_follow_up_markdown("<img src=x onerror=alert(1)>", {}))
    assert "<img" not in html
    assert "onerror" not in html


def test_placeholder_substitution_happens_before_markdown_parsing():
    # Deliberate, documented trade-off: substitution runs before Markdown
    # parsing, so Markdown-special characters in a placeholder value (e.g. an
    # admin-imported guest name) are interpreted as Markdown syntax. bleach's
    # allow-list is the actual security boundary, so this is safe -- just
    # worth locking in as intentional behavior.
    html = str(render_follow_up_markdown("Bonjour {prenom}", {"prenom": "*Jean*"}))
    assert "<em>Jean</em>" in html


def test_sms_render_strips_markdown_to_plain_text():
    text = render_follow_up_sms_text("**Merci** de venir, voir [ici](https://x.example/y)", {})
    assert "*" not in text
    assert "<" not in text and ">" not in text
    assert text == "Merci de venir, voir ici (https://x.example/y)"


def test_sms_render_strips_javascript_url():
    text = render_follow_up_sms_text("[cliquez](javascript:alert(1))", {})
    assert "javascript:" not in text
    assert text == "cliquez"


def test_sms_render_lists_use_dash_bullets():
    text = render_follow_up_sms_text("- item1\n- item2", {})
    assert "- item1" in text
    assert "- item2" in text
