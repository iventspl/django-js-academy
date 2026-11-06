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
