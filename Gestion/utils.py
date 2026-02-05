def get_ordering(request, allowed_fields, default_field='-pk'):
    """
    Helper to determine ordering field based on request params.
    allowed_fields: list of valid field names that can be sorted.
    """
    sort_by = request.GET.get('sort')
    direction = request.GET.get('dir', 'asc')
    
    ordering = default_field
    
    if sort_by in allowed_fields:
        if direction == 'desc':
            ordering = f'-{sort_by}'
        else:
            ordering = sort_by
            
    return ordering
