# FILE PATH: coa/templatetags/coa_extras.py
#
# HOW TO SET UP:
# 1. Create folder: coa/templatetags/
# 2. Create empty file: coa/templatetags/__init__.py
# 3. Create this file: coa/templatetags/coa_extras.py
# 4. At the top of create_coa.html add: {% load coa_extras %}

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Allow dict[key] lookups in templates: {{ my_dict|get_item:key }}"""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None