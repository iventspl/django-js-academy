"""Template filters for the Django handbook's small prose subset."""

from django import template
from django.utils.safestring import mark_safe

from ..handbook import highlight, render_inline, render_prose

register = template.Library()


@register.filter
def prose(value):
    return mark_safe(render_prose(value))


@register.filter
def inline(value):
    return mark_safe(render_inline(value))


@register.filter
def mark_query(value, query):
    return mark_safe(highlight(value, query))


@register.filter
def note_for(notes, section_id):
    return notes.get(section_id) if notes else None


@register.simple_tag(takes_context=True)
def hb_query(context, **kwargs):
    """Return the current query string with keys replaced or removed.

    Used by the level/type filters so a search keeps its query while narrowing.
    """
    request = context.get("request")
    if request is None:
        return ""
    params = request.GET.copy()
    for key, value in kwargs.items():
        if value:
            params[key] = value
        else:
            params.pop(key, None)
    return params.urlencode()
