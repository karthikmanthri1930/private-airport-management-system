from django import template

register = template.Library()


@register.filter
def attr(value, name):
    try:
        field = value._meta.get_field(name)
        display_method = getattr(value, f"get_{name}_display", None)
        if field.choices and display_method:
            return display_method()
        result = getattr(value, name)
        return result() if callable(result) and name.startswith("get_") else result
    except (AttributeError, TypeError):
        return "—"


@register.filter
def status_class(value):
    value = str(value).lower()
    if value in {"confirmed", "available", "arrived", "succeeded", "completed"}:
        return "good"
    if value in {"pending", "scheduled", "boarding", "maintenance", "delayed"}:
        return "warn"
    if value in {"cancelled", "failed", "retired"}:
        return "bad"
    return "neutral"
