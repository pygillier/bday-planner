import html as html_lib
import re

import bleach
import markdown
from markupsafe import Markup

ALLOWED_TAGS = ["p", "br", "strong", "em", "a", "ul", "ol", "li"]
ALLOWED_ATTRIBUTES = {"a": ["href", "title"]}
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

_LINK_RE = re.compile(r'<a\s+[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)


def _substitute(body_template, context):
    """Plain-text placeholder substitution, run BEFORE Markdown parsing.

    Newlines are stripped from substituted values (except {lien}, an
    internally-generated URL) as defense in depth, matching
    render_invitation_subject. The actual trust boundary against injected
    HTML/Markdown is bleach.clean() below, not this step -- see the
    docstrings of render_follow_up_markdown/render_follow_up_sms_text.
    """
    result = body_template
    for key, value in context.items():
        safe_value = str(value)
        if key != "lien":
            safe_value = safe_value.replace("\r", " ").replace("\n", " ")
        result = result.replace("{" + key + "}", safe_value)
    return result


def render_follow_up_markdown(body_template, context):
    """Render an admin-authored Markdown follow-up body to sanitized HTML.

    Placeholders are substituted into the plain-text template first, then
    the whole string is parsed as Markdown, then bleach.clean() strips
    everything outside a small allow-list (bold/italic/links/paragraphs/
    lists). bleach is the real security boundary here -- it's what makes
    substituting before parsing safe -- never render this through Jinja
    (see EmailTemplate's docstring in app/models.py for why).
    """
    substituted = _substitute(body_template, context)
    html_body = markdown.markdown(substituted)
    cleaned = bleach.clean(
        html_body,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    return Markup(cleaned)


def render_follow_up_sms_text(body_template, context):
    """Convert the same Markdown body to plain text for SMS.

    Bold/italic markers and list bullets are dropped (they'd just show up
    as literal asterisks/brackets on a phone) and [text](url) becomes
    'text (url)'. Reuses render_follow_up_markdown's sanitized HTML as the
    starting point, so this never operates on unsanitized content.
    """
    html_body = str(render_follow_up_markdown(body_template, context))
    with_links = _LINK_RE.sub(r"\2 (\1)", html_body)
    with_breaks = (
        with_links.replace("</p>", "\n\n")
        .replace("<br>", "\n")
        .replace("<br/>", "\n")
        .replace("<li>", "- ")
        .replace("</li>", "\n")
    )
    text = bleach.clean(with_breaks, tags=[], strip=True)
    text = html_lib.unescape(text)

    lines = [line.strip() for line in text.splitlines()]
    collapsed = []
    for line in lines:
        if line or (collapsed and collapsed[-1]):
            collapsed.append(line)
    return "\n".join(collapsed).strip()
