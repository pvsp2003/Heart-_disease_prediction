
from django import template

register = template.Library()

@register.filter
def is_radio(field):
    """
    Returns True if the form field's widget is a radio button.
    """
    return getattr(field.field.widget, 'input_type', '') == 'radio'
