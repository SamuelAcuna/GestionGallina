from django import template
from django.utils.safestring import mark_safe
from django.utils.http import urlencode

register = template.Library()

@register.simple_tag(takes_context=True)
def sort_header(context, label, field):
    """
    Renders a sortable table header.
    Usage: {% sort_header 'Name' 'name' %}
    """
    request = context['request']
    current_sort = request.GET.get('sort', '')
    current_dir = request.GET.get('dir', 'asc')
    
    # Defaults
    new_dir = 'asc'
    icon = '<i class="bi bi-arrow-down-up text-muted ms-1" style="font-size: 0.8em;"></i>'
    
    if current_sort == field:
        if current_dir == 'asc':
            new_dir = 'desc'
            icon = '<i class="bi bi-arrow-up-short ms-1"></i>'
        else:
            new_dir = 'asc'
            icon = '<i class="bi bi-arrow-down-short ms-1"></i>'
    
    # Build URL params preserving existing ones
    params = request.GET.copy()
    params['sort'] = field
    params['dir'] = new_dir
    
    # Reset pagination to page 1 when sorting
    if 'page' in params:
        del params['page']
        
    url = f"?{params.urlencode()}"
    
    html = f'<a href="{url}" class="text-decoration-none text-dark fw-bold" style="cursor: pointer;">{label} {icon}</a>'
    return mark_safe(html)
