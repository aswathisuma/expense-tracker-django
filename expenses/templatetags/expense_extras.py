from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


def format_inr(value):
    """
    Format a number as Indian Rupees using Indian digit grouping.

    1250       -> ₹1,250.00
    1234567.5  -> ₹12,34,567.50
    """
    try:
        amount = Decimal(value or 0)
    except (InvalidOperation, TypeError, ValueError):
        return value

    sign = '-' if amount < 0 else ''
    whole, fraction = f'{abs(amount):.2f}'.split('.')

    # The last 3 digits form one group; everything before is grouped in pairs.
    if len(whole) > 3:
        head, last_three = whole[:-3], whole[-3:]
        pairs = []
        while len(head) > 2:
            pairs.insert(0, head[-2:])
            head = head[:-2]
        if head:
            pairs.insert(0, head)
        whole = ','.join(pairs) + ',' + last_three

    return f'{sign}₹{whole}.{fraction}'


@register.filter
def inr(value):
    """Template usage: {{ expense.amount|inr }}"""
    return format_inr(value)
