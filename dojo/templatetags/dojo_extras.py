from django import template

register = template.Library()


@register.filter
def lines(value):
    """Split a newline-delimited content field into clean list items."""
    if not value:
        return []
    return [line.strip() for line in str(value).splitlines() if line.strip()]
