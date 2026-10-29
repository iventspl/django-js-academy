"""Podglądy gotowych komponentów w sandboxowanym iframe."""

from __future__ import annotations

from .models import JsComponent

BASE_CSS = """
* { box-sizing: border-box; }
body {
  margin: 0; padding: 16px; background: #fffdf7; color: #1b2a31;
  font-family: "Avenir Next", "Segoe UI", system-ui, sans-serif;
  font-size: 14px; line-height: 1.45;
}
button, input, select, textarea { font: inherit; }
button { cursor: pointer; }
:focus-visible { outline: 2px solid #b88600; outline-offset: 2px; }
"""


def build_component_preview(component: JsComponent) -> str:
    safe_js = component.js_code.replace("</script", "<\\/script")
    return (
        '<!doctype html><html lang="pl"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<style>"
        + BASE_CSS
        + component.css_code
        + "</style></head><body>"
        + component.html_code
        + "<script>"
        + safe_js
        + "</script></body></html>"
    )
