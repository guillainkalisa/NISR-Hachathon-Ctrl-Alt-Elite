from django import template

register = template.Library()


@register.filter
def pct(value, digits=0):
    """0.4123 -> '41%'. Missing values render as an em dash."""
    if value is None:
        return "—"
    return f"{value * 100:.{int(digits)}f}%"


@register.filter
def num(value):
    """12345.6 -> '12,346'."""
    if value is None:
        return "—"
    return f"{round(value):,}"
